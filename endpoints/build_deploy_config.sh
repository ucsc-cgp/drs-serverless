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
