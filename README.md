# DO-CertAutoBot

**CertAutoBot is an automated tool for managing SSL/TLS certificates using Certbot and DigitalOcean's DNS API**. This tool facilitates the creation, renewal, and cleanup of certificates for subdomains, ensuring that the process is automated and efficient.

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

3. **Make the scripts executable**:
    ```bash
    chmod +x auth-hook.sh
    chmod +x cleanup-hook.sh
    ```

## Usage

1. **Run the CertAutoBot script**:
    ```bash
    python3 certbot_auto.py
    ```

2. **Select a Domain**:
   - The script will fetch the domains from your DigitalOcean account. Choose the appropriate domain.

3. **Choose an Action**:
   - You can either create a new DNS record or overwrite an existing one.
   - Alternatively, you can revoke an existing certificate or check how many days are left before a certificate expires.

4. **Check Renewal Eligibility**:
   - Before proceeding, the script checks if the certificate for the selected domain can be renewed. If it cannot be renewed, the script will exit.

5. **Certificate Issuance**:
   - If eligible, Certbot will manage the DNS challenge and issue the certificate.

6. **Force Renewal Option**:
   - If required, you can force a certificate renewal even if the existing certificate is not yet due for renewal.

## 😋 Scripts 

- **`certbot_auto.py`**: Main script that manages the entire certificate creation/renewal process.
- **`auth-hook.sh`**: Hook script that creates the necessary DNS TXT record using the DigitalOcean API during the Certbot DNS-01 challenge.
- **`cleanup-hook.sh`**: Hook script that cleans up the DNS TXT record after the certificate issuance is complete.

## 🥇 Example output 

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

## 😡 Troubleshooting 

- **DNS Propagation Issues**: If Certbot fails due to DNS propagation delays, you may need to increase the sleep duration in the script or manually verify the DNS TXT record before continuing.
- **Permission Errors**: Ensure that the hook scripts are executable and that Certbot has the necessary permissions to run them.
- **DigitalOcean API**: Ensure you give Fully Scoped Access to domain (4): create, read, update, delete.

## 🗨️ Contributing 

Contributions are welcome! Please feel free to submit a Pull Request or open an issue for any bugs or feature requests.

## 🧑‍🎨 👩‍🎨 License 

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 👯 Acknowledgments 

- [Certbot](https://certbot.eff.org/) for making certificate management straightforward.
- [DigitalOcean](https://www.digitalocean.com/) for providing an accessible API to manage DNS records.
- [ChatGPT](https://chatgpt.com/) for help and assist on this piece of sfotware, including this README ;)
