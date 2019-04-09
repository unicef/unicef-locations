#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import codecs
import os
import re
import subprocess
import sys
from codecs import open
from distutils import log
from distutils.errors import DistutilsError

from setuptools import find_packages, setup
from setuptools.command.install import install
from setuptools.command.sdist import sdist as BaseSDistCommand
from setuptools.command.test import test as TestCommand

ROOT = os.path.realpath(os.path.dirname(__file__))
init = os.path.join(ROOT, "src", "unicef_locations", "__init__.py")
_version_re = re.compile(r'__version__\s+=\s+(.*)')
_name_re = re.compile(r'NAME\s+=\s+(.*)')

sys.path.insert(0, os.path.join(ROOT, 'src'))

with open(init, 'rb') as f:
    content = f.read().decode('utf-8')
    VERSION = str(ast.literal_eval(_version_re.search(content).group(1)))
    NAME = str(ast.literal_eval(_name_re.search(content).group(1)))


def read(*files):
    content = []
    for f in files:
        content.extend(codecs.open(os.path.join(ROOT, 'src', 'requirements', f), 'r').readlines())
    return "\n".join(filter(lambda l:not l.startswith('-'), content))


def check(cmd, filename):
    out = subprocess.run(cmd, stdout=subprocess.PIPE)
    f = os.path.join('src', 'requirements', filename)
    reqs = codecs.open(os.path.join(ROOT, f), 'r').readlines()
    existing = {re.split("(==|>=|<=>|<|)", name[:-1])[0] for name in reqs}
    declared = {
        re.split("(==|>=|<=>|<|)", name)[0]
        for name in out.stdout.decode('utf8').split("\n")
        if name and not name.startswith('-')
    }

    if existing != declared:
        msg = """Requirements file not updated.
Run 'make requiremets'
""".format(' '.join(cmd), f)
        raise DistutilsError(msg)


class SDistCommand(BaseSDistCommand):
    def run(self):
        checks = {'install.pip': ['pipenv', 'lock', '--requirements'],
                  'testing.pip': ['pipenv', 'lock', '-d', '--requirements']}

        for filename, cmd in checks.items():
            check(cmd, filename)
        super().run()


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
    license="Apache 2 License",
    description='',
    long_description=codecs.open('README.rst').read(),
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    include_package_data=True,
    install_requires=read('install.pip'),
    extras_require={
        'test': read('install.pip', 'testing.pip'),
    },
    platforms=['any'],
    classifiers=[
        'Environment :: Web Environment',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django',
        'Intended Audience :: Developers',
    ],
    scripts=[],
    cmdclass={
        "sdist": SDistCommand,
        "verify": VerifyTagVersion,
        "test": PyTest,
    }
)
