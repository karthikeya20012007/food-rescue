from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.views.decorators.http import require_POST

from .models import UserProfile, FoodDonation, Notification
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    FoodDonationForm,
    VolunteerProfileUpdateForm,
    DeliveryConfirmationForm,
)


# =============================================================================
# Helpers
# =============================================================================

import math

def _haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lng points."""
    R = 6371
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi  = math.radians(float(lat2) - float(lat1))
    dlam  = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _get_profile(user):
    """Return UserProfile for user, or None."""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def _require_donor(user):
    """Return True if user is a donor."""
    profile = _get_profile(user)
    return profile and profile.role == "donor"


def _require_volunteer(user):
    """Return True if user is a volunteer."""
    profile = _get_profile(user)
    return profile and profile.role == "volunteer"


def _push_notification(user, message, donation=None, notif_type="new_donation"):
    """Create a Notification for a user."""
    Notification.objects.create(
        user=user,
        message=message,
        related_donation=donation,
        type=notif_type,
    )


def _expire_old_donations():
    """Flip available donations that are past expiry to 'expired'."""
    now = timezone.now()
    FoodDonation.objects.filter(
        status="available",
        expiry_time__lte=now,
    ).update(status="expired")


def _role_redirect(user):
    """Redirect to the correct dashboard based on role."""
    profile = _get_profile(user)
    if profile and profile.role == "volunteer":
        return redirect("volunteer_dashboard")
    return redirect("donor_dashboard")


def _unread_count(user):
    """Return unread notification count for navbar badge."""
    return Notification.objects.filter(user=user, is_read=False).count()


# =============================================================================
# Public Views
# =============================================================================

def landing(request):
    """Public landing page with hero, features, and recent deliveries."""
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    _expire_old_donations()

    recent_deliveries = (
        FoodDonation.objects
        .filter(status="delivered")
        .select_related("donor__profile")
        .order_by("-delivery_time")[:3]
    )

    context = {
        "recent_deliveries": recent_deliveries,
        "total_meals": FoodDonation.objects.filter(
            status="delivered"
        ).aggregate(total=Sum("quantity"))["total"] or 0,
        "total_deliveries": FoodDonation.objects.filter(status="delivered").count(),
        "active_donors": UserProfile.objects.filter(role="donor").count(),
    }
    return render(request, "users/landing.html", context)


def impact_feed(request):
    """
    Public impact page — shows all verified deliveries.
    Hides donor name, volunteer phone, and exact address (privacy).
    """
    _expire_old_donations()

    deliveries = (
        FoodDonation.objects
        .filter(status="delivered")
        .select_related("donor__profile", "accepted_by__profile")
        .order_by("-delivery_time")
    )

    # Summary stats
    stats = deliveries.aggregate(total_meals=Sum("quantity"))
    total_meals      = stats["total_meals"] or 0
    total_deliveries = deliveries.count()
    cities = (
        deliveries
        .values_list("donor__profile__city", flat=True)
        .distinct()
        .count()
    )

    context = {
        "deliveries":       deliveries,
        "total_meals":      total_meals,
        "total_deliveries": total_deliveries,
        "cities_served":    cities,
    }
    return render(request, "users/impact_feed.html", context)


# =============================================================================
# Authentication Views
# =============================================================================

def register_view(request):
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
    else:
        form = UserRegistrationForm()

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request,
            f"Welcome to Food Rescue, {user.profile.full_name}! 🎉"
        )
        return _role_redirect(user)

    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    form = UserLoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        # Handle "remember me"
        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)          # browser-session only
        else:
            request.session.set_expiry(60 * 60 * 24 * 30)   # 30 days

        messages.success(request, f"Welcome back, {user.profile.full_name}! 👋")
        next_url = request.GET.get("next")
        if next_url:
            return redirect(next_url)
        return _role_redirect(user)

    return render(request, "users/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("landing")


# =============================================================================
# Shared: Notification helpers (AJAX + mark-read)
# =============================================================================

@login_required
def notifications_json(request):
    """Return unread notifications as JSON for the navbar badge."""
    notifs = (
        Notification.objects
        .filter(user=request.user, is_read=False)
        .select_related("related_donation")
        .order_by("-created_at")[:10]
    )
    data = [
        {
            "id":      n.id,
            "message": n.message,
            "type":    n.type,
            "donation_id": n.related_donation_id,
            "created_at": n.created_at.strftime("%d %b %Y, %I:%M %p"),
        }
        for n in notifs
    ]
    return JsonResponse({"notifications": data, "unread": len(data)})


@login_required
@require_POST
def mark_notifications_read(request):
    """Mark all notifications as read (called via fetch from JS)."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"status": "ok"})


