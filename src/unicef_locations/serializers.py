from rest_framework import serializers

from .models import CartoDBTable
from .utils import get_location_model


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
            'name_col'
        )


class LocationLightSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    name_display = serializers.CharField(source='__str__')
    name = serializers.SerializerMethodField()

    class Meta:
        model = get_location_model()
        fields = (
            'id',
            'name',
            'p_code',
            'admin_level',
            'admin_level_name',
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
    geo_point = serializers.StringRelatedField()
    point = serializers.StringRelatedField()

    class Meta:
        model = get_location_model()
        fields = "__all__"


class LocationExportFlatSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='__str__')
    geom = serializers.SerializerMethodField()
    point = serializers.StringRelatedField()

    class Meta:
        model = get_location_model()
        fields = "__all__"

    def get_geom(self, obj):
        return obj.geom.point_on_surface if obj.geom else ""
