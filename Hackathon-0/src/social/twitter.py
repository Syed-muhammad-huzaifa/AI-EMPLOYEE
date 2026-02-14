"""
Twitter/X Social Watcher + Poster
===================================
Silver/Gold tier: monitor DMs + mentions, post tweets with HITL.

Setup .env:
  TWITTER_EMAIL=your@email.com
  TWITTER_PASSWORD=yourpassword
  TWITTER_USERNAME=@yourhandle   (without @)

First login: python -m src.social.twitter --login
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

TW_HOME = "https://x.com"
TW_DMS  = "https://x.com/messages"


class TwitterWatcher:
    """Monitors Twitter/X for DMs. Posts tweets via Playwright after human approval."""

    def __init__(self, vault_path: Optional[str] = None):
        vault_path = vault_path or os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
        self.vault        = Path(vault_path)
        self.needs_action = self.vault / "Needs_Action"
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self._seen: set   = set()

    def _ensure_logged_in(self, page) -> bool:
        page.wait_for_timeout(1500)
        if "x.com" in page.url and "login" not in page.url and "i/flow" not in page.url:
            return True

        email    = os.getenv("TWITTER_EMAIL", "")
        password = os.getenv("TWITTER_PASSWORD", "")

        if not email or not password:
            logger.error("Twitter: set TWITTER_EMAIL and TWITTER_PASSWORD in .env")
            return False

        try:
            page.goto(f"{TW_HOME}/login", wait_until="domcontentloaded")
            page.wait_for_selector('input[name="text"]', timeout=10_000)
            page.fill('input[name="text"]', email)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)

            username_input = page.query_selector('input[name="text"]')
            if username_input:
                username = os.getenv("TWITTER_USERNAME", email.split("@")[0])
                page.fill('input[name="text"]', username)
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)

            page.wait_for_selector('input[name="password"]', timeout=10_000)
            page.fill('input[name="password"]', password)
            page.keyboard.press("Enter")
            page.wait_for_url("**/home**", timeout=15_000)
            logger.info("Twitter: logged in successfully")
            return True
        except Exception as exc:
            logger.error(f"Twitter: login failed — {exc}")
            return False

    def check_and_create_action_files(self) -> List[Path]:
        """Check DMs, create action files for new ones."""
        created = []

        try:
            with BrowserManager("twitter") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(TW_DMS, wait_until="domcontentloaded")

                if not self._ensure_logged_in(page):
                    return created

                page.wait_for_selector('[data-testid="conversation"]', timeout=20_000)
                dm_convs = page.query_selector_all('[data-testid="conversation"]')

                for conv in dm_convs[:10]:
                    try:
                        name_el = conv.query_selector('[data-testid="UserName"]')
                        sender  = name_el.inner_text().strip() if name_el else "Unknown"

                        preview_el = conv.query_selector('[data-testid="MessageTextContainer"] span')
                        preview = preview_el.inner_text().strip() if preview_el else ""

                        unread_badge = conv.query_selector('[data-testid="unreadBadge"], .r-1niwhzg')
                        if not unread_badge:
                            continue

                        dedup = f"tw_dm:{sender}:{preview[:60]}"
                        if dedup in self._seen:
                            continue
                        self._seen.add(dedup)

                        fp = self._create_action_file("dm", sender, preview)
                        created.append(fp)

                    except Exception as exc:
                        logger.warning(f"Twitter DM parse error: {exc}")

        except Exception as exc:
            logger.error(f"Twitter watcher error: {exc}")

        return created

    def _create_action_file(self, msg_type: str, sender: str, body: str) -> Path:
        ts_iso  = datetime.now().isoformat()
        ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug    = re.sub(r"[^a-z0-9]+", "_", sender.lower()).strip("_")[:40]
        task_id = f"TW_{slug}_{ts_slug}"
        fp      = self.needs_action / f"{task_id}.md"

        content = f"""---
action: send_twitter_dm
task_id: {task_id}
twitter_contact: {sender}
message_type: {msg_type}
received: {ts_iso}
risk_level: low
---

# Twitter/X {msg_type.upper()} from {sender}

## Sender
- **Handle**: {sender}
- **Type**: {msg_type}
- **Received**: {ts_iso[:19].replace('T', ' ')}

## Message

{body}

## Action Required

Draft a concise, professional Twitter reply (max 280 chars for tweets).
For DMs, can be longer.

"""
        fp.write_text(content, encoding="utf-8")
        logger.info(f"Created Twitter action file: {fp.name}")
        return fp

    def post_tweet(self, tweet_text: str) -> bool:
        """Post a tweet. Called after human approval."""
        if len(tweet_text) > 280:
            logger.warning(f"Tweet too long ({len(tweet_text)} chars), truncating")
            tweet_text = tweet_text[:277] + "..."

        try:
            with BrowserManager("twitter") as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(f"{TW_HOME}/home", wait_until="domcontentloaded")

                if not self._ensure_logged_in(page):
                    return False

                compose = page.query_selector(
                    '[data-testid="SideNav_NewTweet_Button"], a[href="/compose/tweet"]'
                )
                if not compose:
                    logger.error("Twitter: compose button not found")
                    return False

                compose.click()
                page.wait_for_timeout(1000)

                editor = page.query_selector(
                    '[data-testid="tweetTextarea_0"], .public-DraftEditor-content'
                )
                if not editor:
                    logger.error("Twitter: tweet editor not found")
                    return False

                editor.click()
                editor.fill(tweet_text)
                page.wait_for_timeout(500)

                send_btn = page.query_selector('[data-testid="tweetButton"]')
                if not send_btn:
                    logger.error("Twitter: send button not found")
                    return False

                send_btn.click()
                page.wait_for_timeout(3000)
                logger.info(f"Twitter: tweet posted ({len(tweet_text)} chars)")
                return True

        except Exception as exc:
            logger.error(f"Twitter post error: {exc}")
            return False


if __name__ == "__main__":
    import argparse
    from src.utils.logger import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Twitter/X Watcher")
    parser.add_argument("--login",  action="store_true")
    parser.add_argument("--check",  action="store_true")
    parser.add_argument("--tweet",  type=str)
    parser.add_argument("--vault-path", default=os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE"))
    args = parser.parse_args()

    if args.login:
        with BrowserManager("twitter", headless=False) as ctx:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(TW_HOME)
            input("Log in, then press Enter...")
        print("Session saved.")
    elif args.check:
        TwitterWatcher(args.vault_path).check_and_create_action_files()
    elif args.tweet:
        TwitterWatcher(args.vault_path).post_tweet(args.tweet)
