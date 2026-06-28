"""
Google OAuth service for handling authentication flow securely via Environment Variables.
"""
import json

from flask import session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import config

OAUTH_STATE_FILE = config.RUNTIME_DIR / "oauth_state.json"
OAUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

LOCAL_REDIRECT_URI = "http://localhost:8080/oauth2callback"


def get_client_config():
    """Build the OAuth client config from local environment variables."""
    return {
        "web": {
            "client_id": config.CLIENT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": config.CLIENT_SECRET
        }
    }


def get_local_redirect_uri():
    return LOCAL_REDIRECT_URI


def save_oauth_state(state, code_verifier):
    data = {"state": state, "code_verifier": code_verifier}
    with OAUTH_STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)


def load_oauth_state():
    if not OAUTH_STATE_FILE.exists():
        return None, None
    try:
        with OAUTH_STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("state"), data.get("code_verifier")
    except (OSError, json.JSONDecodeError):
        return None, None


def clear_oauth_state():
    if OAUTH_STATE_FILE.exists():
        OAUTH_STATE_FILE.unlink()


def get_authorization_url():
    """Generate the local Google OAuth login URL."""
    try:
        flow = Flow.from_client_config(get_client_config(), scopes=config.SCOPES)

        flow.redirect_uri = get_local_redirect_uri()

        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        return authorization_url, state, flow.code_verifier
    except Exception as e:
        raise RuntimeError(f"Google OAuth Error: {str(e)}")


def handle_oauth_callback(authorization_response, state, code_verifier):
    """Exchange the local OAuth callback for Google credentials."""
    try:
        if not state or not code_verifier:
            raise RuntimeError("Missing OAuth state or code verifier. Check session/cookie persistence.")

        flow = Flow.from_client_config(get_client_config(), scopes=config.SCOPES, state=state)
        flow.code_verifier = code_verifier

        flow.redirect_uri = get_local_redirect_uri()

        flow.fetch_token(authorization_response=authorization_response)

        return credentials_to_dict(flow.credentials)
    except Exception as e:
        raise RuntimeError(f"OAuth Callback Error: {str(e)}")

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_credentials_from_session():
    if 'credentials' not in session:
        raise RuntimeError("No credentials found in session. Please log in first.")
    return Credentials(**session['credentials'])
