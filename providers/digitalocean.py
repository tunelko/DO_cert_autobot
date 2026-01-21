"""DigitalOcean DNS Provider plugin."""

import requests
from .base import DNSProvider


class DigitalOceanProvider(DNSProvider):
    """DigitalOcean DNS provider implementation."""

    name = "digitalocean"
    env_token_name = "DIGITALOCEAN_API_TOKEN"
    api_base = "https://api.digitalocean.com/v2"

    def __init__(self, api_token):
        super().__init__(api_token)
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method, endpoint, data=None):
        """Make an API request."""
        url = f"{self.api_base}{endpoint}"
        print(f"Executing API request: {method} {url}")

        response = requests.request(
            method,
            url,
            headers=self.headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()

        if response.status_code == 204:
            return None
        return response.json()

    def fetch_domains(self):
        """Fetch list of domains from DigitalOcean."""
        data = self._request("GET", "/domains")
        return [d["name"] for d in data.get("domains", [])]

    def fetch_domain_records(self, domain):
        """Fetch DNS records for a domain."""
        data = self._request("GET", f"/domains/{domain}/records")
        records = []
        for rec in data.get("domain_records", []):
            records.append({
                "id": rec["id"],
                "name": rec["name"],
                "type": rec["type"],
                "data": rec.get("data", ""),
            })
        return records

    def create_txt_record(self, domain, record_name, value, ttl=60):
        """Create a TXT record."""
        data = {
            "type": "TXT",
            "name": record_name,
            "data": value,
            "ttl": ttl,
        }

        try:
            result = self._request("POST", f"/domains/{domain}/records", data)
            record = result.get("domain_record", {})
            print(f"DNS TXT record created successfully (ID: {record.get('id')}).")
            return record
        except requests.RequestException as e:
            print(f"Failed to create DNS TXT record: {e}")
            return None

    def delete_txt_record(self, domain, record_id):
        """Delete a TXT record by ID."""
        try:
            self._request("DELETE", f"/domains/{domain}/records/{record_id}")
            print(f"DNS TXT record {record_id} deleted successfully.")
            return True
        except requests.RequestException as e:
            print(f"Failed to delete DNS TXT record {record_id}: {e}")
            return False
