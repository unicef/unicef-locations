from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.generics import ListAPIView

from .cache import etag_cached
from .models import CartoDBTable
from .serializers import CartoDBTableSerializer, LocationLightSerializer, LocationSerializer
from .utils import get_location_model


class CartoDBTablesView(ListAPIView):
    """
    Gets a list of CartoDB tables for the mapping system
    """

    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer


class LocationsViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD for Locations
    """

    queryset = get_location_model().objects.all()
    serializer_class = LocationSerializer

    @etag_cached("locations")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_object(self):
        if "p_code" in self.kwargs:
            obj = get_object_or_404(self.get_queryset(), p_code=self.kwargs["p_code"])
            self.check_object_permissions(self.request, obj)
            return obj
        else:
            return super().get_object()

    def get_queryset(self):
        queryset = get_location_model().objects.all()
        if "values" in self.request.query_params.keys():
            # Used for ghost data - filter in all(), and return straight away.
            try:
                ids = [int(x) for x in self.request.query_params.get("values").split(",")]
            except ValueError:  # pragma: no-cover
                raise ValidationError("ID values must be integers")
            else:
                queryset = queryset.filter(id__in=ids)
        return queryset


class LocationsLightViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Returns a list of all Locations with restricted field set.
    """

    queryset = get_location_model().objects.defer(
        "geom",
    )
    serializer_class = LocationLightSerializer

    @etag_cached("locations")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LocationQuerySetView(ListAPIView):
    model = get_location_model()
    serializer_class = LocationLightSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q")
        qs = self.model.objects.defer(
            "geom",
        )

        if q:
            qs = qs.filter(name__icontains=q)

        # return maximum 7 records
        return qs.all()[:7]
