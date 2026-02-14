"""
LinkedIn Social Watcher + Poster
==================================
Silver tier: monitor LinkedIn messages/notifications + post business updates.

Setup:
  Add to .env:
    LINKEDIN_EMAIL=your@email.com
    LINKEDIN_PASSWORD=yourpassword

First login:
  python -m src.social.linkedin --login

Daemon mode (called by scheduler):
  from src.social.linkedin import LinkedInWatcher
  watcher = LinkedInWatcher(vault_path)
  watcher.check_and_create_action_files()   # called periodically
  watcher.post_from_approved(file_path)     # called when human approves a post
"""

import os
import re
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent.parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

load_dotenv(_BASE_DIR / ".env")

from src.social.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

LI_HOME   = "https://www.linkedin.com"
LI_FEED   = "https://www.linkedin.com/feed/"
LI_MSGS   = "https://www.linkedin.com/messaging/"


class LinkedInWatcher:
    """
    Monitors LinkedIn for:
    - New messages (creates action files in Needs_Action/)
    - Notification mentions / connection requests (logs)

    Posts:
    - LinkedIn posts from approved files (after human approval)
    """

    def __init__(self, vault_path: Optional[str] = None):
        vault_path = vault_path or os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
        self.vault        = Path(vault_path)
        self.needs_action = self.vault / "Needs_Action"
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self._seen: set   = set()

    def _ensure_logged_in(self, page) -> bool:
        """Return True if already logged in, else attempt login via credentials."""
        try:
            # Wait a moment for page to load
            page.wait_for_timeout(2000)

            current_url = page.url
            # If on any LinkedIn page that is NOT the login page, we're logged in
            if "linkedin.com" in current_url and "login" not in current_url and \
               "signup" not in current_url and "authwall" not in current_url:
                logger.info(f"LinkedIn: already logged in (URL: {current_url})")
                return True
        except Exception:
            pass

        # Not logged in, attempt login
        email    = os.getenv("LINKEDIN_EMAIL", "")
        password = os.getenv("LINKEDIN_PASSWORD", "")

        if not email or not password:
            logger.error("LinkedIn: set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env")
            return False

        try:
            logger.info("LinkedIn: attempting login...")
            page.goto(f"{LI_HOME}/login", wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            page.fill("#username", email)
            page.fill("#password", password)
            page.click('[data-litms-control-urn="login-submit"]')

            # Wait for either feed or verification page
            try:
                page.wait_for_url("**/feed/**", timeout=30_000)
                logger.info("LinkedIn: logged in successfully")
                return True
            except:
                # Check if we're on feed anyway (URL pattern might differ)
                page.wait_for_timeout(3000)
                if page.query_selector('[aria-label="Start a post"]'):
                    logger.info("LinkedIn: logged in successfully (alternate detection)")
                    return True
                raise

        except Exception as exc:
            logger.error(f"LinkedIn: login failed — {exc}")
            return False

    def check_and_create_action_files(self) -> List[Path]:
        """Scan LinkedIn messages and create action files for unread ones."""
        created = []

        try:
            with BrowserManager("linkedin") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(LI_MSGS, wait_until="domcontentloaded")

                if not self._ensure_logged_in(page):
                    return created

                page.wait_for_selector(".msg-conversations-container", timeout=20_000)

                conv_items = page.query_selector_all(".msg-conversation-listitem--unread")
                logger.info(f"LinkedIn: {len(conv_items)} unread conversations")

                for item in conv_items:
                    try:
                        name_el = item.query_selector(".msg-conversation-listitem__participant-names")
                        sender  = name_el.inner_text().strip() if name_el else "Unknown"

                        preview_el = item.query_selector(".msg-conversation-listitem__message-snippet")
                        preview    = preview_el.inner_text().strip() if preview_el else ""

                        dedup = f"li:{sender}:{preview[:60]}"
                        if dedup in self._seen:
                            continue
                        self._seen.add(dedup)

                        item.click()
                        page.wait_for_timeout(1500)

                        msg_els = page.query_selector_all(
                            ".msg-s-message-list__event:not(.msg-s-message-event--self) "
                            ".msg-s-event__content .msg-s-event-listitem__message-bubble"
                        )
                        full_text = "\n".join(
                            el.inner_text().strip() for el in msg_els[-5:] if el.inner_text().strip()
                        ) or preview

                        fp = self._create_action_file(sender, full_text)
                        created.append(fp)

                    except Exception as exc:
                        logger.warning(f"LinkedIn: error reading conversation: {exc}")

        except Exception as exc:
            logger.error(f"LinkedIn watcher error: {exc}")

        return created

    def _create_action_file(self, sender: str, message: str) -> Path:
        ts_iso  = datetime.now().isoformat()
        ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug    = re.sub(r"[^a-z0-9]+", "_", sender.lower()).strip("_")[:40]
        task_id = f"LI_{slug}_{ts_slug}"
        fp      = self.needs_action / f"{task_id}.md"

        content = f"""---
action: send_linkedin_message
task_id: {task_id}
linkedin_contact: {sender}
received: {ts_iso}
risk_level: low
---

# LinkedIn Message from {sender}

## Sender
- **Name**: {sender}
- **Received**: {ts_iso[:19].replace('T', ' ')}

## Message

{message}

## Action Required

Reply professionally to this LinkedIn message.
Tone: professional, concise. Do not over-promise.

"""
        fp.write_text(content, encoding="utf-8")
        logger.info(f"Created LinkedIn action file: {fp.name}")
        return fp

    def post_to_linkedin(self, post_text: str) -> bool:
        """Post to LinkedIn feed. Called by scheduler/approved-sender after human approves."""
        try:
            with BrowserManager("linkedin") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()

                # Navigate to feed and wait for full load
                logger.info("LinkedIn: navigating to feed...")
                page.goto(LI_FEED, wait_until="load", timeout=30_000)
                page.wait_for_timeout(4000)

                current_url = page.url
                logger.info(f"LinkedIn: page URL = {current_url}")

                # If not on feed, attempt login
                if "linkedin.com/feed" not in current_url:
                    logger.info("LinkedIn: not on feed, attempting login...")
                    if not self._ensure_logged_in(page):
                        return False
                    page.goto(LI_FEED, wait_until="load", timeout=30_000)
                    page.wait_for_timeout(3000)
                    current_url = page.url
                    if "linkedin.com/feed" not in current_url:
                        logger.error(f"LinkedIn: still not on feed after login. URL: {current_url}")
                        return False

                # Find "Start a post" button with multiple selectors
                start_post = None
                for selector in [
                    'button[aria-label="Start a post"]',
                    'button:has-text("Start a post")',
                    '.share-box-feed-entry__trigger',
                    '[data-control-name="share.sharebox_trigger"]',
                    'button.share-box-feed-entry__trigger',
                ]:
                    start_post = page.query_selector(selector)
                    if start_post:
                        break

                if not start_post:
                    logger.error(f"LinkedIn: could not find 'Start a post' button. URL: {page.url}")
                    return False

                logger.info("LinkedIn: clicking 'Start a post'...")
                start_post.click()
                page.wait_for_timeout(2000)

                # Find editor with multiple selectors
                editor = None
                for selector in [
                    '.ql-editor[contenteditable="true"]',
                    '[data-placeholder="What do you want to talk about?"]',
                    'div[role="textbox"]',
                    '.editor-content[contenteditable="true"]',
                ]:
                    editor = page.query_selector(selector)
                    if editor:
                        break

                if not editor:
                    logger.error("LinkedIn: post editor not found")
                    return False

                logger.info("LinkedIn: filling post content...")
                editor.click()
                editor.fill(post_text)
                page.wait_for_timeout(1000)

                # Find Post button
                post_btn = None
                for selector in [
                    'button.share-actions__primary-action',
                    'button[aria-label="Post"]',
                    '.share-actions__primary-action',
                ]:
                    post_btn = page.query_selector(selector)
                    if post_btn:
                        break

                if not post_btn:
                    logger.error("LinkedIn: Post button not found")
                    return False

                logger.info("LinkedIn: clicking Post button...")
                post_btn.click()
                page.wait_for_timeout(3000)
                logger.info("LinkedIn: post published successfully")
                return True

        except Exception as exc:
            logger.error(f"LinkedIn post error: {exc}")
            return False


if __name__ == "__main__":
    import argparse
    from src.utils.logger import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="LinkedIn Watcher")
    parser.add_argument("--login",  action="store_true", help="Open headed browser for login")
    parser.add_argument("--check",  action="store_true", help="Check messages now")
    parser.add_argument("--post",   type=str, metavar="TEXT", help="Post text to LinkedIn")
    parser.add_argument("--vault-path", default=os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE"))
    args = parser.parse_args()

    if args.login:
        print("Opening headed LinkedIn browser for login...")
        with BrowserManager("linkedin", headless=False) as ctx:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(LI_HOME)
            input("Log in, then press Enter to save session...")
        print("Session saved.")
    elif args.check:
        LinkedInWatcher(args.vault_path).check_and_create_action_files()
    elif args.post:
        ok = LinkedInWatcher(args.vault_path).post_to_linkedin(args.post)
        print("Posted!" if ok else "Failed to post.")
