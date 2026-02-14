"""
WhatsApp Watcher (Playwright-based)
====================================
Monitors WhatsApp Web for unread messages matching business keywords.
Uses Playwright persistent context for session reuse (scan QR once, then headless).

First run:
  python -m src.watchers.whatsapp_watcher --login
  → opens headed browser, scan QR code with your phone, session is saved

Subsequent runs (daemon mode):
  Headless, session loaded automatically. Checks every 30 seconds.

Action files written to: <vault>/Needs_Action/WA_<contact>_<timestamp>.md
Reply files approved at:  <vault>/Approved/WA_<task_id>.md
"""

import os
import re
import sys
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent.parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

load_dotenv(_BASE_DIR / ".env")

from src.social.browser_manager import BrowserManager
from src.watchers.base_watcher import BaseWatcher

logger = logging.getLogger(__name__)

# Keywords that trigger action-file creation (per hackathon spec)
ACTION_KEYWORDS = ["urgent", "asap", "invoice", "payment", "help", "price",
                   "pricing", "quote", "buy", "order", "meeting", "call"]

# ── WhatsApp Watcher ──────────────────────────────────────────────────────────

class WhatsAppWatcher(BaseWatcher):
    """
    Playwright-based WhatsApp Web watcher.

    Inherits BaseWatcher for vault path, needs_action_dir, and run loop.
    Overrides check_for_updates() and create_action_file().
    """

    def __init__(self, vault_path: Optional[str] = None, check_interval: int = 30):
        vault_path = vault_path or os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
        super().__init__(vault_path=vault_path, check_interval=check_interval)
        self._seen_messages: set = set()    # dedup across iterations
        self._lock = threading.Lock()

    # ── Core watcher methods ──────────────────────────────────────────────────

    def _session_exists(self) -> bool:
        """Return True if a WhatsApp browser session has been saved."""
        session_dir = _BASE_DIR / "config" / "sessions" / "whatsapp"
        return (session_dir / "Default").exists()

    def check_for_updates(self) -> List[Dict]:
        """
        Open WhatsApp Web, scan for unread chats containing keywords.
        Returns list of message dicts for create_action_file().
        """
        results = []

        # Skip if no session saved yet — avoid opening headed browser repeatedly
        if not self._session_exists():
            logger.info("WhatsApp: no session saved, skipping (run --login first to scan QR code)")
            return results

        try:
            # Handle asyncio loop conflict when running as daemon thread
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                logger.warning("WhatsApp: asyncio loop detected, skipping this iteration")
                return results
            except RuntimeError:
                pass  # No loop running, safe to use sync API

            with BrowserManager("whatsapp") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

                # Wait for chat list to be ready (up to 30s)
                try:
                    page.wait_for_selector('[data-testid="chat-list"]', timeout=30_000)
                except Exception:
                    logger.warning("WhatsApp: chat list not loaded — may need QR scan")
                    return results

                # Find all unread chat items
                unread_chats = page.query_selector_all(
                    '[data-testid="cell-frame-container"] [data-testid="icon-unread-count"]'
                )
                logger.info(f"WhatsApp: found {len(unread_chats)} unread chats")

                for badge in unread_chats:
                    try:
                        # Navigate up to the chat container
                        chat_el = badge.evaluate_handle(
                            "el => el.closest('[data-testid=\"cell-frame-container\"]')"
                        )
                        if not chat_el:
                            continue

                        # Extract contact name
                        name_el = chat_el.query_selector('[data-testid="cell-frame-title"]')
                        contact = name_el.inner_text().strip() if name_el else "Unknown"

                        # Extract last message preview
                        preview_el = chat_el.query_selector(
                            '[data-testid="last-msg-prefix"] + span, '
                            '.copyable-text span'
                        )
                        preview = preview_el.inner_text().strip() if preview_el else ""

                        # Keyword filter
                        full_text = (contact + " " + preview).lower()
                        matched_kw = [kw for kw in ACTION_KEYWORDS if kw in full_text]

                        if not matched_kw:
                            continue

                        # Open chat to get full message text
                        chat_el.click()
                        page.wait_for_load_state("networkidle", timeout=5000)

                        messages_els = page.query_selector_all(
                            '.message-in .selectable-text span[dir="ltr"]'
                        )
                        full_messages = []
                        for msg_el in messages_els[-5:]:   # last 5 incoming
                            txt = msg_el.inner_text().strip()
                            if txt:
                                full_messages.append(txt)

                        body = "\n".join(full_messages) or preview

                        # Dedup key: contact + first 80 chars of body
                        dedup_key = f"{contact}:{body[:80]}"
                        with self._lock:
                            if dedup_key in self._seen_messages:
                                continue
                            self._seen_messages.add(dedup_key)

                        results.append({
                            "contact":     contact,
                            "body":        body,
                            "keywords":    matched_kw,
                            "timestamp":   datetime.now().isoformat(),
                        })
                        logger.info(f"WhatsApp: actionable message from {contact!r} | keywords={matched_kw}")

                    except Exception as exc:
                        logger.warning(f"WhatsApp: error reading chat element: {exc}")
                        continue

        except Exception as exc:
            logger.error(f"WhatsApp watcher error: {exc}")

        return results

    def create_action_file(self, item: Dict) -> Path:
        """Write a Needs_Action file for an incoming WhatsApp message."""
        ts_iso  = item["timestamp"]
        ts_slug = datetime.fromisoformat(ts_iso).strftime("%Y%m%d_%H%M%S")
        contact_slug = re.sub(r"[^a-z0-9]+", "_", item["contact"].lower()).strip("_")[:40]
        task_id  = f"WA_{contact_slug}_{ts_slug}"
        filename = f"{task_id}.md"
        file_path = self.needs_action_dir / filename

        keywords_str = ", ".join(item["keywords"])
        content = f"""---
action: send_whatsapp
task_id: {task_id}
whatsapp_contact: {item['contact']}
keywords_detected: {keywords_str}
received: {ts_iso}
risk_level: low
---

# WhatsApp Message from {item['contact']}

## Sender
- **Contact**: {item['contact']}
- **Received**: {ts_iso[:19].replace('T', ' ')}
- **Keywords detected**: {keywords_str}

## Message

{item['body']}

## Action Required

Read the message above and draft a short, conversational WhatsApp reply.
Keep it concise and professional.

"""
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Created WhatsApp action file: {filename}")
        return file_path

    def send_whatsapp_reply(self, contact: str, message: str) -> bool:
        """
        Open WhatsApp Web, find the contact, and send a reply.
        Called by the approved-sender flow after human approval.
        """
        try:
            with BrowserManager("whatsapp") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                page.wait_for_selector('[data-testid="chat-list"]', timeout=30_000)

                # Use the search box to find the contact
                search = page.query_selector('[data-testid="search-container"] div[contenteditable]')
                if not search:
                    logger.error("WhatsApp: could not find search box")
                    return False

                search.click()
                search.fill(contact)
                page.wait_for_timeout(1500)

                # Click the first search result
                result = page.query_selector('[data-testid="cell-frame-title"]')
                if not result:
                    logger.error(f"WhatsApp: contact {contact!r} not found")
                    return False
                result.click()
                page.wait_for_timeout(1000)

                # Type and send the message
                input_box = page.query_selector(
                    '[data-testid="conversation-compose-box-input"]'
                )
                if not input_box:
                    logger.error("WhatsApp: compose box not found")
                    return False

                input_box.click()
                input_box.fill(message)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)

                logger.info(f"WhatsApp: reply sent to {contact!r}")
                return True

        except Exception as exc:
            logger.error(f"WhatsApp send error: {exc}")
            return False


# ── CLI: first-time login ─────────────────────────────────────────────────────

def _do_login():
    """Open headed browser for QR code scan. Session persists after close."""
    print("\n[WhatsApp Login]")
    print("A browser window will open. Scan the QR code with your phone.")
    print("Once you see your chats, press Enter here to save the session.\n")
    with BrowserManager("whatsapp", headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://web.whatsapp.com")
        input("Press Enter once WhatsApp Web is loaded and chats are visible... ")
    print("Session saved. Future runs will be headless.\n")


if __name__ == "__main__":
    from src.utils.logger import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="WhatsApp Playwright Watcher")
    parser.add_argument("--login", action="store_true",
                        help="Open headed browser for QR code scan (first time)")
    parser.add_argument("--vault-path", default=os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE"))
    args = parser.parse_args()

    if args.login:
        _do_login()
    else:
        WhatsAppWatcher(vault_path=args.vault_path).run()
