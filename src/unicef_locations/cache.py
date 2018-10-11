# -*- coding: utf-8 -*-
import uuid
from functools import wraps

from django.core.cache import cache
from django.utils.cache import patch_cache_control
from django.utils.text import slugify
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from .config import conf


def get_cache_version():
    return cache.get(conf.CACHE_VERSION_KEY) or 0


def invalidate_cache():
    """
    Invalidate the locations etag in the cache on every change.
    """
    try:
        cache.incr(conf.CACHE_VERSION_KEY)
    except ValueError:
        cache.set(conf.CACHE_VERSION_KEY, 1)


def get_cache_key(request: Request):
    url = str(request._request.get_raw_uri())
    return 'locations-etag-%s-%s' % (get_cache_version(), slugify(url))


def etag_cached(cache_key: str, public_cache=False):
    """
    Returns list of instances only if there's a new ETag, and it does not
    match the one sent along with the request.
    Otherwise it returns 304 NOT MODIFIED.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            key = conf.GET_CACHE_KEY(self.request)

            cache_etag = cache.get(key)
            request_etag = self.request.META.get("HTTP_IF_NONE_MATCH", None)

            local_etag = cache_etag if cache_etag else '"{}"'.format(uuid.uuid4().hex)

            if cache_etag and request_etag and cache_etag == request_etag:
                response = Response(status=status.HTTP_304_NOT_MODIFIED)
            else:
                response = func(self, *args, **kwargs)
                response["ETag"] = local_etag

            if not cache_etag:
                cache.set(key, local_etag)

            patch_cache_control(response, private=True, must_revalidate=True)
            return response

        # def invalidate():
        #     cache.delete(key)
        # wrapper.invalidate = invalidate
        return wrapper

    return decorator
