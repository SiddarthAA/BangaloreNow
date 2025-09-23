import os
from google.cloud import secretmanager

# Initialize the client
client = secretmanager.SecretManagerServiceClient()

# Get the GCP Project ID from the environment, which is automatically set in Cloud Run
PROJECT_ID = os.environ.get('GCP_PROJECT')

def access_secret(secret_id, version_id="latest"):
    """Access the payload for the given secret version and return it as a string."""
    if not PROJECT_ID:
        raise EnvironmentError("GCP_PROJECT environment variable not set. Are you running in Cloud Run?")

    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def load_secrets_into_env():
    """Fetch all required secrets and load them into the environment."""
    print("Loading secrets into environment...")
    # Define the secrets your application needs
    secrets_to_load = {
        "DATABASE_URL": "DATABASE_URL", # The name of the secret in Secret Manager
        "base_gemini": "BASE_GEMINI_API_KEY",
        "base_geo": "BASE_GEO_API_KEY"
    }

    for env_var, secret_id in secrets_to_load.items():
        try:
            secret_value = access_secret(secret_id)
            os.environ[env_var] = secret_value
        except Exception as e:
            print(f"Warning: Could not load secret '{secret_id}'. Error: {e}")

    print("Secrets loaded.")
