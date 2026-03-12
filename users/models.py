from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator


# ---------------------------------------------------------------------------
# Upload path helpers
# ---------------------------------------------------------------------------

def profile_image_upload_path(instance, filename):
    """Store profile images under media/profile_images/<user_id>/"""
    return f"profile_images/{instance.user.id}/{filename}"


def food_image_upload_path(instance, filename):
    """Store food images under media/food_images/<donor_id>/"""
    return f"food_images/{instance.donor.id}/{filename}"


def delivery_image_upload_path(instance, filename):
    """Store delivery proof images under media/delivery_images/<donation_id>/"""
    return f"delivery_images/{instance.id}/{filename}"


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("donor", "Donor"),
        ("volunteer", "Volunteer"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="donor")
    city = models.CharField(max_length=100, blank=True)
    organization_name = models.CharField(max_length=200, blank=True)
    profile_image = models.ImageField(
        upload_to=profile_image_upload_path,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    @property
    def is_donor(self):
        return self.role == "donor"

    @property
    def is_volunteer(self):
        return self.role == "volunteer"


# ---------------------------------------------------------------------------
# FoodDonation
# ---------------------------------------------------------------------------

class FoodDonation(models.Model):
    FOOD_TYPE_CHOICES = [
        ("veg", "Vegetarian"),
        ("non_veg", "Non-Vegetarian"),
    ]

    STATUS_CHOICES = [
        ("available", "Available"),
        ("accepted", "Accepted"),
        ("picked_up", "Picked Up"),
        ("on_the_way", "On The Way"),
        ("delivered", "Delivered"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    # Core donation info
    donor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="donations",
    )
    food_name = models.CharField(max_length=200)
    food_type = models.CharField(
        max_length=10,
        choices=FOOD_TYPE_CHOICES,
        default="veg",
    )
    quantity = models.PositiveIntegerField(
        help_text="Approximate number of people this food can serve",
        validators=[MinValueValidator(1)],
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=food_image_upload_path,
        blank=True,
        null=True,
    )

    # Timing
    prepared_time = models.DateTimeField(default=timezone.now)
    expiry_time = models.DateTimeField()

    # Location
    pickup_address = models.TextField()
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )

    # Workflow state
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
        db_index=True,
    )

    # Volunteer assignment
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_donations",
    )
    pickup_time = models.DateTimeField(null=True, blank=True)

    # Delivery proof
    delivery_location = models.TextField(blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    delivery_image = models.ImageField(
        upload_to=delivery_image_upload_path,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Food Donation"
        verbose_name_plural = "Food Donations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.food_name} by {self.donor.get_full_name() or self.donor.username} [{self.status}]"

    @property
    def is_available(self):
        return self.status == "available"

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_time

    @property
    def google_maps_url(self):
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return f"https://www.google.com/maps?q={self.pickup_address}"

    @property
    def status_badge_color(self):
        color_map = {
            "available": "green",
            "accepted": "yellow",
            "picked_up": "blue",
            "on_the_way": "purple",
            "delivered": "gray",
            "expired": "red",
            "cancelled": "red",
        }
        return color_map.get(self.status, "gray")

    def save(self, *args, **kwargs):
        # Auto-expire donations past expiry time
        if self.status == "available" and self.is_expired:
            self.status = "expired"
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("accepted", "Volunteer Accepted Donation"),
        ("cancelled", "Volunteer Cancelled Pickup"),
        ("new_donation", "New Donation Posted"),
        ("picked_up", "Food Picked Up"),
        ("on_the_way", "Volunteer On The Way"),
        ("delivered", "Food Delivered"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    related_donation = models.ForeignKey(
        FoodDonation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default="new_donation",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:60]}"
