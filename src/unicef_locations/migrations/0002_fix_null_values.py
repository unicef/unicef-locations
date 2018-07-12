from django.db import migrations


def fix_null_values(model, field_names, new_value=''):
    """
    For each fieldname, update any records in 'model' where the field's value is NULL
    to be an empty string instead (or whatever new_value is)
    """
    for name in field_names:
        model._default_manager.filter(**{name: None}).update(**{name: new_value})


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('locations.cartodbtable'),
        [
            'color',
            'display_name',
            'parent_code_col',
        ]
    )
    fix_null_values(
        apps.get_model('locations.location'),
        [
            'p_code',
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        (u'locations', u'0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
