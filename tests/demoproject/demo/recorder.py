# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import os
import pickle

import decorator
from adminactions.export import ForeignKeysCollector
from django.db import IntegrityError

from pytest import fail

try:
    from concurrency.api import disable_concurrency
except ImportError:
    disable_concurrency = lambda z: True  #

BASEDIR = os.path.dirname(__file__)
FILENAME_BASE_FIXTURE = 'fixture'
FILENAME_BASE_RECORD = 'response'


def mktree(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired "
                      "dir, '%s', already exists." % newdir)
    else:
        os.makedirs(newdir)


class Dummy(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Recorder(object):
    """
    Recorder aims to simplify request/response tests.

    it register the initial response and any further tests will be checked
    against the first stored response. Be sure the first one is correct.

    To work with dynamically created fixtures it provides a decorator do
    'freeze()' produced fixtures so to use always the same values.

    Example:
        the following example will produce two files into `recorder` dir
        test_exchangerate-fixture-exchange_rate.pickle and
        test_exchangerate-record-unexchangerate-list-std.pickle

    recorder = Recorder.new(__file__)

    @pytest.fixture()
    @recorder.freeze
    def exchange_rate():
        return G(UNExchangeRate,
        since=datetime.date(2015, 9, 1),
        rate=0.88900,
        currency_code='EUR',
        currency=None)

    @pytest.mark.django_db
    def test_exchange_rate_all_serializer(client_application, exchange_rate, serializer):

        url = reverse('unexchangerate-list')
        with recorder('unexchangerate-list', serializer, client_application) as tape:

            res = client_application.get("{}?serializer={}".format(url, serializer))
            assert res.json['count'] == 1
            response = res.json['results'][0]
            tape.assert_response(response)

    """

    def __init__(self, viewname, serializer, client):
        self.viewname = viewname
        self.serializer = serializer
        self.client = client
        self._original_get = self.client.get
        self._response = None

    def __getattr__(self, item):
        return getattr(self._response, item)

    @classmethod
    def new(self, f):
        return type('Recorder', (Recorder,), {'CALLER_FILE': f,
                                              'basedir': os.path.dirname(f),
                                              'caller': os.path.basename(f).replace('.py', '')
                                              })

    @property
    def filename(self):
        return self.get_filename("{}-{}-{}".format(FILENAME_BASE_RECORD, self.viewname,
                                                   self.serializer))

    def _load(self):
        if os.path.exists(self.filename):
            self._response = pickle.load(open(self.filename, 'rb'))

    @classmethod
    def get_filename(cls, *parts):
        filename = os.path.join(cls.basedir, "recorder",
                                "{}-{}.pickle".format(cls.caller, "-".join(parts)))
        if not os.path.exists(filename):
            mktree(os.path.dirname(filename))
        return filename

    def _save(self, res):
        c = Dummy(status_code=res.status_code,
                  content=res.content,
                  json=res.json)
        pickle.dump(c, open(self.filename, 'wb'), -1)

    # def get(self, suffix):
    #     url = "{}?{}".format(self.viewname, suffix)
    #     res = self._original_get(url)
    #     if not os.path.exists(self.filename):
    #         self._save(res)
    #         self._load()
    #     return res

    def _get(self, url, *args, **kwargs):
        res = self._original_get(url, *args, **kwargs)
        if not os.path.exists(self.filename):
            self._save(res)
            self._load()
        return res

    def __enter__(self):
        self._original_get, self.client.get = self.client.get, self._get
        self._load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.get = self._original_get

    @classmethod
    def freeze(cls, empty_table=True):
        def inner(func):
            filename = cls.get_filename(FILENAME_BASE_FIXTURE, func.__name__)

            def wrapper(func, *args, **kwargs):
                if not os.path.exists(filename):
                    ret = func(*args, **kwargs)
                    try:
                        os.makedirs(os.path.join(cls.basedir, "recorder"))
                    except OSError:
                        pass
                    pickle.dump(ret, open(filename, 'wb'))
                    return ret
                try:
                    ret = pickle.load(open(filename, 'rb'))
                    if empty_table:
                        ret.__class__.objects.all().delete()
                    if hasattr(ret.__class__, '_concurrencymeta'):
                        with disable_concurrency(ret.__class__):
                            ret.save()
                    else:
                        ret.save(force_insert=True)
                    return ret
                except IntegrityError as e:
                    raise IntegrityError(f'Invalid fixture {filename}: {e}')
                except AttributeError as e:
                    raise AttributeError(f'Invalid fixture {filename}: {e}')

            return decorator.decorator(wrapper, func)

        return inner

    @classmethod
    def freeze2(cls):
        def inner(func):

            filename = cls.get_filename(FILENAME_BASE_FIXTURE, func.__name__)

            def wrapper(func, *args, **kwargs):
                if not os.path.exists(filename):
                    ret = func(*args, **kwargs)

                    c = ForeignKeysCollector(None)
                    c.collect([ret])
                    pickle.dump(c.data, open(filename, 'wb'))
                try:
                    ret = pickle.load(open(filename, 'rb'))
                    _visited = []
                    for e in reversed(ret):
                        if e.__class__ not in _visited:
                            e.__class__.objects.all().delete()
                            _visited.append(e.__class__)
                        if hasattr(e.__class__, '_concurrencymeta'):
                            with disable_concurrency(e.__class__):
                                e.save()
                        else:
                            e.save(force_insert=True)
                    return ret[0]
                except IntegrityError as e:
                    raise IntegrityError('Invalid fixture {}: {}'.format(filename, e))
                except AttributeError as e:
                    raise AttributeError('Invalid fixture {}: {}'.format(filename, e))

            return decorator.decorator(wrapper, func)

        return inner

    def assert_response(self, response, ignore_fields=None):
        stored = self.json[0]
        response = response.json[0]
        ignore_fields = ignore_fields or []
        # assert bool(key in stored.keys() for key in response.keys())

        for field, value in response.items():
            if field not in ignore_fields:
                if field in stored:
                    assert response[field] == stored[field], \
                        rf"""Error in tape {self.filename}
    field `{field}` does not match.
    - expected: `{stored[field]}`
    - received: `{response[field]}`"""

        # if the length is different that means that we added
        # some field. (we already checked that old fields exist
        if not sorted(response.keys()) == sorted(stored.keys()):
            fail(f"""Test succeed but action needed.
{self.filename} tape need rebuild'
The following field(s) have been added to `{self.serializer}` Serializer
`%s`""" % [f for f in response.keys() if f not in stored.keys()])
        return True
