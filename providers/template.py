"""
Template DNS Provider plugin.

To create a new provider:
1. Copy this file to providers/yourprovider.py
2. Rename the class to YourProviderProvider
3. Update 'name' and 'env_token_name'
4. Implement all methods
5. Add to providers/__init__.py:
   from .yourprovider import YourProviderProvider
   PROVIDERS["yourprovider"] = YourProviderProvider
"""

import requests
from .base import DNSProvider


class TemplateProvider(DNSProvider):
    """Template DNS provider - copy and customize."""

    # Provider identifier (lowercase)
    name = "template"

    # Environment variable name for API token
    env_token_name = "TEMPLATE_API_TOKEN"

    # API base URL
    api_base = "https://api.yourprovider.com/v1"

    def __init__(self, api_token):
        super().__init__(api_token)
        # Set up headers or authentication
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def fetch_domains(self):
        """
        Fetch list of domains from the provider.

        Returns:
            list: List of domain names (strings)
        """
        # Example implementation:
        # response = requests.get(
        #     f"{self.api_base}/domains",
        #     headers=self.headers,
        #     timeout=30
        # )
        # response.raise_for_status()
        # return [d["name"] for d in response.json()["domains"]]

        raise NotImplementedError("Implement fetch_domains()")

    def fetch_domain_records(self, domain):
        """
        Fetch DNS records for a domain.

        Returns:
            list: List of dicts with keys: id, name, type, data
        """
        # Example implementation:
        # response = requests.get(
        #     f"{self.api_base}/domains/{domain}/records",
        #     headers=self.headers,
        #     timeout=30
        # )
        # response.raise_for_status()
        # records = []
        # for rec in response.json()["records"]:
        #     records.append({
        #         "id": rec["id"],
        #         "name": rec["name"],
        #         "type": rec["type"],
        #         "data": rec["content"],
        #     })
        # return records

        raise NotImplementedError("Implement fetch_domain_records()")

    def create_txt_record(self, domain, record_name, value, ttl=60):
        """
        Create a TXT record for DNS challenge.

        Returns:
            dict: Created record with 'id' key, or None on failure
        """
        # Example implementation:
        # data = {
        #     "type": "TXT",
        #     "name": record_name,
        #     "content": value,
        #     "ttl": ttl,
        # }
        # response = requests.post(
        #     f"{self.api_base}/domains/{domain}/records",
        #     headers=self.headers,
        #     json=data,
        #     timeout=30
        # )
        # response.raise_for_status()
        # return response.json()["record"]

        raise NotImplementedError("Implement create_txt_record()")

    def delete_txt_record(self, domain, record_id):
        """
        Delete a TXT record by ID.

        Returns:
            bool: True if deleted successfully
        """
        # Example implementation:
        # response = requests.delete(
        #     f"{self.api_base}/domains/{domain}/records/{record_id}",
        #     headers=self.headers,
        #     timeout=30
        # )
        # return response.status_code in (200, 204)

        raise NotImplementedError("Implement delete_txt_record()")
