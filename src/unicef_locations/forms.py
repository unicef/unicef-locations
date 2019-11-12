
import logging

from arcgis.features import FeatureLayer
from carto.exceptions import CartoException
from carto.sql import SQLClient
from django import forms
from django.core.exceptions import ValidationError

from .auth import LocationsCartoNoAuthClient
from .models import ArcgisDBTable, CartoDBTable

# from arcgis.features import FeatureSet

logger = logging.getLogger(__name__)


class CartoDBTableForm(forms.ModelForm):

    class Meta:
        model = CartoDBTable
        fields = '__all__'

    def clean(self):

        domain = self.cleaned_data['domain']
        table_name = self.cleaned_data['table_name']
        name_col = self.cleaned_data['name_col']
        pcode_col = self.cleaned_data['pcode_col']
        parent_code_col = self.cleaned_data['parent_code_col']
        remap_table_name = self.cleaned_data['remap_table_name']
        auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(str(domain)))

        sql_client = SQLClient(auth_client)
        try:
            sites = sql_client.send('select * from {} limit 1'.format(table_name))
        except CartoException:
            logger.exception("CartoDB exception occured")
            raise ValidationError("Couldn't connect to CartoDB table: {}".format(table_name))
        else:
            row = sites['rows'][0]
            if name_col not in row:
                raise ValidationError('The Name column ({}) is not in table: {}'.format(
                    name_col, table_name
                ))
            if pcode_col not in row:
                raise ValidationError('The PCode column ({}) is not in table: {}'.format(
                    pcode_col, table_name
                ))
            if parent_code_col and parent_code_col not in row:
                raise ValidationError('The Parent Code column ({}) is not in table: {}'.format(
                    parent_code_col, table_name
                ))

        if remap_table_name:
            try:
                remap_table = sql_client.send('select * from {} limit 1'.format(remap_table_name))
            except CartoException:  # pragma: no-cover
                logger.exception("CartoDB exception occured")
                raise ValidationError("Couldn't connect to the CartoDB remap table: {}".format(remap_table_name))
            else:
                row = remap_table['rows'][0]

                if 'old_pcode' not in row.keys():
                    raise ValidationError('The Old PCode column ({}) is not in table: {}'.format(
                        'old_pcode', remap_table_name
                    ))

                if 'new_pcode' not in row.keys():
                    raise ValidationError('The New PCode column ({}) is not in table: {}'.format(
                        'new_pcode', remap_table_name
                    ))

        return self.cleaned_data


class ArcgisDBTableForm(forms.ModelForm):

    class Meta:
        model = ArcgisDBTable
        fields = '__all__'

    def clean(self):
        service_url = self.cleaned_data['service_url']
        remap_table_service_url = self.cleaned_data['remap_table_service_url']
        # name_col = self.cleaned_data['name_col']
        # pcode_col = self.cleaned_data['pcode_col']
        # parent_code_col = self.cleaned_data['parent_code_col']

        try:
            # gis_auth = GIS('https://[user].maps.arcgis.com', '[user]', '[pwd]')
            # features = FeatureLayer(service_url, gis=gis_auth)
            FeatureLayer(service_url)
            # TODO: finish validating the remaining colums against the featureset fields
        except RuntimeError:
            raise ValidationError("Cannot load Arcgis dataset from: {}".format(service_url))

        if remap_table_service_url:
            try:
                # gis_auth = GIS('https://[user].maps.arcgis.com', '[user]', '[pwd]')
                # features = FeatureLayer(service_url, gis=gis_auth)
                FeatureLayer(remap_table_service_url)
                # TODO: check if new_pcode, old_pcode are present in the remap table fields
            except RuntimeError:
                raise ValidationError("Cannot load Arcgis remap table from: {}".format(remap_table_service_url))

        return self.cleaned_data
