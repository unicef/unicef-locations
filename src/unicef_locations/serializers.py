from rest_framework import serializers

from .models import CartoDBTable, GatewayType, Location, LocationRemapHistory


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
        fields = '__all__'


class LocationLightSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField()
    gateway = GatewayTypeSerializer()

    @staticmethod
    def get_name(obj):
        return '{} [{} - {}]'.format(obj.name, obj.gateway.name, obj.p_code)

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'gateway',
        )


class LocationSerializer(LocationLightSerializer):

    geo_point = serializers.StringRelatedField()

    class Meta(LocationLightSerializer.Meta):
        model = Location
        fields = LocationLightSerializer.Meta.fields + ('geo_point', 'parent')


class LocationExportSerializer(serializers.ModelSerializer):
    location_type = serializers.CharField(source='gateway.name')
    geo_point = serializers.StringRelatedField()
    point = serializers.StringRelatedField()

    class Meta:
        model = Location
        fields = "__all__"


class LocationExportFlatSerializer(serializers.ModelSerializer):
    location_type = serializers.CharField(source='gateway.name')
    geom = serializers.SerializerMethodField()
    point = serializers.StringRelatedField()

    class Meta:
        model = Location
        fields = "__all__"

    def get_geom(self, obj):
        return obj.geom.point_on_surface if obj.geom else ""


class LocationRemapHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = LocationRemapHistory
        fields = "__all__"
