BUILDDIR?=~build
DJANGO_SETTINGS_MODULE?="demo.settings"
DEMOPATH=tests/demoproject


help:
	@echo "Usage:"
	@echo "   develop                 setup development environment"
	@echo "   lint                    run pyflake/isort checks"
	@echo "   clean                   clean dev environment"
	@echo "   fullclean               totally remove any development/test artifacts"
	@echo "   test                    run test suite"


develop:
	@${MAKE} clean
	pip install .[test]


test:
	pytest tests/ src/


rundemo:
	PYTHONPATH=${PYTHONPATH}:${DEMOPATH} django-admin.py migrate --settings ${DJANGO_SETTINGS_MODULE}
	PYTHONPATH=${PYTHONPATH}:${DEMOPATH} django-admin.py runserver --settings ${DJANGO_SETTINGS_MODULE}


lint:
#	black -l 100 src
	flake8 src/ tests
	isort -rc src/ --check-only
	PYTHONPATH=${PYTHONPATH}:${DEMOPATH} django-admin.py check --settings ${DJANGO_SETTINGS_MODULE}


clean:
	rm -fr ${BUILDDIR} build dist src/*.egg-info .coverage coverage.xml .eggs .coverage.*
	find src -name __pycache__ -o -name "*.py?" -o -name "*.orig" -prune | xargs rm -rf


fullclean:
	rm -fr .tox .cache .pytest_cache .venv
	$(MAKE) clean


travis:
	docker run --privileged -it --rm --name travis-debug -u travis quay.io/travisci/travis-python /bin/bash -l
