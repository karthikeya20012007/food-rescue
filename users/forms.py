from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .models import UserProfile, FoodDonation


class CleanFileInput(forms.ClearableFileInput):
    """
    Clean file input — hides Django's verbose 'Currently: path Clear Change:'
    rendering. Renders just the file chooser button; the template shows the
    current image separately via profile_image.url / image.url.
    """
    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        # Suppress 'Currently: …' initial-value display
        ctx['widget']['is_initial'] = False
        return ctx

    def use_required_attribute(self, initial_value):
        # Don't mark required when a file already exists
        return not initial_value


# ---------------------------------------------------------------------------
# Tailwind CSS class helpers
# ---------------------------------------------------------------------------

TEXT_INPUT   = "inp"
SELECT_INPUT = "inp"
FILE_INPUT   = (
    "w-full text-sm t3 "
    "file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 "
    "file:text-sm file:font-semibold cursor-pointer "
    "file:bg-emerald-900 file:text-emerald-300 "
    "hover:file:bg-emerald-800 "
    "dark:file:bg-emerald-900 dark:file:text-emerald-300 "
    "transition duration-200"
)
TEXTAREA     = "inp"
CHECKBOX     = (
    "h-4 w-4 rounded text-emerald-500 "
    "focus:ring-emerald-400 transition duration-200 cursor-pointer"
)


# ---------------------------------------------------------------------------
# 1. User Registration Form
# ---------------------------------------------------------------------------

class UserRegistrationForm(forms.Form):
    """
    Combined form that creates both a Django User and a linked UserProfile.
    Call form.save() to persist both objects.
    """

    ROLE_CHOICES = [
        ("donor",     "🍱 Food Donor"),
        ("volunteer", "🤝 Volunteer"),
    ]

    # ── User fields ──────────────────────────────────────────────────────────
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "Jane Smith",
            "autofocus":   True,
        }),
        label="Full Name",
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "jane@example.com",
        }),
        label="Email Address",
    )

    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "+91 98765 43210",
        }),
        label="Phone Number",
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "Minimum 8 characters",
        }),
        label="Password",
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "Re-enter your password",
        }),
        label="Confirm Password",
    )

    # ── Profile fields ───────────────────────────────────────────────────────
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "hidden peer"}),
        label="I want to join as",
        initial="donor",
    )

    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "Mumbai",
        }),
        label="City",
    )

    organization_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "Restaurant / NGO / Event (optional)",
        }),
        label="Organization Name",
    )

    profile_image = forms.ImageField(
        required=False,
        widget=CleanFileInput(attrs={
            "class":  FILE_INPUT,
            "accept": "image/*",
        }),
        label="Profile Photo",
    )

    # ── Validation ───────────────────────────────────────────────────────────

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_confirm_password(self):
        pw  = self.cleaned_data.get("password")
        cpw = self.cleaned_data.get("confirm_password")
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cpw

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            digits = "".join(c for c in phone if c.isdigit())
            if len(digits) < 7:
                raise forms.ValidationError("Enter a valid phone number.")
        return phone

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self):
        data  = self.cleaned_data
        email = data["email"]

        user = User.objects.create_user(
            username   = email,
            email      = email,
            password   = data["password"],
            first_name = data["full_name"].split()[0],
            last_name  = " ".join(data["full_name"].split()[1:]),
        )

        # The signal creates a bare profile; update it with full data
        profile = user.profile
        profile.full_name         = data["full_name"]
        profile.phone             = data.get("phone", "")
        profile.role              = data["role"]
        profile.city              = data.get("city", "")
        profile.organization_name = data.get("organization_name", "")
        if data.get("profile_image"):
            profile.profile_image = data["profile_image"]
        profile.save()

        return user


# ---------------------------------------------------------------------------
# 2. Login Form
# ---------------------------------------------------------------------------

class UserLoginForm(AuthenticationForm):
    """
    Extends Django's built-in AuthenticationForm with Tailwind styling.
    Accepts email as the username field.
    """

    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class":         TEXT_INPUT,
            "placeholder":   "jane@example.com",
            "autofocus":     True,
            "autocomplete":  "off",
            "data-lpignore": "true",
            "data-form-type":"other",
            "spellcheck":    "false",
        }),
        label="Email Address",
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class":         TEXT_INPUT,
            "placeholder":   "Your password",
            "autocomplete":  "new-password",
            "data-lpignore": "true",
            "data-form-type":"other",
        }),
        label="Password",
    )

    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX}),
        label="Remember me for 30 days",
    )

    error_messages = {
        "invalid_login": "Invalid email or password. Please try again.",
        "inactive":      "This account has been deactivated.",
    }


# ---------------------------------------------------------------------------
# 3. Food Donation Form
# ---------------------------------------------------------------------------

