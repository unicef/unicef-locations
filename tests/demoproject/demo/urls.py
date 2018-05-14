from django.conf.urls import url, include
from django.contrib import admin
from rest_framework import routers

from unicef_locations.views import LocationsViewSet, LocationsLightViewSet, LocationTypesViewSet

api = routers.SimpleRouter()

api.register(r'locations', LocationsViewSet, base_name='locations')
api.register(r'locations-light', LocationsLightViewSet, base_name='locations-light')
api.register(r'locations-types', LocationTypesViewSet, base_name='locationtypes')

urlpatterns = [
    url(r'^api/', include(api.urls)),
    url(
        r'^api/locations/pcode/(?P<p_code>\w+)/$',
        LocationsViewSet.as_view({
            'get': 'retrieve'
        }),
        name='locations_detail_pcode'
    ),
    url(r'^admin/', admin.site.urls),
    url(r'', include('unicef_locations.urls')),
]
