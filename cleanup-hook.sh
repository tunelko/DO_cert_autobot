#!/bin/bash

# This script will be executed by Certbot with the following environment variables available:
# - CERTBOT_DOMAIN: The domain that was validated.
# - CERTBOT_VALIDATION: The value of the TXT record that was created.
# - CERTBOT_TOKEN: A challenge token (rarely needed in custom hooks).

set -euo pipefail

DOMAIN="${CERTBOT_DOMAIN:-}"
TOKEN="${DIGITALOCEAN_API_TOKEN:-}"

if [ -z "$TOKEN" ]; then
    echo "Error: DIGITALOCEAN_API_TOKEN is not set" >&2
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
echo "ROOT_DOMAIN: $ROOT_DOMAIN"
echo "SUBDOMAIN: $SUBDOMAIN"
echo "RECORD_NAME: $RECORD_NAME"

# Get all matching TXT record IDs (handle multiple records)
RECORD_IDS=$(curl -s -X GET "https://api.digitalocean.com/v2/domains/$ROOT_DOMAIN/records" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" | \
    jq -r ".domain_records[] | select(.type == \"TXT\" and .name == \"$RECORD_NAME\") | .id")

# Delete all matching records
DELETED=0
for RECORD_ID in $RECORD_IDS; do
    if [ -n "$RECORD_ID" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
            "https://api.digitalocean.com/v2/domains/$ROOT_DOMAIN/records/$RECORD_ID" \
            -H "Authorization: Bearer $TOKEN")
        if [ "$HTTP_CODE" = "204" ]; then
            echo "DNS TXT record $RECORD_ID deleted successfully."
            DELETED=$((DELETED + 1))
        else
            echo "Warning: Failed to delete record $RECORD_ID (HTTP $HTTP_CODE)" >&2
        fi
    fi
done

if [ "$DELETED" -eq 0 ]; then
    echo "No matching DNS TXT records found to delete." >&2
    exit 0
fi

echo "Total records deleted: $DELETED"