# =============================================================================
# Donor Views
# =============================================================================

@login_required
def donor_dashboard(request):
    """Donor's main dashboard with analytics and donation list."""
    if not _require_donor(request.user):
        messages.error(request, "Access denied. This page is for donors only.")
        return redirect("volunteer_dashboard")

    _expire_old_donations()

    donations = (
        FoodDonation.objects
        .filter(donor=request.user)
        .select_related("accepted_by__profile")
        .order_by("-created_at")
    )

    # Analytics
    total       = donations.count()
    meals_saved = donations.filter(
        status="delivered"
    ).aggregate(total=Sum("quantity"))["total"] or 0
    active      = donations.filter(
        status__in=["available", "accepted", "picked_up", "on_the_way"]
    ).count()
    delivered   = donations.filter(status="delivered").count()

    unread = _unread_count(request.user)

    context = {
        "donations":    donations,
        "total":        total,
        "meals_saved":  meals_saved,
        "active":       active,
        "delivered":    delivered,
        "unread":       unread,
        "profile":      _get_profile(request.user),
    }
    return render(request, "users/donor_dashboard.html", context)


@login_required
def create_donation(request):
    """Donor creates a new food donation."""
    if not _require_donor(request.user):
        messages.error(request, "Only donors can post food donations.")
        return redirect("volunteer_dashboard")

    if request.method == 'POST':
        form = FoodDonationForm(request.POST, request.FILES)
    else:
        form = FoodDonationForm()

    if request.method == "POST" and form.is_valid():
        donation = form.save(commit=False)
        donation.donor = request.user
        donation.status = "available"
        donation.save()

        # Notify all volunteers about new donation
        volunteers = UserProfile.objects.filter(role="volunteer").select_related("user")
        notifications = [
            Notification(
                user=v.user,
                message=(
                    f"🍱 New donation available: {donation.food_name} "
                    f"({donation.quantity} people) in "
                    f"{request.user.profile.city or 'your area'}."
                ),
                related_donation=donation,
                type="new_donation",
            )
            for v in volunteers
        ]
        Notification.objects.bulk_create(notifications)

        messages.success(
            request,
            f"'{donation.food_name}' posted successfully! Volunteers will be notified. 🎉"
        )
        return redirect("donor_dashboard")

    context = {
        "form":    form,
        "profile": _get_profile(request.user),
        "unread":  _unread_count(request.user),
    }
    return render(request, "users/create_donation.html", context)


@login_required
def edit_donation(request, pk):
    """Donor edits an existing donation (only if still available)."""
    donation = get_object_or_404(FoodDonation, pk=pk, donor=request.user)

    if donation.status not in ("available", "expired"):
        messages.error(
            request,
            "This donation can no longer be edited because a volunteer has already accepted it."
        )
        return redirect("donation_detail", pk=pk)

    if request.method == 'POST':
        form = FoodDonationForm(request.POST, request.FILES, instance=donation)
    else:
        form = FoodDonationForm(instance=donation)

    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        # Re-open expired donations if expiry is updated to future
        if updated.expiry_time > timezone.now():
            updated.status = "available"
        updated.save()
        messages.success(request, "Donation updated successfully. ✅")
        return redirect("donation_detail", pk=pk)

    context = {
        "form":     form,
        "donation": donation,
        "profile":  _get_profile(request.user),
        "unread":   _unread_count(request.user),
    }
    return render(request, "users/create_donation.html", context)


