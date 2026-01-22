# DO-CertAutoBot

**CertAutoBot is an automated tool for managing SSL/TLS certificates using Certbot and DNS provider APIs (DigitalOcean by default, extensible via plugins)**. This tool facilitates the creation, renewal, and cleanup of certificates for subdomains, ensuring that the process is automated and efficient.

## Features

- **Automated Certificate Management**: Automatically create, renew, and clean up SSL/TLS certificates using Certbot and DigitalOcean's DNS API.
- **DNS-01 Challenge**: Uses the DNS-01 challenge method to prove domain ownership.
- **Support for Subdomains**: Easily handle certificates for subdomains.
- **Renewal Check**: Verifies if a certificate is due for renewal before attempting to create or renew a certificate.
- **Certificate Expiry Notification**: Check how many days are left before a certificate expires, including subdomains.
- **Force Renewal Option**: Added an option to force renewal of certificates if needed, even if the certificate is not due for renewal.

## Prerequisites

- Python 3.x
- Certbot
- DigitalOcean API Token
- jq (for JSON parsing in bash scripts)

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/tunelko/certautobot.git
    cd certautobot
    ```

2. **Set up the environment**:
    - Ensure that Certbot and the necessary dependencies are installed on your system.
    - Set the DigitalOcean API token as an environment variable:
      ```bash
      export DIGITALOCEAN_API_TOKEN="your_digital_ocean_api_token"
      ```

3. **Make the hooks executable**:
    ```bash
    chmod +x auth-hook.py
    chmod +x cleanup-hook.py
    ```

## Usage

### Interactive Mode

```bash
python3 certbot_auto.py
```

### CLI Mode (for cron/automation)

```
usage: certbot_auto.py [-h] [--action {renew,revoke,expiry}] [--domain DOMAIN]
                       [--subdomain SUBDOMAIN]

Automated SSL/TLS certificate management with Certbot and DigitalOcean DNS

options:
  -h, --help            show this help message and exit
  --action {renew,revoke,expiry}
                        Action to perform: renew, revoke, or expiry check
  --domain DOMAIN       Root domain (e.g., example.com)
  --subdomain SUBDOMAIN
                        Subdomain for certificate (e.g., www, mail). Empty for root domain
```

**Examples:**

```bash
# Renew certificate for subdomain
python3 certbot_auto.py --action renew --domain example.com --subdomain www

# Renew certificate for root domain
python3 certbot_auto.py --action renew --domain example.com

# Revoke certificate
python3 certbot_auto.py --action revoke --domain example.com --subdomain www

# Check certificate expiry
python3 certbot_auto.py --action expiry --domain example.com
```

**Cron example (renew monthly):**

```bash
0 0 1 * * DIGITALOCEAN_API_TOKEN="your_token" /usr/bin/python3 /path/to/certbot_auto.py --action renew --domain example.com --subdomain www
```

### Interactive Mode Steps

1. **Select a Domain**:
   - The script will fetch the domains from your DigitalOcean account. Choose the appropriate domain.

2. **Choose an Action**:
   - You can either create a new DNS record or overwrite an existing one.
   - Alternatively, you can revoke an existing certificate or check how many days are left before a certificate expires.

3. **Check Renewal Eligibility**:
   - Before proceeding, the script checks if the certificate for the selected domain can be renewed. If it cannot be renewed, the script will exit.

4. **Certificate Issuance**:
   - If eligible, Certbot will manage the DNS challenge and issue the certificate.

5. **Force Renewal Option**:
   - If required, you can force a certificate renewal even if the existing certificate is not yet due for renewal.

## Scripts

- **`certbot_auto.py`**: Main script that manages the entire certificate creation/renewal process.
- **`auth-hook.py`**: Hook that creates DNS TXT records for DNS-01 challenge (works with all providers).
- **`cleanup-hook.py`**: Hook that cleans up DNS TXT records after validation (works with all providers).

## Provider Plugin System

The tool supports multiple DNS providers through a plugin system.

**Available providers:** `digitalocean` (default)

### How to Implement Your Own Provider

#### Step 1: Create the provider file

Copy the template to a new file:

```bash
cp providers/template.py providers/cloudflare.py
```

#### Step 2: Implement the required methods

Edit your new provider file and implement these methods:

```python
class CloudflareProvider(DNSProvider):
    name = "cloudflare"
    env_token_name = "CLOUDFLARE_API_TOKEN"
    api_base = "https://api.cloudflare.com/client/v4"

    def fetch_domains(self):
        """Return list of domain names: ["example.com", "mydomain.org"]"""
        pass

    def fetch_domain_records(self, domain):
        """Return list of records: [{"id": 123, "name": "www", "type": "A", "data": "1.2.3.4"}]"""
        pass

    def create_txt_record(self, domain, record_name, value, ttl=60):
        """Create TXT record, return {"id": 123} or None on failure"""
        pass

    def delete_txt_record(self, domain, record_id):
        """Delete record by ID, return True/False"""
        pass
