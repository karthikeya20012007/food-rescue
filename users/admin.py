from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import UserProfile, FoodDonation, Notification


# ---------------------------------------------------------------------------
# UserProfile Admin
# ---------------------------------------------------------------------------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "user",
        "role",
        "city",
        "organization_name",
        "phone",
        "profile_image_preview",
        "created_at",
    )
    list_filter = ("role", "city", "created_at")
    search_fields = ("full_name", "user__username", "user__email", "city", "organization_name")
    readonly_fields = ("created_at", "profile_image_preview")
    ordering = ("-created_at",)

    fieldsets = (
        ("Account", {
            "fields": ("user", "full_name", "role"),
        }),
        ("Contact & Location", {
            "fields": ("phone", "city", "organization_name"),
        }),
        ("Profile Image", {
            "fields": ("profile_image", "profile_image_preview"),
        }),
        ("Metadata", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Photo")
    def profile_image_preview(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width:48px; height:48px; '
                'border-radius:50%; object-fit:cover;" />',
                obj.profile_image.url,
            )
        return "—"


# ---------------------------------------------------------------------------
# FoodDonation Admin
# ---------------------------------------------------------------------------

@admin.register(FoodDonation)
class FoodDonationAdmin(admin.ModelAdmin):
    list_display = (
        "food_name",
        "food_type",
        "quantity",
        "donor",
        "status_badge",
        "pickup_address_short",
        "expiry_time",
        "accepted_by",
        "created_at",
    )
    list_filter = ("status", "food_type", "created_at")
    search_fields = (
        "food_name",
        "donor__username",
        "donor__email",
        "pickup_address",
        "accepted_by__username",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "food_image_preview",
        "delivery_image_preview",
        "google_maps_link",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Food Details", {
            "fields": (
                "donor",
                "food_name",
                "food_type",
                "quantity",
                "description",
                ("image", "food_image_preview"),
            ),
        }),
        ("Timing", {
            "fields": ("prepared_time", "expiry_time"),
        }),
        ("Pickup Location", {
            "fields": (
                "pickup_address",
                ("latitude", "longitude"),
                "google_maps_link",
            ),
        }),
        ("Workflow", {
            "fields": ("status", "accepted_by", "pickup_time"),
        }),
        ("Delivery", {
            "fields": (
                "delivery_location",
                "delivery_time",
                ("delivery_image", "delivery_image_preview"),
            ),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["mark_expired", "mark_available"]

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colors = {
            "available": "#10b981",
            "accepted": "#f59e0b",
            "picked_up": "#3b82f6",
            "on_the_way": "#8b5cf6",
            "delivered": "#6b7280",
            "expired": "#ef4444",
            "cancelled": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:999px;font-size:12px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Pickup Address")
    def pickup_address_short(self, obj):
        return obj.pickup_address[:50] + "…" if len(obj.pickup_address) > 50 else obj.pickup_address

    @admin.display(description="Food Image")
    def food_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:120px; border-radius:8px;" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Delivery Image")
    def delivery_image_preview(self, obj):
        if obj.delivery_image:
            return format_html(
                '<img src="{}" style="max-height:120px; border-radius:8px;" />',
                obj.delivery_image.url,
            )
        return "—"

    @admin.display(description="Google Maps")
    def google_maps_link(self, obj):
        url = obj.google_maps_url
        return format_html('<a href="{}" target="_blank">📍 Open in Maps</a>', url)

    @admin.action(description="Mark selected donations as Expired")
    def mark_expired(self, request, queryset):
        updated = queryset.update(status="expired")
        self.message_user(request, f"{updated} donation(s) marked as expired.")

    @admin.action(description="Reset selected donations to Available")
    def mark_available(self, request, queryset):
        updated = queryset.update(status="available", accepted_by=None, pickup_time=None)
        self.message_user(request, f"{updated} donation(s) reset to available.")


# ---------------------------------------------------------------------------
# Notification Admin
# ---------------------------------------------------------------------------

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "type",
        "message_short",
        "related_donation",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("user__username", "message", "related_donation__food_name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    actions = ["mark_all_read"]

    @admin.display(description="Message")
    def message_short(self, obj):
        return obj.message[:80] + "…" if len(obj.message) > 80 else obj.message

    @admin.action(description="Mark selected notifications as read")
    def mark_all_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")


# ---------------------------------------------------------------------------
# Admin site branding
# ---------------------------------------------------------------------------

admin.site.site_header = "🍱 Food Rescue Admin"
admin.site.site_title = "Food Rescue"
admin.site.index_title = "Management Dashboard"
