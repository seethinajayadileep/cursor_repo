#!/usr/bin/env bash
# Run in Azure Cloud Shell (or any PC already az-logged). Prints JSON for the panel Setup page.
set -euo pipefail
SUB="${AZURE_SUBSCRIPTION_ID:-8ff63f54-fc03-42ad-b01b-b06db0b941aa}"
RG="${RESOURCE_GROUP:-mailboxRg}"
az account set --subscription "$SUB"
az ad sp create-for-rbac --name mail-brand-api --role Contributor \
  --scopes "/subscriptions/${SUB}/resourceGroups/${RG}" \
  --only-show-errors
echo
echo "Copy the JSON above (appId, password, tenant) into Setup → Azure JSON box, then Save."
