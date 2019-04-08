#!/bin/bash

set -euo pipefail

if [[ -z $DRS_HOME ]]; then
    echo 'Please run "source environment" in the data-store repo root directory before running this command'
    exit 1
fi

api_domain_name="${DRS_APPENGINE_SERVICE_VERSION}-dot-${DRS_APPENGINE_SERVICE_NAME}-dot-${GCP_PROJECT}.appspot.com"

cat ../drs-api.yml \
    | yq . \
    | jq --arg host "${api_domain_name}" '.host=$host' \
    | yq -y . | sponge drs-api.yml
