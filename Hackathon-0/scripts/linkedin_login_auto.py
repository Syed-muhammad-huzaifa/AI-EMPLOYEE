#!/usr/bin/env python3
"""
LinkedIn Auto-Login Helper
===========================
Opens a headed browser for LinkedIn login and automatically saves the session
after 2 minutes (no Enter key required).

Usage:
  DISPLAY=:0 python3 scripts/linkedin_login_auto.py
"""

import sys
import time
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_BASE_DIR))

from src.social.browser_manager import BrowserManager

print("=" * 60)
print("  LinkedIn Login - Auto-Save Mode")
print("=" * 60)
print()
print("A Chrome window will open in 3 seconds...")
print("Log in to LinkedIn and wait - session will auto-save in 2 minutes.")
print()

time.sleep(3)

with BrowserManager("linkedin", headless=False) as ctx:
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.linkedin.com")

    print("✅ Browser opened!")
    print("📋 Log in to LinkedIn now...")
    print()
    print("Waiting 2 minutes for you to log in...")

    for remaining in range(120, 0, -10):
        print(f"   {remaining} seconds remaining...")
        time.sleep(10)

    print()
    print("✅ Session saved!")
    print("   Browser will close in 3 seconds...")
    time.sleep(3)

print()
print("=" * 60)
print("  Done! LinkedIn session is now saved.")
print("=" * 60)
