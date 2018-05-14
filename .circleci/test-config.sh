#!/usr/bin/env bash
curl --user ${CIRCLE_TOKEN}: \
    --request POST \
    --form revision=ac93c0a3147145eed8db0614bad4f00ba7c2ba0e \
    --form config=@config.yml \
    --form notify=false \
        https://circleci.com/api/v1.1/project/github/unicef/etools-validator/tree/master
