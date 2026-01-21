import os
import subprocess
import sys
import shutil
import argparse
import re
import dns.resolver
import OpenSSL
from datetime import datetime
import glob

from providers import get_provider, list_providers


def parse_args():
    """Parse command line arguments."""
    available_providers = ", ".join(list_providers())
    parser = argparse.ArgumentParser(
        description="Automated SSL/TLS certificate management with Certbot and DNS providers",
        epilog="Examples:\n"
               "  %(prog)s --action renew --domain example.com --subdomain www\n"
               "  %(prog)s --action renew --domain example.com  # root domain\n"
               "  %(prog)s --action revoke --domain www.example.com\n"
               "  %(prog)s --action expiry --domain example.com\n"
               "  %(prog)s --provider cloudflare --action renew --domain example.com\n"
               f"\nAvailable providers: {available_providers}\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--provider", type=str, default="digitalocean",
                        help=f"DNS provider ({available_providers}). Default: digitalocean")
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


def validate_args(args, valid_domains, provider_name):
    """Validate CLI arguments."""
    if args.action and not args.domain:
        print("Error: --domain is required when --action is specified")
        sys.exit(1)

    if args.domain:
        validate_domain(args.domain)
        if args.domain not in valid_domains:
            print(f"Error: Domain '{args.domain}' not found in {provider_name} account")
            print(f"Available domains: {', '.join(valid_domains)}")
            sys.exit(1)

    if args.subdomain:
        validate_subdomain(args.subdomain)


def check_prerequisites(provider_class, interactive=True):
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

    token_env = provider_class.env_token_name
    if not os.getenv(token_env):
        if interactive:
            token = input(f"{token_env} not set. Enter token: ")
            if token:
                os.environ[token_env] = token
            else:
                sys.exit(1)
        else:
            print(f"Error: {token_env} environment variable is not set")
            sys.exit(1)


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


def finalize_certbot(domain, script_dir, provider_name, force_renewal=False):
    """Run certbot to finalize the certificate issuance."""
    # Use Python hooks (generic, work with all providers)
    auth_hook = os.path.join(script_dir, "auth-hook.py")
    cleanup_hook = os.path.join(script_dir, "cleanup-hook.py")

    # Fallback to shell hooks if Python hooks don't exist
    if not os.path.exists(auth_hook):
        auth_hook = os.path.join(script_dir, "auth-hook.sh")
    if not os.path.exists(cleanup_hook):
        cleanup_hook = os.path.join(script_dir, "cleanup-hook.sh")

    # Set DNS_PROVIDER env var for hooks
    env = os.environ.copy()
    env["DNS_PROVIDER"] = provider_name

    certbot_cmd = [
        "certbot", "certonly", "--manual", "--preferred-challenges=dns",
        "--manual-public-ip-logging-ok", "-d", domain,
        "--manual-auth-hook", auth_hook,
        "--manual-cleanup-hook", cleanup_hook,
        "--non-interactive"
    ]
    if force_renewal:
        certbot_cmd.append("--force-renewal")

    print(f"Executing command: {' '.join(certbot_cmd)}")
    result = subprocess.run(certbot_cmd, check=True, env=env)
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
    """Get the number of days left before the certificate expires."""
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


def run_cli_mode(args, provider, script_dir, domain_names):
    """Run in non-interactive CLI mode."""
    validate_args(args, domain_names, provider.name)

    if args.action == "renew":
        full_domain = f"{args.subdomain}.{args.domain}" if args.subdomain else args.domain
        print(f"Renewing certificate for: {full_domain}")

        if args.subdomain and not provider.check_subdomain_exists(args.domain, args.subdomain):
            print(f"WARNING: Subdomain '{args.subdomain}' has no A record in {args.domain}")
            print("         Certificate will be created but subdomain won't resolve.")

        if not finalize_certbot(full_domain, script_dir, provider.name, force_renewal=True):
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


def run_interactive_mode(provider, script_dir, domain_names):
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
            domain_records = provider.fetch_domain_records(selected_domain)
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

        if subdomain and not provider.check_subdomain_exists(selected_domain, subdomain):
            print(f"WARNING: Subdomain '{subdomain}' has no A record in {selected_domain}")
            print("         Certificate will be created but subdomain won't resolve.")

        if not finalize_certbot(full_domain, script_dir, provider.name, force_renewal=True):
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

    try:
        provider_class = get_provider(args.provider)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    check_prerequisites(provider_class, interactive=interactive)

    try:
        api_token = os.getenv(provider_class.env_token_name)
        provider = provider_class(api_token)
        script_dir = os.path.dirname(os.path.abspath(__file__))

        print(f"Using provider: {provider.name}")
        print("Fetching domains...")
        domain_names = provider.fetch_domains()

        if interactive:
            run_interactive_mode(provider, script_dir, domain_names)
        else:
            run_cli_mode(args, provider, script_dir, domain_names)

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
