from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile whenever a new User is created."""
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={"full_name": instance.get_full_name() or instance.username},
        )


@receiver(post_save, sender=User)
def sync_user_profile_name(sender, instance, created, **kwargs):
    """
    Sync first_name / last_name changes from User → UserProfile.full_name.
    Deliberately does NOT call profile.save() for the whole object — that
    would overwrite profile_image with whatever value is currently in the
    ORM cache, which may not have the newly-uploaded file yet.
    Only runs on UPDATE (not on initial creation, which is handled above).
    """
    if created:
        return  # handled by create_user_profile
    try:
        profile = instance.profile
    except UserProfile.DoesNotExist:
        return

    # Only update full_name if it looks like a default/empty value
    # (i.e. user changed their Django first/last name and we want to reflect it)
    new_full = (
        f"{instance.first_name} {instance.last_name}".strip()
        or instance.username
    )
    if new_full and profile.full_name != new_full and not profile.full_name:
        # Only auto-sync if profile.full_name is blank (user hasn't set a custom name)
        UserProfile.objects.filter(pk=profile.pk).update(full_name=new_full)