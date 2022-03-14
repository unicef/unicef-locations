from django.contrib import admin

from unicef_locations.admin import LocationAdmin

from demo.sample.models import Location

admin.site.register(Location, LocationAdmin)
