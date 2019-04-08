#!/bin/bash

set -euo pipefail

if [[ -z $DRS_HOME ]]; then
    echo 'Please run "source environment" in the data-store repo root directory before running this command'
    exit 1
fi

#EXPORT_ENV_VARS_TO_APPENGINE=${EXPORT_ENV_VARS_TO_APPENGINE_ARRAY[*]}
for var in ${EXPORT_ENV_VARS_TO_APPENGINE}; do
    echo env.${var}
done

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