@login_required
@require_POST
def cancel_donation(request, pk):
    """Donor cancels their donation."""
    donation = get_object_or_404(FoodDonation, pk=pk, donor=request.user)

    if donation.status not in ("available", "expired"):
        msg = "Cannot cancel a donation that is already in progress."
        messages.error(request, msg)
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": msg}, status=400)
        return redirect("donation_detail", pk=pk)

    donation.status = "cancelled"
    donation.save()
    msg = f"'{donation.food_name}' has been cancelled."
    messages.success(request, msg)
    if _is_ajax(request):
        return JsonResponse({"ok": True, "message": msg, "pk": pk})
    return redirect("donor_dashboard")


@login_required
def donation_detail(request, pk):
    """
    Detail view for a single donation.
    Donors see full info; volunteers see it from their perspective.
    """
    _expire_old_donations()
    donation = get_object_or_404(
        FoodDonation.objects.select_related(
            "donor__profile",
            "accepted_by__profile",
        ),
        pk=pk,
    )

    # Only donor or the assigned volunteer can see full details
    profile = _get_profile(request.user)
    is_owner     = donation.donor == request.user
    is_volunteer = (
        profile and profile.role == "volunteer"
        and donation.accepted_by == request.user
    )

    if not (is_owner or is_volunteer or profile and profile.role == "volunteer"):
        messages.error(request, "You don't have permission to view this donation.")
        return redirect("landing")

    context = {
        "donation":    donation,
        "is_owner":    is_owner,
        "is_volunteer": is_volunteer,
        "profile":     profile,
        "unread":      _unread_count(request.user),
    }
    return render(request, "users/donation_detail.html", context)


