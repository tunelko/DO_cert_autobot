#!/bin/bash

# This script will be executed by Certbot with the following environment variables available:
# - CERTBOT_DOMAIN: The domain that was validated.
# - CERTBOT_VALIDATION: The value of the TXT record that was created.
# - CERTBOT_TOKEN: A challenge token (rarely needed in custom hooks).

DOMAIN=$CERTBOT_DOMAIN
TOKEN=$DIGITALOCEAN_API_TOKEN

# Determine the root domain and subdomain (if any)
ROOT_DOMAIN=$(echo $DOMAIN | awk -F. '{print $(NF-1)"."$NF}')
SUBDOMAIN=$(echo $DOMAIN | sed "s/.$ROOT_DOMAIN//")

# Correctly set up the name of the TXT record
if [ "$SUBDOMAIN" = "$ROOT_DOMAIN" ]; then
    RECORD_NAME="_acme-challenge"
else
    RECORD_NAME="_acme-challenge.$SUBDOMAIN"
fi

echo "DOMAIN: $DOMAIN"
echo "CERTBOT_DOMAIN: $CERTBOT_DOMAIN"
echo "ROOT_DOMAIN: $ROOT_DOMAIN"
echo "SUBDOMAIN: $SUBDOMAIN"
echo "RECORD_NAME: $RECORD_NAME"

# Get the ID of the DNS record that we want to delete
RECORD_ID=$(curl -s -X GET "https://api.digitalocean.com/v2/domains/$ROOT_DOMAIN/records" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" | \
    jq -r ".domain_records[] | select(.type == \"TXT\" and .name == \"$RECORD_NAME\") | .id")

# Verify if the record exists and delete it
if [ -n "$RECORD_ID" ]; then
    curl -s -X DELETE "https://api.digitalocean.com/v2/domains/$ROOT_DOMAIN/records/$RECORD_ID" \
         -H "Authorization: Bearer $TOKEN"
    echo "DNS TXT record deleted successfully."
else
    echo "No matching DNS TXT record found." >&2
    exit 1
fi
