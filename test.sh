#!/usr/bin/env bash
export PATH=$PATH:/home/circleci/.local/bin
pip install -r src/requirements/install.pip --user
pip install -r src/requirements/testing.pip --user
pytest tests \
  -q \
  --create-db \
  --cov-report=html \
  --cov-report=term \
  --cov-config=tests/.coveragerc \
  --cov=unicef_locations
