from django.contrib import admin

from unicef_locations.admin import LocationAdmin
from unicef_locations.locations.models import Location

admin.site.register(Location, LocationAdmin)
