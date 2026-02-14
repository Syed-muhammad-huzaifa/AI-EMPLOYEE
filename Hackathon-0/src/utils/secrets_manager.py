"""Utility for loading secrets from environment variables."""

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Keys that must be present for the system to function.
_REQUIRED_KEYS = ("VAULT_PATH",)


def load_secrets() -> Dict[str, Optional[str]]:
    """Load secrets from the .env file and environment.

    Returns:
        Dictionary of secret values (value is None when not set).

    Raises:
        EnvironmentError: If any required secret is missing.
    """
    load_dotenv()

    secrets: Dict[str, Optional[str]] = {
        "vault_path":             os.getenv("VAULT_PATH"),
        "claude_api_key":         os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"),
        "gmail_credentials_path": os.getenv("GMAIL_CREDENTIALS_PATH"),
        "whatsapp_session_path":  os.getenv("WHATSAPP_SESSION_PATH"),
    }

    # Validate required keys.
    missing = [k for k in _REQUIRED_KEYS if not secrets.get(k.lower())]
    if missing:
        raise EnvironmentError(
            f"Required environment variable(s) not set: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in all required values."
        )

    # Warn about optional but commonly-needed keys.
    if not secrets["claude_api_key"]:
        logger.warning("ANTHROPIC_API_KEY is not set — orchestrator will not function.")
    if not secrets["gmail_credentials_path"]:
        logger.debug("GMAIL_CREDENTIALS_PATH not set — Gmail watcher may fail.")

    return secrets
