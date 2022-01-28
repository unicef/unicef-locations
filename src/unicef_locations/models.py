import logging

from django.contrib.gis.db import models
from django.utils.translation import gettext as _
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey

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
        verbose_name = 'Location Type'

    def __str__(self):
        return self.name


class LocationsManager(TreeManager):

    def get_queryset(self):
        return super().get_queryset().select_related('gateway', 'parent')

    def active(self):
        return self.get_queryset().filter(is_active=True)

    def archived_locations(self):
        return self.get_queryset().filter(is_active=False)


class LocationAbstract(TimeStampedModel, MPTTModel):
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
        return u'{}{} ({}: {})'.format(
            self.name,
            '' if self.is_active else ' [Archived]',
            self.gateway.name,
            self.p_code if self.p_code else '',
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
        abstract = True


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
