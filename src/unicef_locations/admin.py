from django import forms
from django.contrib import admin as basic_admin
from django.contrib.gis import admin
from django.forms import Textarea
from django.utils.translation import ugettext_lazy as _

from leaflet.admin import LeafletGeoAdmin
from mptt.admin import MPTTModelAdmin

from .forms import CartoDBTableForm
from .models import CartoDBTable, GatewayType, Location
from .tasks import update_sites_from_cartodb


class AutoSizeTextForm(forms.ModelForm):
    """
    Use textarea for name and description fields
    """

    class Meta:
        widgets = {
            'name': Textarea(),
            'description': Textarea(),
        }


class ActiveLocationsFilter(basic_admin.SimpleListFilter):

    title = 'Active Status'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):

        return [
            (True, 'Active'),
            (False, 'Archived')
        ]

    def queryset(self, request, queryset):

        value = self.value()

        if value == 'True':
            return Location.objects
        elif value == 'False':
            return Location.archived_locations
        else:
            return Location.all_locations


class LocationAdmin(LeafletGeoAdmin, MPTTModelAdmin):
    save_as = True
    form = AutoSizeTextForm
    fields = [
        'name',
        'gateway',
        'p_code',
        'geom',
        'point',
    ]
    list_display = (
        'name',
        'gateway',
        'p_code',
        'is_active',
    )
    list_filter = (
        'gateway',
        ActiveLocationsFilter,
        'parent',
    )
    search_fields = ('name', 'p_code',)

    def get_form(self, request, obj=None, **kwargs):
        self.readonly_fields = [] if request.user.is_superuser else ['p_code', 'geom', 'point', 'gateway']

        return super(LocationAdmin, self).get_form(request, obj, **kwargs)


class CartoDBTableAdmin(admin.ModelAdmin):
    form = CartoDBTableForm
    save_as = True
    list_display = (
        'table_name',
        'location_type',
        'name_col',
        'pcode_col',
        'parent_code_col',
    )

    actions = ('import_sites',)

    def import_sites(self, request, queryset):
        for table in queryset:
            update_sites_from_cartodb.delay(table.pk)


admin.site.register(Location, LocationAdmin)
admin.site.register(GatewayType)
admin.site.register(CartoDBTable, CartoDBTableAdmin)
