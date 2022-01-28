from django.db import models

from unicef_locations.locations.models import Location


class DemoModel(models.Model):

    name = models.CharField(max_length=50)
    country = models.ForeignKey(Location, on_delete=models.CASCADE)
