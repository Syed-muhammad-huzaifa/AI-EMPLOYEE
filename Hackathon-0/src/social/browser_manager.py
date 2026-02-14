"""
BrowserManager
==============
Shared Playwright Chromium browser + per-platform persistent session management.

Each social platform gets its own session directory under config/sessions/<platform>/
so WhatsApp, LinkedIn, Twitter, and Facebook maintain independent login state.

Usage:
    from src.social.browser_manager import BrowserManager

    with BrowserManager("whatsapp") as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://web.whatsapp.com")
"""

import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

from playwright.sync_api import sync_playwright, BrowserContext, Playwright

_BASE_DIR = Path(__file__).parent.parent.parent          # Hackathon-0/
_SESSIONS_DIR = _BASE_DIR / "config" / "sessions"

logger = logging.getLogger(__name__)

# How long (ms) to wait for selectors before raising TimeoutError
DEFAULT_TIMEOUT_MS = 30_000

PLATFORM_URLS = {
    "whatsapp": "https://web.whatsapp.com",
    "linkedin":  "https://www.linkedin.com",
    "twitter":   "https://x.com",
    "facebook":  "https://www.facebook.com",
}


class BrowserManager:
    """
    Context-manager wrapper around Playwright's persistent browser context.

    - Each platform stores its session in config/sessions/<platform>/
    - First launch will be headful so the user can log in / scan QR code
    - Subsequent launches are headless (session is reused)
    - Automatically detects whether a session already exists
    """

    def __init__(
        self,
        platform: str,
        headless: Optional[bool] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        platform = platform.lower()
        if platform not in PLATFORM_URLS:
            raise ValueError(f"Unknown platform '{platform}'. Choose from {list(PLATFORM_URLS)}")

        self.platform    = platform
        self.timeout_ms  = timeout_ms
        self._session_dir = _SESSIONS_DIR / platform
        self._session_dir.mkdir(parents=True, exist_ok=True)

        # Auto-detect headless: headless if session already exists
        if headless is None:
            self._headless = self._session_exists()
        else:
            self._headless = headless

        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None

    def _session_exists(self) -> bool:
        """Return True if a Chromium profile directory has been populated."""
        markers = ["Default", "Default/Cookies", "Local State"]
        return any((self._session_dir / m).exists() for m in markers)

    def __enter__(self) -> BrowserContext:
        self._playwright = sync_playwright().start()

        mode = "headless" if self._headless else "headed (first-time login)"
        logger.info(f"[{self.platform}] Launching browser ({mode}) | session={self._session_dir}")

        self._context = self._playwright.chromium.launch_persistent_context(
            str(self._session_dir),
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._context.set_default_timeout(self.timeout_ms)
        return self._context

    def __exit__(self, *_):
        try:
            if self._context:
                self._context.close()
        except Exception as exc:
            logger.warning(f"[{self.platform}] Error closing context: {exc}")
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception as exc:
            logger.warning(f"[{self.platform}] Error stopping playwright: {exc}")

    @contextmanager
    def page(self):
        """Convenience: open browser context and yield an active page."""
        with self as ctx:
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.set_default_timeout(self.timeout_ms)
            try:
                yield pg
            finally:
                pass   # context closed by __exit__


def get_or_open_page(platform: str, url: Optional[str] = None, headless: Optional[bool] = None):
    """
    Return (playwright_instance, context, page) for manual lifecycle management.
    Caller is responsible for calling context.close() and playwright.stop().
    """
    session_dir = _SESSIONS_DIR / platform.lower()
    session_dir.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        str(session_dir),
        headless=headless if headless is not None else (session_dir / "Default").exists(),
        args=["--no-sandbox", "--disable-setuid-sandbox",
              "--disable-dev-shm-usage", "--disable-gpu",
              "--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    ctx.set_default_timeout(DEFAULT_TIMEOUT_MS)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    if url:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        except Exception as exc:
            logger.warning(f"[{platform}] Could not navigate to {url}: {exc}")
    return pw, ctx, page
