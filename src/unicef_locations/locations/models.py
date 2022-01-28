from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext as _
from model_utils.fields import AutoCreatedField
from model_utils.models import TimeStampedModel
from mptt.fields import TreeForeignKey

from unicef_locations.cache import invalidate_cache
from unicef_locations.models import LocationAbstract


class Location(LocationAbstract):

    parent = TreeForeignKey(
        'self',
        verbose_name=_("Parent"),
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.CASCADE
    )


@receiver(post_delete, sender=Location)
@receiver(post_save, sender=Location)
def invalidate_locations_etag(sender, instance, **kwargs):
    """
    Invalidate the locations etag in the cache on every change.
    """
    invalidate_cache()


class LocationRemapHistory(TimeStampedModel):
    """
    Location Remap History records for the related objects(interventions, travels, activities, actions)
    """
    old_location = models.ForeignKey(
        Location,
        verbose_name=_("Old Location"),
        on_delete=models.CASCADE,
        related_name="+"
    )
    new_location = models.ForeignKey(
        Location,
        verbose_name=_("New Location"),
        on_delete=models.CASCADE,
        related_name="+"
    )
    comments = models.TextField(
        verbose_name=_('Comments'),
        blank=True,
        null=True
    )
    created = AutoCreatedField(_('created'))

    class Meta:
        verbose_name = _('Remap history')
        verbose_name_plural = _('Location remap history')