```

#### Step 3: Register the provider

Add to `providers/__init__.py`:

```python
from .cloudflare import CloudflareProvider

PROVIDERS = {
    "digitalocean": DigitalOceanProvider,
    "cloudflare": CloudflareProvider,  # Add your provider
}
```

#### Step 4: Use your provider

```bash
export CLOUDFLARE_API_TOKEN="your_token"
python3 certbot_auto.py --provider cloudflare --action renew --domain example.com
```

#### Note on Hooks

The Python hooks (`auth-hook.py`, `cleanup-hook.py`) automatically work with any registered provider. They use the `DNS_PROVIDER` environment variable set by the main script.

No custom hooks needed - just implement your provider and the hooks will use it automatically.

## Example output 

```bash_session
# python3 certbot_auto.py
Fetching domains from DigitalOcean...
Executing API request: GET https://api.digitalocean.com/v2/domains
1. example.com
Select a domain: subdomain
Selected domain: example.com
1. Create a new record
2. Overwrite an existing record
What would you like to do? 1
Enter the subdomain name (e.g., www, mail): subdomain
Running Certbot to manage DNS challenge and certificate issuance...
Executing command: certbot certonly --manual --preferred-challenges=dns --manual-public-ip-logging-ok -d subexample.example.com --manual-auth-hook /root/certautobot/auth-hook.sh --manual-cleanup-hook /root/certautobot/cleanup-hook.sh --non-interactive
Saving debug log to /var/log/letsencrypt/letsencrypt.log
Requesting a certificate for subexample.example.com
Hook '--manual-auth-hook' for subexample.example.com ran with output:
 DOMAIN: subexample.example.com
 CERTBOT_DOMAIN: subexample.example.com
 CERTBOT_VALIDATION: 5gV6zAnr444tqk3ebkBZvjngKYsU7-HjDOhphHEEpn0
 ROOT_DOMAIN: example.com
 SUBDOMAIN: subdomain
 RECORD_NAME: _acme-challenge.subdomain
 DNS TXT record created successfully.
Hook '--manual-cleanup-hook' for subexample.example.com ran with output:
 DOMAIN: subexample.example.com
 CERTBOT_DOMAIN: subexample.example.com
 ROOT_DOMAIN: example.com
 SUBDOMAIN: subdomain
 RECORD_NAME: _acme-challenge.subdomain
 DNS TXT record deleted successfully.

Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/subexample.example.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/subexample.example.com/privkey.pem
This certificate expires on 2024-11-26.
These files will be updated when the certificate renews.
Certbot has set up a scheduled task to automatically renew this certificate in the background.

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
If you like Certbot, please consider supporting our work by:
 * Donating to ISRG / Let's Encrypt:   https://letsencrypt.org/donate
 * Donating to EFF:                    https://eff.org/donate-le
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

```

## Troubleshooting 

- **DNS Propagation Issues**: If Certbot fails due to DNS propagation delays, you may need to increase the sleep duration in the script or manually verify the DNS TXT record before continuing.
- **Permission Errors**: Ensure that the hook scripts are executable and that Certbot has the necessary permissions to run them.
- **DigitalOcean API**: Ensure you give Fully Scoped Access to domain (4): create, read, update, delete.

## Contributing 

Contributions are welcome! Please feel free to submit a Pull Request or open an issue for any bugs or feature requests.

## License 

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments 

- [Certbot](https://certbot.eff.org/) for making certificate management straightforward.
- [DigitalOcean](https://www.digitalocean.com/) for providing an accessible API to manage DNS records.
- [Claude Code](https://claude.ai/) for help and assist on this piece of software, including this README ;)
