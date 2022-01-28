from rest_framework import serializers

from unicef_locations.locations.models import LocationRemapHistory
from unicef_locations.utils import get_location_model

from .models import CartoDBTable, GatewayType


class CartoDBTableSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = CartoDBTable
        fields = (
            'id',
            'domain',
            'api_key',
            'table_name',
            'display_name',
            'pcode_col',
            'color',
            'location_type',
            'name_col'
        )


class GatewayTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = GatewayType
        fields = ('name', 'admin_level')


class LocationLightSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    name_display = serializers.CharField(source='__str__')
    name = serializers.SerializerMethodField()
    gateway = GatewayTypeSerializer()

    class Meta:
        model = get_location_model()
        fields = (
            'id',
            'name',
            'p_code',
            'gateway',
            'parent',
            'name_display'
        )

    @staticmethod
    def get_name(obj):
        return '{}{}'.format(
            str(obj),
            " -- {}".format(obj.parent.name) if obj.parent else "",
        )


class LocationSerializer(LocationLightSerializer):

    geo_point = serializers.StringRelatedField()

    class Meta(LocationLightSerializer.Meta):
        model = get_location_model()
        fields = LocationLightSerializer.Meta.fields + ('geo_point', )


class LocationExportSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='__str__')
    location_type = serializers.CharField(source='gateway.name')
    geo_point = serializers.StringRelatedField()
    point = serializers.StringRelatedField()

    class Meta:
        model = get_location_model()
        fields = "__all__"


class LocationExportFlatSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='__str__')
    location_type = serializers.CharField(source='gateway.name')
    geom = serializers.SerializerMethodField()
    point = serializers.StringRelatedField()

    class Meta:
        model = get_location_model()
        fields = "__all__"

    def get_geom(self, obj):
        return obj.geom.point_on_surface if obj.geom else ""


class LocationRemapHistorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='__str__')

    class Meta:
        model = LocationRemapHistory
        fields = "__all__"
