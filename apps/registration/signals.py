"""Django signals for the registration app."""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import RegistrationSubmission


@receiver(post_save, sender=RegistrationSubmission)
def invalidate_pending_cache_on_save(sender, instance, **kwargs):
    """Clear the pending submissions count cache when a submission is saved."""
    cache.delete("pending_submissions_count")


@receiver(post_delete, sender=RegistrationSubmission)
def invalidate_pending_cache_on_delete(sender, instance, **kwargs):
    """Clear the pending submissions count cache when a submission is deleted."""
    cache.delete("pending_submissions_count")
