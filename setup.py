#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import codecs
import os
import re
import sys

from setuptools import find_packages, setup
from setuptools.command.install import install
from setuptools.command.test import test as TestCommand

HERE = os.path.abspath(os.path.dirname(__file__))
init = os.path.join(HERE, "src", "unicef_locations", "__init__.py")

_version_re = re.compile(r'__version__\s+=\s+(.*)')
_name_re = re.compile(r'NAME\s+=\s+(.*)')

with open(init, 'rb') as f:
    content = f.read().decode('utf-8')
    VERSION = str(ast.literal_eval(_version_re.search(content).group(1)))
    NAME = str(ast.literal_eval(_name_re.search(content).group(1)))


def read(*files):
    content = ''
    for f in files:
        content += codecs.open(os.path.join(HERE, f), 'r').read()
    return content


class VerifyTagVersion(install):
    """Verify that the git tag matches version"""

    def run(self):
        tag = os.getenv("CIRCLE_TAG")
        if tag != VERSION:
            info = "Git tag: {} does not match the version of this app: {}".format(
                tag,
                VERSION
            )
            sys.exit(info)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


setup(
    name=NAME,
    version=VERSION,
    url='https://github.com/unicef/unicef-locations',
    author='UNICEF',
    author_email='rapidpro@unicef.org',
    description='',
    long_description=read('README.rst'),
    platforms=['any'],
    license='Apache 2 License',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    cmdclass={"verify": VerifyTagVersion,
              'test': PyTest,
              }
)
