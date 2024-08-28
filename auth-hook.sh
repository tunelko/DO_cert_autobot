#!/bin/bash

# This script will be executed by Certbot with the following environment variables available:
# - CERTBOT_DOMAIN: The domain that is being validated.
# - CERTBOT_VALIDATION: The value of the TXT record that needs to be created.
# - CERTBOT_TOKEN: A challenge token (rarely needed in custom hooks).

DOMAIN=$CERTBOT_DOMAIN
TXT_VALUE=$CERTBOT_VALIDATION
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
echo "CERTBOT_VALIDATION: $CERTBOT_VALIDATION"
echo "ROOT_DOMAIN: $ROOT_DOMAIN"
echo "SUBDOMAIN: $SUBDOMAIN"
echo "RECORD_NAME: $RECORD_NAME"

# Create the DNS record using the DigitalOcean API
RESPONSE=$(curl -s -X POST "https://api.digitalocean.com/v2/domains/$ROOT_DOMAIN/records" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"type":"TXT","name":"'"$RECORD_NAME"'","data":"'"$TXT_VALUE"'","ttl":60}')

# Check if it was created successfully
if echo "$RESPONSE" | grep -q '"id":'; then
    echo "DNS TXT record created successfully."
else
    echo "Failed to create DNS TXT record." >&2
    echo "$RESPONSE" >&2
    exit 1
fi
