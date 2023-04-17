from django.db import models

from unicef_locations.models import AbstractLocation


class Location(AbstractLocation):
    class Meta:
        app_label = "sample"


class DemoModel(models.Model):
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="countries")
    capital = models.ForeignKey(Location, related_name="capitals", blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        app_label = "sample"
