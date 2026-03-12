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
def save_user_profile(sender, instance, **kwargs):
    """Keep UserProfile in sync when User is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()