"""
Facebook Social Watcher + Poster
===================================
Gold tier: monitor FB Messenger + page notifications, post business updates.

Setup .env:
  FACEBOOK_EMAIL=your@email.com
  FACEBOOK_PASSWORD=yourpassword

First login: python -m src.social.facebook --login
"""

import os
import re
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent.parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

load_dotenv(_BASE_DIR / ".env")

from src.social.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

FB_HOME  = "https://www.facebook.com"
FB_MSGS  = "https://www.facebook.com/messages"


class FacebookWatcher:
    """Monitors Facebook Messenger for unread messages. Posts to Facebook after human approval."""

    def __init__(self, vault_path: Optional[str] = None):
        vault_path = vault_path or os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
        self.vault        = Path(vault_path)
        self.needs_action = self.vault / "Needs_Action"
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self._seen: set   = set()

    def _ensure_logged_in(self, page) -> bool:
        page.wait_for_timeout(1500)
        if "facebook.com" in page.url and "login" not in page.url and \
           "signup" not in page.url and "checkpoint" not in page.url:
            return True

        email    = os.getenv("FACEBOOK_EMAIL", "")
        password = os.getenv("FACEBOOK_PASSWORD", "")

        if not email or not password:
            logger.error("Facebook: set FACEBOOK_EMAIL and FACEBOOK_PASSWORD in .env")
            return False

        try:
            page.goto(FB_HOME, wait_until="domcontentloaded")
            page.wait_for_selector('#email', timeout=10_000)
            page.fill('#email', email)
            page.fill('#pass', password)
            page.click('[name="login"]')
            page.wait_for_url(f"{FB_HOME}/**", timeout=15_000)

            if "checkpoint" in page.url or "two_step" in page.url:
                logger.warning("Facebook: 2FA checkpoint detected — run with --login for manual resolution")
                return False

            logger.info("Facebook: logged in successfully")
            return True
        except Exception as exc:
            logger.error(f"Facebook: login failed — {exc}")
            return False

    def check_and_create_action_files(self) -> List[Path]:
        """Scan Messenger for unread messages, create action files."""
        created = []

        try:
            with BrowserManager("facebook") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(FB_MSGS, wait_until="domcontentloaded")

                if not self._ensure_logged_in(page):
                    return created

                page.wait_for_timeout(3000)

                thread_items = page.query_selector_all('[role="row"], .x1n2onr6 [aria-selected]')

                for item in thread_items[:15]:
                    try:
                        bold_name = item.query_selector('span[style*="font-weight: 700"], b')
                        if not bold_name:
                            continue

                        sender  = bold_name.inner_text().strip()
                        preview_el = item.query_selector('span:not([class]):last-child, .x193iq5w span')
                        preview = preview_el.inner_text().strip() if preview_el else ""

                        dedup = f"fb:{sender}:{preview[:60]}"
                        if dedup in self._seen:
                            continue
                        self._seen.add(dedup)

                        fp = self._create_action_file(sender, preview)
                        created.append(fp)

                    except Exception as exc:
                        logger.warning(f"Facebook: error reading thread: {exc}")

        except Exception as exc:
            logger.error(f"Facebook watcher error: {exc}")

        return created

    def _create_action_file(self, sender: str, message: str) -> Path:
        ts_iso  = datetime.now().isoformat()
        ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug    = re.sub(r"[^a-z0-9]+", "_", sender.lower()).strip("_")[:40]
        task_id = f"FB_{slug}_{ts_slug}"
        fp      = self.needs_action / f"{task_id}.md"

        content = f"""---
action: send_facebook_message
task_id: {task_id}
facebook_contact: {sender}
received: {ts_iso}
risk_level: low
---

# Facebook Message from {sender}

## Sender
- **Name**: {sender}
- **Received**: {ts_iso[:19].replace('T', ' ')}

## Message

{message}

## Action Required

Draft a professional, friendly reply to this Facebook message.

"""
        fp.write_text(content, encoding="utf-8")
        logger.info(f"Created Facebook action file: {fp.name}")
        return fp

    def post_to_facebook(self, post_text: str) -> bool:
        """Post to Facebook timeline/page after human approval."""
        try:
            with BrowserManager("facebook") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(FB_HOME, wait_until="domcontentloaded")

                if not self._ensure_logged_in(page):
                    return False

                compose = page.query_selector(
                    '[aria-label="Create a post"], [placeholder="What\'s on your mind?"]'
                )
                if not compose:
                    logger.error("Facebook: compose area not found")
                    return False

                compose.click()
                page.wait_for_timeout(1500)

                editor = page.query_selector(
                    '[contenteditable="true"][role="textbox"], [data-lexical-editor="true"]'
                )
                if not editor:
                    logger.error("Facebook: post editor not found")
                    return False

                editor.fill(post_text)
                page.wait_for_timeout(500)

                post_btn = page.query_selector('[aria-label="Post"], button[type="submit"]')
                if not post_btn:
                    logger.error("Facebook: Post button not found")
                    return False

                post_btn.click()
                page.wait_for_timeout(3000)
                logger.info("Facebook: post published")
                return True

        except Exception as exc:
            logger.error(f"Facebook post error: {exc}")
            return False


if __name__ == "__main__":
    import argparse
    from src.utils.logger import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Facebook Watcher")
    parser.add_argument("--login",  action="store_true")
    parser.add_argument("--check",  action="store_true")
    parser.add_argument("--post",   type=str)
    parser.add_argument("--vault-path", default=os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE"))
    args = parser.parse_args()

    if args.login:
        with BrowserManager("facebook", headless=False) as ctx:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(FB_HOME)
            input("Log in, then press Enter...")
        print("Session saved.")
    elif args.check:
        FacebookWatcher(args.vault_path).check_and_create_action_files()
    elif args.post:
        FacebookWatcher(args.vault_path).post_to_facebook(args.post)
