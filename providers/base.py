"""Base DNS Provider interface."""

from abc import ABC, abstractmethod


class DNSProvider(ABC):
    """
    Abstract base class for DNS providers.

    To create a new provider plugin:
    1. Copy template.py to your_provider.py
    2. Implement all abstract methods
    3. Register in providers/__init__.py PROVIDERS dict
    """

    # Provider metadata
    name = "base"
    env_token_name = "DNS_API_TOKEN"

    def __init__(self, api_token):
        """Initialize the provider with API token."""
        self.api_token = api_token

    @abstractmethod
    def fetch_domains(self):
        """
        Fetch list of domains from the provider.

        Returns:
            list: List of domain names (strings)

        Example:
            ["example.com", "mydomain.org"]
        """
        pass

    @abstractmethod
    def fetch_domain_records(self, domain):
        """
        Fetch DNS records for a domain.

        Args:
            domain: The domain name

        Returns:
            list: List of record dicts with keys: id, name, type, data

        Example:
            [{"id": 123, "name": "www", "type": "A", "data": "1.2.3.4"}]
        """
        pass

    @abstractmethod
    def create_txt_record(self, domain, record_name, value, ttl=60):
        """
        Create a TXT record for DNS challenge.

        Args:
            domain: Root domain (e.g., "example.com")
            record_name: Record name (e.g., "_acme-challenge.www")
            value: TXT record value (validation token)
            ttl: Time to live in seconds

        Returns:
            dict: Created record with 'id' key, or None on failure
        """
        pass

    @abstractmethod
    def delete_txt_record(self, domain, record_id):
        """
        Delete a TXT record by ID.

        Args:
            domain: Root domain
            record_id: The record ID to delete

        Returns:
            bool: True if deleted successfully
        """
        pass

    def find_txt_records(self, domain, record_name):
        """
        Find TXT records matching a name.

        Args:
            domain: Root domain
            record_name: Record name to find

        Returns:
            list: List of matching record dicts
        """
        records = self.fetch_domain_records(domain)
        return [r for r in records if r['type'] == 'TXT' and r['name'] == record_name]

    def check_subdomain_exists(self, domain, subdomain):
        """
        Check if subdomain has an A record.

        Args:
            domain: Root domain
            subdomain: Subdomain to check

        Returns:
            bool: True if A record exists
        """
        if not subdomain:
            return True
        records = self.fetch_domain_records(domain)
        for rec in records:
            if rec['name'] == subdomain and rec['type'] == 'A':
                return True
        return False

    def cleanup_txt_records(self, domain, record_name):
        """
        Delete all TXT records matching a name.

        Args:
            domain: Root domain
            record_name: Record name to delete

        Returns:
            int: Number of records deleted
        """
        records = self.find_txt_records(domain, record_name)
        deleted = 0
        for rec in records:
            if self.delete_txt_record(domain, rec['id']):
                deleted += 1
        return deleted
