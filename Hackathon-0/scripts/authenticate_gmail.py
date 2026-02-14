#!/usr/bin/env python3
"""
One-time OAuth2 authentication script for Gmail API.

WSL2-safe: does NOT try to open a browser automatically.
Copy the printed URL into your Windows browser to authorise.

Usage:
    cd Hackathon-0/
    python scripts/authenticate_gmail.py

IMPORTANT — before running, ensure all three scopes are added in Google
Cloud Console → APIs & Services → OAuth consent screen → Edit App → Scopes:
    • https://www.googleapis.com/auth/gmail.readonly
    • https://www.googleapis.com/auth/gmail.send
    • https://www.googleapis.com/auth/gmail.modify
"""

import os
import pickle
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ── Config ────────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent.parent  # Hackathon-0/
load_dotenv(_BASE_DIR / ".env")

TOKEN_PATH = _BASE_DIR / "config" / "gmail_token.pickle"
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# ── Auth ──────────────────────────────────────────────────────────────────────


def _run_oauth_flow(client_id: str, client_secret: str):
    """
    Run the OAuth2 local-server flow.
    WSL2-safe: open_browser=False — copy the URL into your Windows browser.
    Catches the oauthlib scope-mismatch Warning so the token is still saved
    even if Google's consent screen hasn't had all scopes approved yet.
    """
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n" + "=" * 70)
    print("WSL2 detected — browser will NOT open automatically.")
    print("Copy the URL below into your Windows browser, authorize,")
    print("then return here. The script will capture the redirect.")
    print("=" * 70 + "\n")

    try:
        # open_browser=False: prints URL, does not call xdg-open / gio
        creds = flow.run_local_server(port=0, open_browser=False)
    except Warning as scope_warn:
        # oauthlib raises a Warning when granted scopes differ from requested.
        # The token is still exchanged and stored in flow.credentials.
        creds = flow.credentials
        print(f"\n⚠️  Scope warning: {scope_warn}")
        _warn_missing_scopes(creds)

    return creds


def _warn_missing_scopes(creds):
    """Print a clear message if send/modify scopes were not granted."""
    granted = set(creds.scopes or [])
    missing = []
    if "https://www.googleapis.com/auth/gmail.send" not in granted:
        missing.append("gmail.send  (needed to send emails via MCP server)")
    if "https://www.googleapis.com/auth/gmail.modify" not in granted:
        missing.append("gmail.modify  (needed to label emails in Gmail)")

    if missing:
        print("\n⚠️  The following scopes were NOT granted by Google:")
        for s in missing:
            print(f"   • {s}")
        print(
            "\nTo fix this:\n"
            "  1. Go to Google Cloud Console → APIs & Services → OAuth consent screen\n"
            "  2. Click 'Edit App' → Scopes → 'Add or Remove Scopes'\n"
            "  3. Add: gmail.readonly, gmail.send, gmail.modify\n"
            "  4. Save and re-run this script.\n"
            "\nThe token was saved with readonly scope only.\n"
            "Email sending and labelling will fail until all scopes are granted."
        )
    else:
        print("✅ All required scopes granted.")


def authenticate() -> None:
    creds = None

    # Re-use existing token if present
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as fh:
            creds = pickle.load(fh)
        print(f"Found existing token at {TOKEN_PATH}")

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        print("Token expired — refreshing…")
        creds.refresh(Request())

    elif not creds or not creds.valid:
        client_id = os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise SystemExit(
                "ERROR: GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env"
            )

        creds = _run_oauth_flow(client_id, client_secret)

    # Persist token
    with open(TOKEN_PATH, "wb") as fh:
        pickle.dump(creds, fh)

    print(f"\n✅ Token saved to {TOKEN_PATH}")

    # Scope check on existing/refreshed tokens too
    _warn_missing_scopes(creds)


if __name__ == "__main__":
    authenticate()
