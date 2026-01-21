import os
import subprocess
import sys
import shutil
import argparse
import re
import requests
import dns.resolver
import OpenSSL
from datetime import datetime
import glob


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Automated SSL/TLS certificate management with Certbot and DigitalOcean DNS",
        epilog="Examples:\n"
               "  %(prog)s --action renew --domain example.com --subdomain www\n"
               "  %(prog)s --action renew --domain example.com  # root domain\n"
               "  %(prog)s --action revoke --domain www.example.com\n"
               "  %(prog)s --action expiry --domain example.com\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--action", choices=["renew", "revoke", "expiry"],
                        help="Action to perform: renew, revoke, or expiry check")
    parser.add_argument("--domain", type=str,
                        help="Root domain (e.g., example.com)")
    parser.add_argument("--subdomain", type=str, default="",
                        help="Subdomain for certificate (e.g., www, mail). Empty for root domain")
    return parser.parse_args()


def validate_domain(domain):
    """Validate domain format."""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
    if not re.match(pattern, domain):
        print(f"Error: Invalid domain format: {domain}")
        sys.exit(1)
    return True


def validate_subdomain(subdomain):
    """Validate subdomain format."""
    if not subdomain:
        return True
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    if not re.match(pattern, subdomain):
        print(f"Error: Invalid subdomain format: {subdomain}")
        sys.exit(1)
    return True


def validate_args(args, valid_domains):
    """Validate CLI arguments."""
    if args.action and not args.domain:
        print("Error: --domain is required when --action is specified")
        sys.exit(1)

    if args.domain:
        validate_domain(args.domain)
        if args.domain not in valid_domains:
            print(f"Error: Domain '{args.domain}' not found in DigitalOcean account")
            print(f"Available domains: {', '.join(valid_domains)}")
            sys.exit(1)

    if args.subdomain:
        validate_subdomain(args.subdomain)


def check_prerequisites(interactive=True):
    """Check that all prerequisites are met before running."""
    if sys.version_info < (3, 0):
        print("Error: Python 3.x is required")
        sys.exit(1)

    if not shutil.which("certbot"):
        if interactive:
            answer = input("certbot is not installed. Install it? [y/N]: ")
            if answer.lower() == 'y':
                subprocess.run(["sudo", "apt", "install", "-y", "certbot"], check=True)
            else:
                sys.exit(1)
        else:
            print("Error: certbot is not installed")
            sys.exit(1)

    if not shutil.which("jq"):
        if interactive:
            answer = input("jq is not installed. Install it? [y/N]: ")
            if answer.lower() == 'y':
                subprocess.run(["sudo", "apt", "install", "-y", "jq"], check=True)
            else:
                sys.exit(1)
        else:
            print("Error: jq is not installed")
            sys.exit(1)

    if not os.getenv("DIGITALOCEAN_API_TOKEN"):
        if interactive:
            token = input("DIGITALOCEAN_API_TOKEN not set. Enter token: ")
            if token:
                os.environ["DIGITALOCEAN_API_TOKEN"] = token
            else:
                sys.exit(1)
        else:
            print("Error: DIGITALOCEAN_API_TOKEN environment variable is not set")
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
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()["domains"]


def fetch_domain_records(api_token, domain_name):
    """Fetch the DNS records of a specific domain from DigitalOcean."""
    url = f"https://api.digitalocean.com/v2/domains/{domain_name}/records"
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    print(f"Executing API request: GET {url}")
    response = requests.get(url, headers=headers, timeout=30)
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


def run_cli_mode(args, api_token, script_dir, domain_names):
    """Run in non-interactive CLI mode."""
    validate_args(args, domain_names)

    if args.action == "renew":
        full_domain = f"{args.subdomain}.{args.domain}" if args.subdomain else args.domain
        print(f"Renewing certificate for: {full_domain}")
        if not finalize_certbot(full_domain, script_dir, force_renewal=True):
            print("Certbot validation failed.")
            sys.exit(1)
        print("Certificate renewed successfully.")

    elif args.action == "revoke":
        full_domain = f"{args.subdomain}.{args.domain}" if args.subdomain else args.domain
        print(f"Revoking certificate for: {full_domain}")
        revoke_certbot_certificate(full_domain)

    elif args.action == "expiry":
        print(f"Checking certificate expiry for: {args.domain}")
        get_certificate_expiry_days(args.domain)


def run_interactive_mode(api_token, script_dir, domain_names):
    """Run in interactive mode."""
    action = get_user_selection(
        ["Issue a new certificate", "Revoke an existing certificate", "Check certificate expiry"],
        "What would you like to do?"
    )

    if action == "Issue a new certificate":
        selected_domain = get_user_selection(domain_names, "Select a domain:")
        print(f"Selected domain: {selected_domain}")

        record_action = get_user_selection(
            ["Create a new record", "Overwrite an existing record"],
            "What would you like to do?"
        )

        if record_action == "Overwrite an existing record":
            print(f"Fetching DNS records for {selected_domain}...")
            domain_records = fetch_domain_records(api_token, selected_domain)
            record_names = [f"{rec['name']} ({rec['type']})" for rec in domain_records]
            selected_record = get_user_selection(record_names, "Select a record to overwrite:")
            record_data = domain_records[record_names.index(selected_record)]
            record_name = record_data["name"]

            if record_name.startswith("_acme-challenge."):
                subdomain = record_name[len("_acme-challenge."):]
            else:
                subdomain = ""
        else:
            subdomain = input("Enter the subdomain name (e.g., www, mail): ")

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


def main():
    args = parse_args()
    interactive = not args.action

    check_prerequisites(interactive=interactive)

    try:
        api_token = get_env_var("DIGITALOCEAN_API_TOKEN")
        script_dir = os.path.dirname(os.path.abspath(__file__))

        print("Fetching domains from DigitalOcean...")
        domains = fetch_domains(api_token)
        domain_names = [domain["name"] for domain in domains]

        if interactive:
            run_interactive_mode(api_token, script_dir, domain_names)
        else:
            run_cli_mode(args, api_token, script_dir, domain_names)

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
