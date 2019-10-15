import logging

from django.contrib.gis.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import ugettext as _
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey

from .cache import invalidate_cache
from .libs import get_random_color

logger = logging.getLogger(__name__)


class GatewayType(TimeStampedModel):
    """
    Represents an Admin Type in location-related models.
    """

    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    admin_level = models.PositiveSmallIntegerField(null=True, unique=True, verbose_name=_('Admin Level'))

    class Meta:
        ordering = ['name']
        verbose_name = _('Location Type')

    def __str__(self):
        return self.name


class LocationsManager(TreeManager):
    def get_queryset(self):
        return super(LocationsManager, self).get_queryset().filter(is_active=True)\
            .order_by('name').select_related('gateway')

    def archived_locations(self):
        return super(LocationsManager, self).get_queryset().filter(is_active=False)\
            .order_by('name').select_related('gateway')

    def all_locations(self):
        return super(LocationsManager, self).get_queryset()\
            .order_by('name').select_related('gateway')


class Location(TimeStampedModel, MPTTModel):
    """
    Represents Location, either a point or geospatial object,
    pcode should be unique

    Relates to :model:`locations.GatewayType`
    """

    name = models.CharField(verbose_name=_("Name"), max_length=254)
    gateway = models.ForeignKey(
        GatewayType, verbose_name=_('Location Type'),
        on_delete=models.CASCADE,
    )
    latitude = models.FloatField(
        verbose_name=_("Latitude"),
        null=True,
        blank=True,
    )
    longitude = models.FloatField(
        verbose_name=_("Longitude"),
        null=True,
        blank=True,
    )
    p_code = models.CharField(
        verbose_name=_("P Code"),
        max_length=32,
        blank=True,
        default='',
    )

    parent = TreeForeignKey(
        'self',
        verbose_name=_("Parent"),
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.CASCADE
    )
    geom = models.MultiPolygonField(
        verbose_name=_("Geo Point"),
        null=True,
        blank=True,
    )
    point = models.PointField(verbose_name=_("Point"), null=True, blank=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True, blank=True)
    created = AutoCreatedField(_('created'))
    modified = AutoLastModifiedField(_('modified'))

    objects = LocationsManager()

    def __str__(self):
        # TODO: Make generic
        return u'{} ({} {}: {})'.format(
            self.name,
            self.gateway.name,
            'CERD' if self.gateway.name == 'School' else 'PCode',
            self.p_code if self.p_code else ''
        )

    @property
    def geo_point(self):
        return self.point if self.point else self.geom.point_on_surface if self.geom else ""

    @property
    def point_lat_long(self):
        return "Lat: {}, Long: {}".format(
            self.point.y,
            self.point.x
        )

    class Meta:
        unique_together = ('name', 'gateway', 'p_code')
        ordering = ['name']


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


@receiver(post_delete, sender=Location)
@receiver(post_save, sender=Location)
def invalidate_locations_etag(sender, instance, **kwargs):
    """
    Invalidate the locations etag in the cache on every change.
    """
    invalidate_cache()


class CartoDBTable(TimeStampedModel, MPTTModel):
    """
    Represents a table in CartoDB, it is used to import locations

    Relates to :model:`locations.GatewayType`
    """

    domain = models.CharField(max_length=254, verbose_name=_('Domain'))
    api_key = models.CharField(max_length=254, verbose_name=_('API Key'))
    table_name = models.CharField(max_length=254, verbose_name=_('Table Name'))
    display_name = models.CharField(max_length=254, default='', blank=True, verbose_name=_('Display Name'))
    location_type = models.ForeignKey(
        GatewayType, verbose_name=_('Location Type'),
        on_delete=models.CASCADE,
    )
    name_col = models.CharField(max_length=254, default='name', verbose_name=_('Name Column'))
    pcode_col = models.CharField(max_length=254, default='pcode', verbose_name=_('Pcode Column'))
    # Cartodb table name used to remap old pcodes to new pcodes
    remap_table_name = models.CharField(max_length=254, verbose_name=_('Remap Table Name'), blank=True, null=True)
    parent_code_col = models.CharField(max_length=254, default='', blank=True, verbose_name=_('Parent Code Column'))
    parent = TreeForeignKey(
        'self', null=True, blank=True, related_name='children', db_index=True,
        verbose_name=_('Parent'),
        on_delete=models.CASCADE,
    )
    color = models.CharField(blank=True, default=get_random_color, max_length=7, verbose_name=_('Color'))

    def __str__(self):
        return self.table_name

    class Meta:
        app_label = 'locations'


class ArcgisDBTable(TimeStampedModel, MPTTModel):
    """
    Represents a table in Arcgis Online, it is used to import locations

    Relates to :model:`locations.GatewayType`
    """

    service_url = models.CharField(max_length=512, verbose_name=_('Service URL'))
    service_name = models.CharField(max_length=254, verbose_name=_('Service Name'))
    location_type = models.ForeignKey(
        GatewayType, verbose_name=_('Location Type'),
        on_delete=models.CASCADE,
    )
    name_col = models.CharField(max_length=254, default='name', verbose_name=_('Name Column'))
    pcode_col = models.CharField(max_length=254, default='pcode', verbose_name=_('Pcode Column'))
    # AOS table name used to remap old pcodes to new pcodes
    remap_table_service_url = models.CharField(
        max_length=512,
        verbose_name=_('Remap Table Service URL'),
        blank=True,
        null=True
    )
    parent_code_col = models.CharField(max_length=254, default='', blank=True, verbose_name=_('Parent Code Column'))
    parent = TreeForeignKey(
        'self', null=True, blank=True, related_name='children', db_index=True,
        verbose_name=_('Parent'),
        on_delete=models.CASCADE,
    )
    color = models.CharField(blank=True, default=get_random_color, max_length=7, verbose_name=_('Color'))

    def __str__(self):
        return self.service_name

    class Meta:
        app_label = 'locations'