class FoodDonationForm(forms.ModelForm):
    """
    Used by donors to post a new surplus food donation.
    Includes GPS-optional location capture via hidden lat/lng fields.
    """

    class Meta:
        model  = FoodDonation
        fields = [
            "food_name",
            "food_type",
            "quantity",
            "description",
            "image",
            "expiry_time",
            "pickup_address",
            "latitude",
            "longitude",
        ]
        widgets = {
            "food_name": forms.TextInput(attrs={
                "class":       TEXT_INPUT,
                "placeholder": "e.g. Biryani, Sandwiches, Curry",
            }),
            "food_type": forms.Select(attrs={
                "class": SELECT_INPUT,
            }),
            "quantity": forms.NumberInput(attrs={
                "class":       TEXT_INPUT,
                "placeholder": "Number of people this can serve",
                "min":         1,
                "max":         10000,
            }),
            "description": forms.Textarea(attrs={
                "class":       TEXTAREA,
                "placeholder": "Allergens, packaging details, any special notes…",
                "rows":        3,
            }),
            "image": CleanFileInput(attrs={
                "class":   FILE_INPUT,
                "accept":  "image/*",
            }),
            "expiry_time": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": TEXT_INPUT,
                    "type":  "datetime-local",
                },
            ),
            "pickup_address": forms.Textarea(attrs={
                "class":       TEXTAREA,
                "placeholder": "Full pickup address (door / landmark / area)",
                "rows":        2,
            }),
            # Hidden — populated by JS geolocation
            "latitude": forms.HiddenInput(attrs={"id": "id_latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_longitude"}),
        }
        labels = {
            "food_name":      "Food Name",
            "food_type":      "Food Type",
            "quantity":       "Serves (people)",
            "description":    "Description (optional)",
            "image":          "Food Photo (optional)",
            "expiry_time":    "Expires At",
            "pickup_address": "Pickup Address",
            "latitude":       "",
            "longitude":      "",
        }
        help_texts = {
            "quantity":    "Approximate number of people this food can serve.",
            "expiry_time": "Food must be picked up before this time.",
        }

    # ── Init ─────────────────────────────────────────────────────────────────

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Address is validated in clean() so GPS-only submissions work
        self.fields["pickup_address"].required = False

    # ── Validation ───────────────────────────────────────────────────────────

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is None or qty < 1:
            raise forms.ValidationError("Quantity must be at least 1 person.")
        if qty > 10000:
            raise forms.ValidationError("Quantity seems too high. Please double-check.")
        return qty

    def clean_expiry_time(self):
        expiry = self.cleaned_data.get("expiry_time")
        if expiry and expiry <= timezone.now():
            raise forms.ValidationError("Expiry time must be in the future.")
        return expiry

    def clean_food_type(self):
        ft = self.cleaned_data.get("food_type")
        valid = [choice[0] for choice in FoodDonation.FOOD_TYPE_CHOICES]
        if ft not in valid:
            raise forms.ValidationError("Please select a valid food type.")
        return ft

    def clean(self):
        cleaned = super().clean()
        lat     = cleaned.get("latitude")
        lng     = cleaned.get("longitude")
        address = cleaned.get("pickup_address", "").strip()

        # Quantize coordinates to exactly 6 decimal places using Decimal arithmetic.
        # round(float, 6) is NOT sufficient — Python floats have binary noise that
        # can survive rounding (e.g. 17.38504400000001 → 17.385044000000002).
        # Decimal.quantize() truncates the string representation precisely.
        SIX_DP = Decimal("0.000001")
        if lat is not None:
            try:
                lat = Decimal(str(lat)).quantize(SIX_DP, rounding=ROUND_HALF_UP)
                cleaned["latitude"] = lat
            except Exception:
                self.add_error("latitude", "Invalid latitude value.")
                lat = None

        if lng is not None:
            try:
                lng = Decimal(str(lng)).quantize(SIX_DP, rounding=ROUND_HALF_UP)
                cleaned["longitude"] = lng
            except Exception:
                self.add_error("longitude", "Invalid longitude value.")
                lng = None

        has_coords = lat is not None and lng is not None

        # Accept coords OR a typed address — at least one must be present
        if not address and not has_coords:
            self.add_error(
                "pickup_address",
                "Please enter a pickup address or use the GPS button.",
            )

        # If GPS was used but address left blank, store coords as fallback text
        if not address and has_coords:
            cleaned["pickup_address"] = f"GPS location: {lat:.6f}, {lng:.6f}"

        # Validate coordinate range (compare as float — Decimal supports this)
        if lat is not None:
            if not (Decimal("-90") <= lat <= Decimal("90")):
                self.add_error("latitude", "Latitude must be between -90 and 90.")
        if lng is not None:
            if not (Decimal("-180") <= lng <= Decimal("180")):
                self.add_error("longitude", "Longitude must be between -180 and 180.")

        return cleaned


# ---------------------------------------------------------------------------
# 4. Volunteer Profile Update Form
# ---------------------------------------------------------------------------

