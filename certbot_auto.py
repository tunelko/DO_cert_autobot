import os
import subprocess
import sys
import shutil
import requests
import dns.resolver
import OpenSSL
from datetime import datetime
import glob


def check_prerequisites():
    """Check that all prerequisites are met before running."""
    if sys.version_info < (3, 0):
        print("Error: Python 3.x is required")
        sys.exit(1)

    if not shutil.which("certbot"):
        answer = input("certbot is not installed. Install it? [y/N]: ")
        if answer.lower() == 'y':
            subprocess.run(["sudo", "apt", "install", "-y", "certbot"], check=True)
        else:
            sys.exit(1)

    if not shutil.which("jq"):
        answer = input("jq is not installed. Install it? [y/N]: ")
        if answer.lower() == 'y':
            subprocess.run(["sudo", "apt", "install", "-y", "jq"], check=True)
        else:
            sys.exit(1)

    if not os.getenv("DIGITALOCEAN_API_TOKEN"):
        token = input("DIGITALOCEAN_API_TOKEN not set. Enter token: ")
        if token:
            os.environ["DIGITALOCEAN_API_TOKEN"] = token
        else:
            sys.exit(1)


def get_env_var(var_name):
    """Get an environment variable or raise an error if it doesn't exist."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Environment variable {var_name} is not set.")
    return value


def fetch_domains(api_token):
    """Fetch the list of domains from DigitalOcean."""
    url = "https://api.digitalocean.com/v2/domains"
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    print(f"Executing API request: GET {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["domains"]


def fetch_domain_records(api_token, domain_name):
    """Fetch the DNS records of a specific domain from DigitalOcean."""
    url = f"https://api.digitalocean.com/v2/domains/{domain_name}/records"
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    print(f"Executing API request: GET {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["domain_records"]


def get_user_selection(options, prompt="Select an option:", allow_skip=False):
    """Display a menu and get the user's selection."""
    for idx, option in enumerate(options, start=1):
        print(f"{idx}. {option}")
    choice = input(f"{prompt} ")
    if allow_skip and choice == '':
        return None
    try:
        choice = int(choice) - 1
        if choice < 0 or choice >= len(options):
            print("Invalid selection, please try again.")
            return get_user_selection(options, prompt, allow_skip)
    except ValueError:
        print("Invalid selection, please try again.")
        return get_user_selection(options, prompt, allow_skip)
    return options[choice]


def check_dns_propagation(domain):
    """Check if the DNS TXT record has propagated."""
    try:
        txt_records = dns.resolver.resolve(f"_acme-challenge.{domain}", 'TXT')
        if txt_records:
            print("DNS propagation check successful.")
            return True
    except Exception as e:
        print(f"DNS propagation check failed: {e}")
    return False


def finalize_certbot(domain, script_dir, force_renewal=False):
    """Run certbot to finalize the certificate issuance."""
    certbot_cmd = [
        "certbot", "certonly", "--manual", "--preferred-challenges=dns",
        "--manual-public-ip-logging-ok", "-d", domain,
        "--manual-auth-hook", os.path.join(script_dir, "auth-hook.sh"),
        "--manual-cleanup-hook", os.path.join(script_dir, "cleanup-hook.sh"),
        "--non-interactive"
    ]
    if force_renewal:
        certbot_cmd.append("--force-renewal")

    print(f"Executing command: {' '.join(certbot_cmd)}")
    result = subprocess.run(certbot_cmd, check=True)
    return result.returncode == 0


def revoke_certbot_certificate(domain):
    """Revoke a Certbot certificate."""
    certbot_revoke_cmd = [
        "certbot", "revoke", "--cert-name", domain,
        "--non-interactive", "--agree-tos"
    ]
    print(f"Executing command: {' '.join(certbot_revoke_cmd)}")
    try:
        result = subprocess.run(certbot_revoke_cmd, check=True)
        if result.returncode == 0:
            print(f"Certificate for domain {domain} successfully revoked.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to revoke certificate for domain {domain}: {e}")


def get_certificate_expiry_days(domain):
    """Get the number of days left before the certificate expires for the domain and its subdomains."""
    # Search for certificate directories that match the domain pattern
    cert_paths = glob.glob(f"/etc/letsencrypt/live/{domain}*")
    if not cert_paths:
        print(f"Certificate for domain {domain} not found.")
        return

    for cert_path in cert_paths:
        try:
            with open(os.path.join(cert_path, "cert.pem"), "rb") as cert_file:
                cert_data = cert_file.read()
                cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_data)
                expiry_date = datetime.strptime(cert.get_notAfter().decode("ascii"), "%Y%m%d%H%M%SZ")
                days_left = (expiry_date - datetime.now()).days
                domain_name = os.path.basename(cert_path)
                print(f"Certificate for domain {domain_name} expires in {days_left} days.")
        except FileNotFoundError:
            print(f"Certificate for domain {cert_path} not found.")
        except Exception as e:
            print(f"An error occurred while checking certificate expiry for {cert_path}: {e}")


def main():
    check_prerequisites()

    try:
        # Step 1: Get the API token from an environment variable
        api_token = get_env_var("DIGITALOCEAN_API_TOKEN")

        # Step 2: Get the current script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Step 3: Fetch and display the list of domains
        print("Fetching domains from DigitalOcean...")
        domains = fetch_domains(api_token)
        domain_names = [domain["name"] for domain in domains]

        # Step 4: Ask user what action they would like to perform
        action = get_user_selection(["Issue a new certificate", "Revoke an existing certificate", "Check certificate expiry"], "What would you like to do?")

        if action == "Issue a new certificate":
            selected_domain = get_user_selection(domain_names, "Select a domain:")
            print(f"Selected domain: {selected_domain}")

            # Step 5: Ask user if they want to create a new record or overwrite an existing one
            action = get_user_selection(["Create a new record", "Overwrite an existing record"], "What would you like to do?")

            if action == "Overwrite an existing record":
                # Step 6: Fetch and display the DNS records for the selected domain
                print(f"Fetching DNS records for {selected_domain}...")
                domain_records = fetch_domain_records(api_token, selected_domain)
                record_names = [f"{rec['name']} ({rec['type']})" for rec in domain_records]
                selected_record = get_user_selection(record_names, "Select a record to overwrite:")
                record_data = domain_records[record_names.index(selected_record)]
                record_name = record_data["name"]

                # Handle the case where the record is a subdomain or root domain
                if record_name.startswith("_acme-challenge."):
                    subdomain = record_name[len("_acme-challenge."):]
                else:
                    subdomain = ""

            else:  # Creating a new record
                subdomain = input("Enter the subdomain name (e.g., www, mail): ")

            # Step 7: Run Certbot with the hooks to manage the DNS challenge
            print("Running Certbot to manage DNS challenge and certificate issuance...")
            full_domain = f"{subdomain}.{selected_domain}" if subdomain else selected_domain

            if not finalize_certbot(full_domain, script_dir, force_renewal=True):
                print("Certbot validation failed.")
                return

        elif action == "Revoke an existing certificate":
            selected_domain = get_user_selection(domain_names, "Select a domain to revoke its certificate:")
            revoke_certbot_certificate(selected_domain)

        elif action == "Check certificate expiry":
            selected_domain = get_user_selection(domain_names, "Select a domain to check certificate expiry:")
            get_certificate_expiry_days(selected_domain)

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
