from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

import factory
from factory import fuzzy

from demo.sample import models


class DemoModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DemoModel


class UserFactory(factory.django.DjangoModelFactory):
    username = fuzzy.FuzzyText(length=50)

    class Meta:
        model = get_user_model()


class PermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Permission
        django_get_or_create = ("codename",)
