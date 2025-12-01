"""OAuth2 authentication for YouTube Data API."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube upload scope
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Default paths (relative to project root)
DEFAULT_CLIENT_SECRETS = "credentials/client_secrets.json"
DEFAULT_TOKEN_FILE = "credentials/token.json"


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_authenticated_service(
    client_secrets_path: str | None = None,
    token_path: str | None = None,
):
    """
    Get an authenticated YouTube service.

    Handles:
    1. Loading existing token from token.json
    2. Refreshing expired tokens automatically
    3. Running OAuth flow for first-time setup
    4. Saving new tokens for future use

    Args:
        client_secrets_path: Path to client_secrets.json (optional)
        token_path: Path to token.json for storing credentials (optional)

    Returns:
        Authenticated YouTube service resource
    """
    project_root = get_project_root()

    # Resolve paths
    if client_secrets_path:
        secrets_file = Path(client_secrets_path)
    else:
        secrets_file = project_root / DEFAULT_CLIENT_SECRETS

    if token_path:
        token_file = Path(token_path)
    else:
        token_file = project_root / DEFAULT_TOKEN_FILE

    credentials = _load_or_refresh_credentials(secrets_file, token_file)

    return build("youtube", "v3", credentials=credentials)


def _load_or_refresh_credentials(
    secrets_file: Path,
    token_file: Path,
) -> Credentials:
    """Load existing credentials or run OAuth flow."""
    credentials = None

    # Try to load existing token
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    # Check if credentials are valid or need refresh
    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        print("Refreshing expired credentials...")
        credentials.refresh(Request())
        _save_credentials(credentials, token_file)
        return credentials

    # Need to run OAuth flow
    if not secrets_file.exists():
        raise FileNotFoundError(
            f"Client secrets file not found: {secrets_file}\n"
            "Please download client_secrets.json from Google Cloud Console:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a project and enable YouTube Data API v3\n"
            "3. Create OAuth 2.0 credentials (Desktop Application)\n"
            "4. Download and save as credentials/client_secrets.json"
        )

    print("Starting OAuth flow - a browser window will open for authorization...")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_file), SCOPES)
    credentials = flow.run_local_server(port=0)

    _save_credentials(credentials, token_file)
    print(f"Credentials saved to {token_file}")

    return credentials


def _save_credentials(credentials: Credentials, token_file: Path) -> None:
    """Save credentials to token file."""
    token_file.parent.mkdir(parents=True, exist_ok=True)
    with open(token_file, "w") as f:
        f.write(credentials.to_json())


def authenticate_only(
    client_secrets_path: str | None = None,
    token_path: str | None = None,
) -> bool:
    """
    Run authentication flow only (for first-time setup).

    Returns True if authentication successful.
    """
    try:
        service = get_authenticated_service(client_secrets_path, token_path)
        # Test the service with a simple API call
        service.channels().list(part="snippet", mine=True).execute()
        print("Authentication successful!")
        return True
    except Exception as e:
        print(f"Authentication failed: {e}")
        return False
