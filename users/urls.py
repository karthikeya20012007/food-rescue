from django.urls import path
from . import views

urlpatterns = [

    # ── Public ────────────────────────────────────────────────────────────────
    path("",                    views.landing,      name="landing"),
    path("impact/",             views.impact_feed,  name="impact_feed"),

    # ── Auth ──────────────────────────────────────────────────────────────────
    path("register/",           views.register_view, name="register"),
    path("login/",              views.login_view,    name="login"),
    path("logout/",             views.logout_view,   name="logout"),

    # ── Notifications (AJAX) ──────────────────────────────────────────────────
    path("notifications/",      views.notifications_json,      name="notifications_json"),
    path("notifications/read/", views.mark_notifications_read, name="mark_notifications_read"),

    # ── Profile ───────────────────────────────────────────────────────────────
    path("profile/",            views.volunteer_profile,    name="volunteer_profile"),
    path("profile/remove-photo/", views.remove_profile_image, name="remove_profile_image"),
    path("profile/change-password/", views.change_password_view, name="change_password"),

    # ── Donor ─────────────────────────────────────────────────────────────────
    path("donor/",                            views.donor_dashboard, name="donor_dashboard"),
    path("donor/donate/",                     views.create_donation, name="create_donation"),
    path("donor/donate/<int:pk>/edit/",       views.edit_donation,   name="edit_donation"),
    path("donor/donate/<int:pk>/cancel/",     views.cancel_donation, name="cancel_donation"),
    path("donation/<int:pk>/",                views.donation_detail, name="donation_detail"),

    # ── Volunteer ─────────────────────────────────────────────────────────────
    path("volunteer/",                        views.volunteer_dashboard, name="volunteer_dashboard"),
    path("volunteer/<int:pk>/accept/",        views.accept_pickup,       name="accept_pickup"),
    path("volunteer/<int:pk>/cancel/",        views.cancel_pickup,       name="cancel_pickup"),
    path("volunteer/<int:pk>/picked-up/",     views.mark_picked_up,      name="mark_picked_up"),
    path("volunteer/<int:pk>/on-the-way/",    views.mark_on_the_way,     name="mark_on_the_way"),
    path("volunteer/<int:pk>/delivered/",     views.mark_delivered,      name="mark_delivered"),
]