# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.urls import get_callable


class AppSettings(object):
    defaults = {
        'GET_CACHE_KEY': 'unicef_locations.cache.get_cache_key',
        'CACHE_VERSION_KEY': 'locations-etag-version',
    }

    def __init__(self, prefix):
        """
        Loads our settings from django.conf.settings, applying defaults for any
        that are omitted.
        """
        self.prefix = prefix
        setting_changed.connect(self._handler)

    def __getattr__(self, name):
        if name in self.defaults.keys():
            from django.conf import settings
            name_with_prefix = (self.prefix + '_' + name).upper()
            raw_value = getattr(settings, name_with_prefix, self.defaults[name])
            value = self._set_attr(name_with_prefix, raw_value)
            setattr(settings, name_with_prefix, raw_value)
            setting_changed.send(self.__class__, setting=name_with_prefix, value=raw_value, enter=True)
            return value
        return super(AppSettings, self).__getattr__(name)

    def _set_attr(self, prefix_name, value):
        name = prefix_name[len(self.prefix) + 1:]
        if name in ('GET_CACHE_KEY', 'GET_CACHE_VERSION'):
            try:
                if isinstance(value, str):
                    func = get_callable(value)
                elif callable(value):
                    func = value
                else:
                    raise ImproperlyConfigured(
                        f"{value} is not a valid value for `{name}`. "
                        "It must be a callable or a fullpath to callable. ")
            except Exception as e:
                raise ImproperlyConfigured(e)
            setattr(self, name, func)
            return func
        else:
            setattr(self, name, value)
            return value

    def _handler(self, sender, setting, value, **kwargs):
        """
            handler for ``setting_changed`` signal.

        @see :ref:`django:setting-changed`_
        """
        if setting.startswith(self.prefix):
            name = setting[len(self.prefix) + 1:]
            try:
                delattr(self, name)
            except AttributeError:
                pass


conf = AppSettings('UNICEF_LOCATIONS')
