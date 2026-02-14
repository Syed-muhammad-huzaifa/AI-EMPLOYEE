#!/usr/bin/env python3
"""
Standalone Social Media Poster
===============================
Runs Playwright operations in a separate process to avoid asyncio conflicts.

Usage:
  python post_social.py linkedin "Post text here"
  python post_social.py twitter "Tweet text here"
  python post_social.py facebook "Post text here"
"""

import sys
import os
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_BASE_DIR))

from dotenv import load_dotenv
load_dotenv(_BASE_DIR / ".env")


def post_linkedin(text: str) -> bool:
    from src.social.linkedin import LinkedInWatcher
    vault = os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
    return LinkedInWatcher(vault).post_to_linkedin(text)


def post_twitter(text: str) -> bool:
    from src.social.twitter import TwitterWatcher
    vault = os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
    return TwitterWatcher(vault).post_tweet(text)


def post_facebook(text: str) -> bool:
    from src.social.facebook import FacebookWatcher
    vault = os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
    return FacebookWatcher(vault).post_to_facebook(text)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: post_social.py <platform> <text>")
        print("Platforms: linkedin, twitter, facebook")
        sys.exit(1)

    platform = sys.argv[1].lower()
    text = sys.argv[2]

    try:
        if platform == "linkedin":
            success = post_linkedin(text)
        elif platform == "twitter":
            success = post_twitter(text)
        elif platform == "facebook":
            success = post_facebook(text)
        else:
            print(f"Unknown platform: {platform}")
            sys.exit(1)

        sys.exit(0 if success else 1)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
