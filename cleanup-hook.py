#!/usr/bin/env python3
"""
Generic cleanup hook for Certbot DNS-01 challenge.
Uses the provider plugin system.

Environment variables (set by Certbot):
  - CERTBOT_DOMAIN: The domain that was validated

Environment variables (set by user):
  - DNS_PROVIDER: Provider name (default: digitalocean)
  - {PROVIDER}_API_TOKEN: API token for the provider
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers import get_provider


def main():
    domain = os.environ.get("CERTBOT_DOMAIN", "")
    provider_name = os.environ.get("DNS_PROVIDER", "digitalocean")

    if not domain:
        print("Error: CERTBOT_DOMAIN must be set")
        sys.exit(1)

    print(f"DOMAIN: {domain}")
    print(f"PROVIDER: {provider_name}")

    # Determine root domain and subdomain
    parts = domain.split(".")
    if len(parts) > 2:
        root_domain = ".".join(parts[-2:])
        subdomain = ".".join(parts[:-2])
        record_name = f"_acme-challenge.{subdomain}"
    else:
        root_domain = domain
        subdomain = ""
        record_name = "_acme-challenge"

    print(f"ROOT_DOMAIN: {root_domain}")
    print(f"SUBDOMAIN: {subdomain}")
    print(f"RECORD_NAME: {record_name}")

    try:
        provider_class = get_provider(provider_name)
        api_token = os.environ.get(provider_class.env_token_name)

        if not api_token:
            print(f"Error: {provider_class.env_token_name} not set")
            sys.exit(1)

        provider = provider_class(api_token)
        deleted = provider.cleanup_txt_records(root_domain, record_name)

        if deleted > 0:
            print(f"Total records deleted: {deleted}")
        else:
            print("No matching DNS TXT records found to delete.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
