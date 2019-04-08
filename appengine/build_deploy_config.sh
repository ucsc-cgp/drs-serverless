#!/bin/bash

set -euo pipefail

if [[ -z $DRS_HOME ]]; then
    echo 'Please run "source environment" in the data-store repo root directory before running this command'
    exit 1
fi

cat ../drs-api.yml \
    | yq . \
    | jq --arg host "${API_DOMAIN_NAME}" '.host=$host' \
    | yq -y . | sponge drs-api.yml

cat app.yaml \
    | yq . \
    | jq --arg service ${DRS_APPENGINE_SERVICE_NAME} '.service=$service' \
    | yq -y . | sponge app.yaml

for var in ${EXPORT_ENV_VARS_TO_APPENGINE}; do
    cat app.yaml \
        | yq . \
        | jq .env_variables.$var=env.$var \
        | yq -y . | sponge app.yaml
done
