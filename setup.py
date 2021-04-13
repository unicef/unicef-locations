#!/usr/bin/env python
import ast
import codecs
import os
import re
import sys
from codecs import open

from setuptools import find_packages, setup

ROOT = os.path.realpath(os.path.dirname(__file__))
init = os.path.join(ROOT, "src", "unicef_locations", "__init__.py")
_version_re = re.compile(r'__version__\s+=\s+(.*)')
_name_re = re.compile(r'NAME\s+=\s+(.*)')

sys.path.insert(0, os.path.join(ROOT, 'src'))

with open(init, 'rb') as f:
    content = f.read().decode('utf-8')
    VERSION = str(ast.literal_eval(_version_re.search(content).group(1)))
    NAME = str(ast.literal_eval(_name_re.search(content).group(1)))


setup(
    name=NAME,
    version=VERSION,
    url='https://github.com/unicef/unicef-locations',
    author='UNICEF',
    author_email='rapidpro@unicef.org',
    license="Apache 2 License",
    description='Locations for eTools',
    long_description=codecs.open('README.rst').read(),
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    include_package_data=True,
    install_requires=(
        'django-autocomplete-light',
        'django-mptt',
        'django-model-utils',
        'django-leaflet',
        'djangorestframework',
        'carto',
        'celery',
        'unicef-djangolib',
    ),
    extras_require={
        'test': (
            'coverage',
            'django-fsm',
            'drf-api-checker',
            'django-webtest',
            'factory-boy',
            'faker',
            'flake8',
            'isort',
            'pytest',
            'pytest-cov',
            'pytest-django',
            'pytest-echo',
            'pytest-pythonpath',
            'psycopg2-binary',
            'webtest',
          ),
    },
    platforms=['any'],
    classifiers=[
        'Environment :: Web Environment',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers'],
    scripts=[],
)
