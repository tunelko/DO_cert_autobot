import os
import subprocess
import requests
import time
import dns.resolver

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

def finalize_certbot(domain, script_dir):
    """Run certbot to finalize the certificate issuance."""
    certbot_cmd = [
        "certbot", "certonly", "--manual", "--preferred-challenges=dns",
        "--manual-public-ip-logging-ok", "-d", domain,
        "--manual-auth-hook", os.path.join(script_dir, "auth-hook.sh"),
        "--manual-cleanup-hook", os.path.join(script_dir, "cleanup-hook.sh"),
        "--non-interactive"
    ]
    print(f"Executing command: {' '.join(certbot_cmd)}")
    result = subprocess.run(certbot_cmd, check=True)
    return result.returncode == 0

def main():
    try:
        # Step 1: Get the API token from an environment variable
        api_token = get_env_var("DIGITALOCEAN_API_TOKEN")

        # Step 2: Get the current script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Step 3: Fetch and display the list of domains
        print("Fetching domains from DigitalOcean...")
        domains = fetch_domains(api_token)
        domain_names = [domain["name"] for domain in domains]
        selected_domain = get_user_selection(domain_names, "Select a domain:")
        print(f"Selected domain: {selected_domain}")

        # Step 4: Ask user if they want to create a new record or overwrite an existing one
        action = get_user_selection(["Create a new record", "Overwrite an existing record"], "What would you like to do?")

        if action == "Overwrite an existing record":
            # Step 5: Fetch and display the DNS records for the selected domain
            print(f"Fetching DNS records for {selected_domain}...")
            domain_records = fetch_domain_records(api_token, selected_domain)
            record_names = [f"{rec['name']} ({rec['type']})" for rec in domain_records]
            selected_record = get_user_selection(record_names, "Select a record to overwrite:")
            record_data = domain_records[record_names.index(selected_record)]
            record_id = record_data["id"]
            record_name = record_data["name"]

            # Handle the case where the record is a subdomain or root domain
            if record_name.startswith("_acme-challenge."):
                subdomain = record_name[len("_acme-challenge."):]
            else:
                subdomain = ""

        else:  # Creating a new record
            subdomain = input("Enter the subdomain name (e.g., www, mail): ")
            record_name = f"_acme-challenge.{subdomain}" if subdomain else "_acme-challenge"
            record_id = None

        # Step 6: Run Certbot with the hooks to manage the DNS challenge
        print("Running Certbot to manage DNS challenge and certificate issuance...")
        full_domain = f"{subdomain}.{selected_domain}" if subdomain else selected_domain

        if not finalize_certbot(full_domain, script_dir):
            print("Certbot validation failed.")
            return

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
