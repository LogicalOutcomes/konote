"""Cache invalidation signals for terminology, features, and settings."""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import FeatureToggle, InstanceSetting, TerminologyOverride


@receiver([post_save, post_delete], sender=TerminologyOverride)
def invalidate_terminology_cache(sender, **kwargs):
    cache.delete("terminology_overrides")


@receiver([post_save, post_delete], sender=FeatureToggle)
def invalidate_feature_cache(sender, **kwargs):
    cache.delete("feature_toggles")


@receiver([post_save, post_delete], sender=InstanceSetting)
def invalidate_settings_cache(sender, **kwargs):
    cache.delete("instance_settings")
