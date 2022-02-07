from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin
from carto.sql import SQLClient
from django import forms
from django.contrib import admin as basic_admin, messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.gis import admin
from django.forms import Textarea
from django.http import HttpResponse
from django.template import loader
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from leaflet.admin import LeafletGeoAdmin
from mptt.admin import MPTTModelAdmin

from unicef_locations.auth import LocationsCartoNoAuthClient
from unicef_locations.utils import get_location_model, get_remapping

from .forms import CartoDBTableForm
from .models import CartoDBTable, GatewayType
from .tasks import import_locations


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
        return queryset.filter(**self.used_parameters)


class LocationAdmin(LeafletGeoAdmin, MPTTModelAdmin):
    save_as = True
    form = AutoSizeTextForm

    list_display = (
        'name',
        'admin_level',
        'admin_level_name',
        'p_code',
        'is_active',
    )
    list_filter = (
        ActiveLocationsFilter,
        'parent',
    )
    search_fields = ('name', 'p_code',)
    raw_id_fields = ('parent', )

    def get_queryset(self, request):    # pragma: no-cover
        qs = get_location_model().objects.all()

        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_form(self, request, obj=None, **kwargs):
        self.readonly_fields = [] if request.user.is_superuser else ['p_code', 'geom', 'point', 'admin_level']

        return super().get_form(request, obj, **kwargs)


class CartoDBTableAdmin(ExtraUrlMixin, admin.ModelAdmin):
    form = CartoDBTableForm
    save_as = True
    list_display = (
        'table_name',
        'name_col',
        'pcode_col',
        'parent_code_col',
        'import_table',
    )

    def import_table(self, obj):
        try:
            url = reverse(admin_urlname(obj._meta, 'import_sites'), args=[obj.pk])
            return format_html(f'<a href="{url}">Import</a>')
        except NoReverseMatch:
            return '-'

    @button(css_class="btn-warning auto-disable")
    def import_sites(self, request, pk):
        import_locations.delay(pk)
        messages.info(request, 'Import Scheduled')

    @button(css_class="btn-warning auto-disable")
    def show_remap_table(self, request, pk):
        carto_table = CartoDBTable.objects.get(pk=pk)
        sql_client = SQLClient(LocationsCartoNoAuthClient(base_url=f"https://{carto_table.domain}.carto.com/"))
        old2new, to_deactivate = get_remapping(sql_client, carto_table)
        template = loader.get_template('admin/location_remap.html')
        context = {
            'old2new': old2new,
            'to_deactivate': to_deactivate
        }
        return HttpResponse(template.render(context, request))


admin.site.register(get_location_model(), LocationAdmin)
admin.site.register(GatewayType)
admin.site.register(CartoDBTable, CartoDBTableAdmin)
