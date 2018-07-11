# -*- coding: utf-8 -*-
import random
import uuid
from functools import wraps

from django.core.cache import cache
from django.db import connection
from django.utils.cache import patch_cache_control

from rest_framework import status
from rest_framework.response import Response


def fix_null_values(model, field_names, new_value=''):
    """
    For each fieldname, update any records in 'model' where the field's value is NULL
    to be an empty string instead (or whatever new_value is)
    """
    for name in field_names:
        model._default_manager.filter(**{name: None}).update(**{name: new_value})


def get_random_color():
    return '#%02X%02X%02X' % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


def make_cache_key(cache_key='locations', public_cache=False):
    if public_cache:
        schema_name = 'public'
    else:
        schema_name = connection.schema_name

    return '{}-{}-etag'.format(schema_name, cache_key)


def etag_cached(cache_key: str, public_cache=False):
    """
    Returns list of instances only if there's a new ETag, and it does not
    match the one sent along with the request.
    Otherwise it returns 304 NOT MODIFIED.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):

            cache_etag = cache.get(make_cache_key())
            request_etag = self.request.META.get("HTTP_IF_NONE_MATCH", None)

            local_etag = cache_etag if cache_etag else '"{}"'.format(uuid.uuid4().hex)

            if cache_etag and request_etag and cache_etag == request_etag:
                response = Response(status=status.HTTP_304_NOT_MODIFIED)
            else:
                response = func(self, *args, **kwargs)
                response["ETag"] = local_etag

            if not cache_etag:
                cache.set(make_cache_key(cache_key, public_cache), local_etag)

            patch_cache_control(response, private=True, must_revalidate=True)
            return response

        def invalidate():
            cache.delete(make_cache_key())

        wrapper.invalidate = invalidate
        return wrapper

    return decorator
