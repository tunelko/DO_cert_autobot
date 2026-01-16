#!/bin/bash

# This script will be executed by Certbot with the following environment variables available:
# - CERTBOT_DOMAIN: The domain that is being validated.
# - CERTBOT_VALIDATION: The value of the TXT record that needs to be created.
# - CERTBOT_TOKEN: A challenge token (rarely needed in custom hooks).

set -euo pipefail

DOMAIN="${CERTBOT_DOMAIN:-}"
TXT_VALUE="${CERTBOT_VALIDATION:-}"
TOKEN="${DIGITALOCEAN_API_TOKEN:-}"

if [ -z "$TOKEN" ]; then
    echo "Error: DIGITALOCEAN_API_TOKEN is not set" >&2
    exit 1
fi

if [ -z "$TXT_VALUE" ]; then
    echo "Error: CERTBOT_VALIDATION is not set" >&2
    exit 1
fi

# Determine the root domain and subdomain (if any)
ROOT_DOMAIN=$(echo "$DOMAIN" | awk -F. '{print $(NF-1)"."$NF}')
SUBDOMAIN="${DOMAIN%."$ROOT_DOMAIN"}"

# Correctly set up the name of the TXT record
if [ "$SUBDOMAIN" = "$ROOT_DOMAIN" ] || [ -z "$SUBDOMAIN" ]; then
    RECORD_NAME="_acme-challenge"
else
    RECORD_NAME="_acme-challenge.$SUBDOMAIN"
fi

echo "DOMAIN: $DOMAIN"
echo "CERTBOT_DOMAIN: $CERTBOT_DOMAIN"
echo "CERTBOT_VALIDATION: $CERTBOT_VALIDATION"
echo "ROOT_DOMAIN: $ROOT_DOMAIN"
echo "SUBDOMAIN: $SUBDOMAIN"
echo "RECORD_NAME: $RECORD_NAME"

# Create the DNS record using the DigitalOcean API
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.digitalocean.com/v2/domains/$ROOT_DOMAIN/records" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"type":"TXT","name":"'"$RECORD_NAME"'","data":"'"$TXT_VALUE"'","ttl":60}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Check if it was created successfully
if [ "$HTTP_CODE" = "201" ] && echo "$BODY" | grep -q '"id":'; then
    RECORD_ID=$(echo "$BODY" | jq -r '.domain_record.id')
    echo "DNS TXT record created successfully (ID: $RECORD_ID)."

    # Wait for DNS propagation
    echo "Waiting 10 seconds for DNS propagation..."
    sleep 10
else
    echo "Failed to create DNS TXT record (HTTP $HTTP_CODE)." >&2
    echo "$BODY" >&2
    exit 1
fi
