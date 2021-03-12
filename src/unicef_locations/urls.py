from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from . import views

app_name = 'locations'

api = routers.SimpleRouter()

api.register(r'locations', views.LocationsViewSet, basename='locations')
api.register(r'locations-light', views.LocationsLightViewSet, basename='locations-light')
api.register(r'locations-types', views.LocationTypesViewSet, basename='locationtypes')

urlpatterns = [
    re_path(r'', include(api.urls)),
    re_path(
        r'^locations/pcode/(?P<p_code>\w+)/$', views.LocationsViewSet.as_view({'get': 'retrieve'}),
        name='locations_detail_pcode'
    ),
    re_path(r'^cartodbtables/$', views.CartoDBTablesView.as_view(), name='cartodbtables'),
    re_path(r'^autocomplete/$', views.LocationQuerySetView.as_view(), name='locations_autocomplete'),
]