class VolunteerProfileUpdateForm(forms.ModelForm):
    """
    Allows volunteers (and donors) to update their profile details.
    Also exposes first_name / last_name on the underlying User object.
    """

    # Extra fields pulled from User model
    first_name = forms.CharField(
        max_length=75,
        required=False,
        widget=forms.TextInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "First name",
        }),
        label="First Name",
    )

    last_name = forms.CharField(
        max_length=75,
        required=False,
        widget=forms.TextInput(attrs={
            "class":       TEXT_INPUT,
            "placeholder": "Last name",
        }),
        label="Last Name",
    )

    class Meta:
        model  = UserProfile
        fields = [
            "full_name",
            "phone",
            "city",
            "organization_name",
            "profile_image",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class":       TEXT_INPUT,
                "placeholder": "Your full name",
            }),
            "phone": forms.TextInput(attrs={
                "class":       TEXT_INPUT,
                "placeholder": "+91 98765 43210",
            }),
            "city": forms.TextInput(attrs={
                "class":       TEXT_INPUT,
                "placeholder": "Mumbai",
            }),
            "organization_name": forms.TextInput(attrs={
                "class":       TEXT_INPUT,
                "placeholder": "Restaurant / NGO / Organization (optional)",
            }),
            "profile_image": CleanFileInput(attrs={
                "class":   FILE_INPUT,
                "accept":  "image/*",
            }),
        }
        labels = {
            "full_name":         "Full Name",
            "phone":             "Phone Number",
            "city":              "City",
            "organization_name": "Organization",
            "profile_image":     "Profile Photo",
        }

    def __init__(self, *args, **kwargs):
        # Accept the User instance so we can pre-populate name fields
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial  = self.user.last_name

    # ── Validation ───────────────────────────────────────────────────────────

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            digits = "".join(c for c in phone if c.isdigit())
            if len(digits) < 7:
                raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean_full_name(self):
        name = self.cleaned_data.get("full_name", "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Full name must be at least 2 characters.")
        return name

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Save profile FIRST (writes image file to disk before signal can fire)
            profile.save()
        if self.user:
            self.user.first_name = self.cleaned_data.get("first_name", "")
            self.user.last_name  = self.cleaned_data.get("last_name", "")
            if commit:
                # Save user AFTER profile so the signal's profile.save()
                # doesn't overwrite the freshly-saved profile_image
                self.user.save()
        return profile


# ---------------------------------------------------------------------------
# 5. Delivery Confirmation Form
# ---------------------------------------------------------------------------

class DeliveryConfirmationForm(forms.ModelForm):
    """
    Used by volunteers when marking a donation as Delivered.
    Requires a proof photo; GPS coordinates are captured automatically via
    the browser Geolocation API and submitted as hidden form fields.
    """

    # GPS hidden fields — populated by JavaScript, not model fields directly
    delivery_latitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "delivery_latitude"}),
    )
    delivery_longitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "delivery_longitude"}),
    )

    class Meta:
        model  = FoodDonation
        fields = [
            "delivery_location",
            "delivery_image",
            "delivery_latitude",
            "delivery_longitude",
        ]
        widgets = {
            "delivery_location": forms.Textarea(attrs={
                "class":       TEXTAREA,
                "placeholder": "Where was the food delivered? (area / landmark)",
                "rows":        2,
            }),
            "delivery_image": CleanFileInput(attrs={
                "class":   FILE_INPUT,
                "accept":  "image/*",
            }),
        }
        labels = {
            "delivery_location":  "Delivery Location",
            "delivery_image":     "Delivery Proof Photo",
        }
        help_texts = {
            "delivery_image": "Take a photo of the food being handed over as proof of delivery.",
        }

    # ── Validation ───────────────────────────────────────────────────────────

    def clean_delivery_image(self):
        image = self.cleaned_data.get("delivery_image")
        if not image:
            raise forms.ValidationError(
                "A delivery photo is required to confirm the delivery."
            )
        if hasattr(image, "size") and image.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Image file is too large. Maximum size is 8 MB.")
        return image

    def clean_delivery_location(self):
        loc = self.cleaned_data.get("delivery_location", "").strip()
        if len(loc) < 5:
            raise forms.ValidationError(
                "Please provide a meaningful delivery location (min 5 characters)."
            )
        return loc

    def clean(self):
        cleaned = super().clean()
        SIX_DP = Decimal("0.000001")

        lat = cleaned.get("delivery_latitude")
        lng = cleaned.get("delivery_longitude")

        # Quantize to exactly 6dp to avoid DecimalField digit-overflow
        # from GPS floating-point noise (e.g. 17.38504400000001)
        if lat is not None:
            try:
                lat = Decimal(str(lat)).quantize(SIX_DP, rounding=ROUND_HALF_UP)
                cleaned["delivery_latitude"] = lat
            except Exception:
                cleaned["delivery_latitude"] = None

        if lng is not None:
            try:
                lng = Decimal(str(lng)).quantize(SIX_DP, rounding=ROUND_HALF_UP)
                cleaned["delivery_longitude"] = lng
            except Exception:
                cleaned["delivery_longitude"] = None

        return cleaned

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self, commit=True):
        donation = super().save(commit=False)
        donation.status           = "delivered"
        donation.delivery_time    = timezone.now()
        # Persist GPS coordinates if captured
        lat = self.cleaned_data.get("delivery_latitude")
        lng = self.cleaned_data.get("delivery_longitude")
        if lat is not None:
            donation.delivery_latitude  = lat
        if lng is not None:
            donation.delivery_longitude = lng
        if commit:
            donation.save()
        return donation