@login_required
def volunteer_profile(request):
    """Profile update page for both donors and volunteers."""
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        form = VolunteerProfileUpdateForm(
            request.POST,
            request.FILES,          # Always pass FILES — never use "or None"
            instance=profile,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully! ✅")
            return redirect("volunteer_profile")   # Stay on profile so user sees new photo
    else:
        form = VolunteerProfileUpdateForm(
            instance=profile,
            user=request.user,
        )

    context = {
        "form":    form,
        "profile": profile,
        "unread":  _unread_count(request.user),
    }
    return render(request, "users/volunteer_profile.html", context)


@login_required
def change_password_view(request):
    """Allow authenticated users to change their password."""
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully! 🔐")
            return redirect("volunteer_profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)

    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, "users/change_password.html", {
        "form":    form,
        "profile": profile,
        "unread":  _unread_count(request.user),
    })


@login_required
@require_POST
def remove_profile_image(request):
    """AJAX: Remove the user's profile picture and revert to initials avatar."""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.profile_image:
        # Delete the file from disk
        try:
            profile.profile_image.delete(save=False)
        except Exception:
            pass
        profile.profile_image = None
        profile.save(update_fields=["profile_image"])
    return JsonResponse({"ok": True})


# =============================================================================
# Volunteer Views
# =============================================================================

@login_required
def volunteer_dashboard(request):
    """Volunteer's dashboard with available donations and their pickups."""
    if not _require_volunteer(request.user):
        messages.error(request, "Access denied. This page is for volunteers only.")
        return redirect("donor_dashboard")

    _expire_old_donations()

    # --- Filters ---
    food_type    = request.GET.get("food_type", "all")
    search       = request.GET.get("search", "").strip()
    distance_km  = request.GET.get("distance", "all")
    vol_lat      = request.GET.get("vol_lat", "").strip()
    vol_lng      = request.GET.get("vol_lng", "").strip()

    # Available donations (not yet taken)
    available_qs = FoodDonation.objects.filter(
        status="available"
    ).select_related("donor__profile").order_by("expiry_time")

    if food_type in ("veg", "non_veg"):
        available_qs = available_qs.filter(food_type=food_type)

    if search:
        available_qs = available_qs.filter(
            Q(food_name__icontains=search) |
            Q(pickup_address__icontains=search) |
            Q(donor__profile__city__icontains=search)
        )

    # Distance filter — needs volunteer GPS coords sent from JS
    distance_applied = False
    if distance_km != "all" and vol_lat and vol_lng:
        try:
            max_km = float(distance_km)
            nearby = []
            for d in available_qs:
                if d.latitude and d.longitude:
                    km = _haversine_km(vol_lat, vol_lng, d.latitude, d.longitude)
                    if km <= max_km:
                        d._distance_km = round(km, 1)
                        nearby.append(d)
            available_qs = nearby          # already a list — template iterates fine
            distance_applied = True
        except (ValueError, TypeError):
            pass

    # My pickups
    my_pickups = (
        FoodDonation.objects
        .filter(accepted_by=request.user)
        .exclude(status__in=["delivered", "cancelled"])
        .select_related("donor__profile")
        .order_by("-updated_at")
    )

    # Analytics
    all_my = FoodDonation.objects.filter(accepted_by=request.user)
    total_pickups   = all_my.count()
    meals_delivered = all_my.filter(
        status="delivered"
    ).aggregate(total=Sum("quantity"))["total"] or 0
    active_deliveries  = all_my.filter(
        status__in=["accepted", "picked_up", "on_the_way"]
    ).count()
    completed = all_my.filter(status="delivered").count()

    unread = _unread_count(request.user)

    context = {
        "available_donations": available_qs,
        "my_pickups":          my_pickups,
        "total_pickups":       total_pickups,
        "meals_delivered":     meals_delivered,
        "active_deliveries":   active_deliveries,
        "completed":           completed,
        "food_type":           food_type,
        "search":              search,
        "distance_km":         distance_km,
        "distance_applied":    distance_applied,
        "profile":             _get_profile(request.user),
        "unread":              unread,
    }
    return render(request, "users/volunteer_dashboard.html", context)


def _is_ajax(request):
    """Return True if request is an XMLHttpRequest / fetch with JSON accept."""
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


@login_required
@require_POST
def accept_pickup(request, pk):
    """
    First volunteer to click Accept wins the donation (race-condition safe).
    Uses select_for_update to prevent double-acceptance.
    """
    if not _require_volunteer(request.user):
        messages.error(request, "Only volunteers can accept pickups.")
        return redirect("donor_dashboard")

    with transaction.atomic():
        donation = get_object_or_404(
            FoodDonation.objects.select_for_update(),
            pk=pk,
            status="available",
        )
        donation.status      = "accepted"
        donation.accepted_by = request.user
        donation.save()

    volunteer_name = request.user.profile.full_name

    # Notify the donor
    _push_notification(
        user=donation.donor,
        message=(
            f"✅ {volunteer_name} has accepted your donation "
            f"'{donation.food_name}' and will pick it up soon!"
        ),
        donation=donation,
        notif_type="accepted",
    )

    msg = (
        f"You have accepted '{donation.food_name}'. Please pick it up before "
        f"{donation.expiry_time.strftime('%d %b, %I:%M %p')}. 🚀"
    )
    messages.success(request, msg)
    if _is_ajax(request):
        return JsonResponse({"ok": True, "message": msg, "new_status": "accepted"})
    return redirect("volunteer_dashboard")


@login_required
@require_POST
def cancel_pickup(request, pk):
    """Volunteer cancels their accepted pickup (only while status = accepted)."""
    if not _require_volunteer(request.user):
        return redirect("donor_dashboard")

    donation = get_object_or_404(
        FoodDonation,
        pk=pk,
        accepted_by=request.user,
    )
    # Can only cancel before the food has been handed over (accepted or picked_up)
    if donation.status not in ("accepted", "picked_up"):
        messages.error(request, "You can only cancel before the food is on the way.")
        return redirect("volunteer_dashboard")

    donation.status      = "available"
    donation.accepted_by = None
    donation.pickup_time = None
    donation.save()

    volunteer_name = request.user.profile.full_name

    # Notify the donor
    _push_notification(
        user=donation.donor,
        message=(
            f"⚠️ {volunteer_name} has cancelled the pickup for "
            f"'{donation.food_name}'. It is now available again for other volunteers."
        ),
        donation=donation,
        notif_type="cancelled",
    )

    msg = (
        f"You have cancelled the pickup for '{donation.food_name}'. "
        "The donation is now available to other volunteers."
    )
    messages.warning(request, msg)
    if _is_ajax(request):
        # Return full donation data so the frontend can reinsert the card
        return JsonResponse({
            "ok":         True,
            "message":    msg,
            "new_status": "available",
            "donation": {
                "pk":             donation.pk,
                "food_name":      donation.food_name,
                "food_type":      donation.food_type,
                "quantity":       donation.quantity,
                "pickup_address": donation.pickup_address,
                "expiry_time":    (
                    donation.expiry_time.strftime("%d %b, %I:%M %p")
                    .lstrip("0").replace(" 0", " ")
                ),
                "is_expired":     donation.is_expired,
                "donor_name":     donation.donor.profile.full_name or donation.donor.username,
                "google_maps_url":donation.google_maps_url,
                "accept_url":     f"/volunteer/{donation.pk}/accept/",
            }
        })
    return redirect("volunteer_dashboard")


@login_required
@require_POST
def mark_picked_up(request, pk):
    """Volunteer marks food as physically picked up from donor."""
    if not _require_volunteer(request.user):
        return redirect("donor_dashboard")

    donation = get_object_or_404(
        FoodDonation,
        pk=pk,
        accepted_by=request.user,
        status="accepted",
    )

    donation.status      = "picked_up"
    donation.pickup_time = timezone.now()
    donation.save()

    _push_notification(
        user=donation.donor,
        message=(
            f"📦 {request.user.profile.full_name} has picked up "
            f"'{donation.food_name}' and is heading to deliver it!"
        ),
        donation=donation,
        notif_type="picked_up",
    )

    msg = f"'{donation.food_name}' marked as picked up. Safe travels! 🛵"
    messages.success(request, msg)
    if _is_ajax(request):
        return JsonResponse({"ok": True, "message": msg, "new_status": "picked_up"})
    return redirect("volunteer_dashboard")


@login_required
@require_POST
def mark_on_the_way(request, pk):
    """Volunteer marks that they are on the way to deliver."""
    if not _require_volunteer(request.user):
        return redirect("donor_dashboard")

    donation = get_object_or_404(
        FoodDonation,
        pk=pk,
        accepted_by=request.user,
        status="picked_up",
    )

    donation.status = "on_the_way"
    donation.save()

    _push_notification(
        user=donation.donor,
        message=(
            f"🚗 {request.user.profile.full_name} is on the way to deliver "
            f"'{donation.food_name}'!"
        ),
        donation=donation,
        notif_type="on_the_way",
    )

    msg = f"Status updated — you are on the way with '{donation.food_name}'! 🗺️"
    messages.success(request, msg)
    if _is_ajax(request):
        return JsonResponse({"ok": True, "message": msg, "new_status": "on_the_way"})
    return redirect("volunteer_dashboard")


@login_required
def mark_delivered(request, pk):
    """
    Volunteer marks donation as delivered after uploading proof photo.
    GET  → show delivery confirmation form
    POST → save form and complete delivery
    """
    if not _require_volunteer(request.user):
        return redirect("donor_dashboard")

    donation = get_object_or_404(
        FoodDonation,
        pk=pk,
        accepted_by=request.user,
        status="on_the_way",
    )

    if request.method == 'POST':
        form = DeliveryConfirmationForm(request.POST, request.FILES, instance=donation)
    else:
        form = DeliveryConfirmationForm(instance=donation)

    if request.method == "POST" and form.is_valid():
        form.save()   # sets status=delivered, delivery_time=now, saves image

        _push_notification(
            user=donation.donor,
            message=(
                f"🎉 '{donation.food_name}' has been successfully delivered by "
                f"{request.user.profile.full_name}! "
                f"~{donation.quantity} people have been served. Thank you! ❤️"
            ),
            donation=donation,
            notif_type="delivered",
        )

        messages.success(
            request,
            f"Delivery confirmed for '{donation.food_name}'! "
            f"You just helped feed ~{donation.quantity} people. Amazing work! 🌟"
        )
        return redirect("volunteer_dashboard")

    context = {
        "form":     form,
        "donation": donation,
        "profile":  _get_profile(request.user),
        "unread":   _unread_count(request.user),
    }
    return render(request, "users/mark_delivered.html", context)