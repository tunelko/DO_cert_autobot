"""DNS Provider plugins for CertAutoBot."""

from .base import DNSProvider
from .digitalocean import DigitalOceanProvider

PROVIDERS = {
    "digitalocean": DigitalOceanProvider,
}


def get_provider(name):
    """Get a provider class by name."""
    provider_class = PROVIDERS.get(name.lower())
    if not provider_class:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider: {name}. Available: {available}")
    return provider_class


def list_providers():
    """List all available providers."""
    return list(PROVIDERS.keys())
