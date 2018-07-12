# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.urls import get_callable


class AppSettings(object):
    # GET_CACHE_KEY = lambda : 'locations-etag'
    defaults = {
        'GET_CACHE_KEY': 'unicef_locations.cache.get_cache_key',
    }

    def __init__(self, prefix):
        """
        Loads our settings from django.conf.settings, applying defaults for any
        that are omitted.
        """
        self.prefix = prefix
        from django.conf import settings

        for name, default in self.defaults.items():
            prefix_name = (self.prefix + '_' + name).upper()
            value = getattr(settings, prefix_name, default)
            self._set_attr(prefix_name, value)
            setattr(settings, prefix_name, value)
            setting_changed.send(self.__class__, setting=prefix_name, value=value, enter=True)

        setting_changed.connect(self._handler)

    def _set_attr(self, prefix_name, value):
        name = prefix_name[len(self.prefix) + 1:]
        if name in ('GET_CACHE_KEY', 'GET_CACHE_VERSION'):
            if isinstance(value, str):
                func = get_callable(value)
            elif callable(value):
                func = value
            else:
                raise ImproperlyConfigured(
                    "{} is not a valid value for `GET_CACHE_KEY`. It must be a callable or a fullpath to callable. ".format(
                        value))
            setattr(self, name, func)
        else:
            setattr(self, name, value)

    def _handler(self, sender, setting, value, **kwargs):
        """
            handler for ``setting_changed`` signal.

        @see :ref:`django:setting-changed`_
        """
        if setting.startswith(self.prefix):
            self._set_attr(setting, value)


conf = AppSettings('UNICEF_LOCATIONS')
