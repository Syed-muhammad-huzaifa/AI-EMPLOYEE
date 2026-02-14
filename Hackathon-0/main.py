"""Main entry point for the Personal AI Employee - Bronze Phase + Gmail Integration."""

import argparse
import os
import signal
import sys
import time
import threading
import subprocess
from pathlib import Path

from src.watchers.filesystem_watcher import FilesystemWatcher
from src.watchers.approved_email_sender import ApprovedEmailSender
from src.orchestrator.controller import OrchestratorController
from src.dashboard.updater import DashboardUpdater
from src.utils.logger import setup_logging


# ── Shutdown ──────────────────────────────────────────────────────────────────

_components = []   # registered stop() callables


def signal_handler(_sig, _frame):
    print("\nShutting down AI Employee system...")
    for stop_fn in _components:
        try:
            stop_fn()
        except Exception as exc:
            print(f"  Warning: error during shutdown: {exc}")
    sys.exit(0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_claude_available() -> bool:
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_gmail_token(vault_path: str) -> bool:
    token = Path(__file__).parent / "config" / "gmail_token.pickle"
    if not token.exists():
        print(f"  ⚠️  Gmail token not found at {token}")
        print("  Run: python scripts/authenticate_gmail.py")
        return False
    return True


def start_daemon(target, name: str, **kwargs) -> threading.Thread:
    t = threading.Thread(target=target, kwargs=kwargs, daemon=True, name=name)
    t.start()
    return t


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Personal AI Employee")
    parser.add_argument("--mode", choices=["watcher", "orchestrator", "both"],
                        default="both", help="Run mode")
    parser.add_argument("--vault-path", type=str,
                        default=os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE"),
                        help="Path to the Obsidian vault (default: $VAULT_PATH)")
    parser.add_argument("--log-level", type=str, default="INFO")
    parser.add_argument("--check-interval", type=int, default=10,
                        choices=range(1, 3601), metavar="[1-3600]",
                        help="Orchestrator poll interval in seconds (default: 10)")
    parser.add_argument("--no-gmail", action="store_true",
                        help="Disable Gmail watcher even if token is available")
    parser.add_argument("--no-whatsapp", action="store_true",
                        help="Disable WhatsApp watcher")
    parser.add_argument("--no-scheduler", action="store_true",
                        help="Disable job scheduler (briefings, social posts)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Enable DRY_RUN for email sending (no real emails sent)")

    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    # Check Claude
    if args.mode in ("orchestrator", "both"):
        if not check_claude_available():
            print("Warning: Claude CLI not found. Orchestrator may not work.")
            print("Install Claude Code CLI to enable AI reasoning.")
            # Skip interactive prompt if running in non-interactive mode (e.g., PM2)
            if sys.stdin.isatty():
                if input("Continue anyway? (y/n): ").strip().lower() not in ("y", "yes"):
                    sys.exit(1)
            else:
                print("Running in non-interactive mode, continuing anyway...")

    setup_logging(log_level=args.log_level)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("  Personal AI Employee — Bronze Phase + Gmail Integration")
    print("=" * 60)
    print(f"  Mode       : {args.mode}")
    print(f"  Vault      : {args.vault_path}")
    print(f"  Dry Run    : {args.dry_run}")
    print("=" * 60)

    # ── Filesystem watcher (Inbox/) ───────────────────────────────────────────
    if args.mode in ("watcher", "both"):
        inbox_path = Path(args.vault_path) / "Inbox"
        inbox_path.mkdir(exist_ok=True)

        fs_watcher = FilesystemWatcher(
            args.vault_path, [str(inbox_path)], check_interval=10
        )
        if args.mode == "both":
            start_daemon(fs_watcher.run, "FilesystemWatcher")
            print(f"  ✅ Filesystem watcher   → monitoring {inbox_path}")
        else:
            print(f"  ✅ Filesystem watcher   → monitoring {inbox_path}")
            fs_watcher.run()   # foreground

    # ── Gmail watcher (Gmail inbox) ───────────────────────────────────────────
    gmail_active = False
    if not args.no_gmail and args.mode in ("watcher", "both"):
        if check_gmail_token(args.vault_path):
            try:
                from src.watchers.gmail_watcher import GmailWatcher
                gmail_watcher = GmailWatcher(
                    vault_path=args.vault_path, check_interval=120
                )
                _components.append(gmail_watcher.stop if hasattr(gmail_watcher, "stop") else lambda: None)
                start_daemon(gmail_watcher.run, "GmailWatcher")
                print("  ✅ Gmail watcher        → monitoring Gmail inbox (every 120s)")
                gmail_active = True
            except Exception as exc:
                print(f"  ⚠️  Gmail watcher failed to start: {exc}")
        else:
            print("  ⚠️  Gmail watcher       → SKIPPED (no token)")

    # ── WhatsApp watcher (Playwright-based) ──────────────────────────────────
    if not args.no_whatsapp and args.mode in ("watcher", "both"):
        try:
            from src.watchers.whatsapp_watcher import WhatsAppWatcher
            wa_watcher = WhatsAppWatcher(vault_path=args.vault_path, check_interval=30)
            start_daemon(wa_watcher.run, "WhatsAppWatcher")
            print("  ✅ WhatsApp watcher     → Playwright-based (every 30s)")
        except Exception as exc:
            print(f"  ⚠️  WhatsApp watcher failed to start: {exc}")

    # ── Job Scheduler (briefings, social posts) ──────────────────────────────
    if not args.no_scheduler and args.mode in ("watcher", "both"):
        try:
            from src.scheduler.job_scheduler import (
                JobScheduler, create_daily_briefing_job,
                create_linkedin_post_job, create_social_check_job,
                create_weekly_audit_job
            )
            scheduler = JobScheduler(args.vault_path)

            # Monday 8am briefing
            scheduler.add_job("daily_briefing", "0 8 * * 1", create_daily_briefing_job(args.vault_path))

            # Sunday 9am weekly audit (Gold Tier - Odoo integration)
            scheduler.add_job("weekly_audit", "0 9 * * 0", create_weekly_audit_job(args.vault_path))

            # LinkedIn check every 30 minutes (only runs if session exists)
            scheduler.add_job("linkedin_check", "*/60 * * * *", create_social_check_job(args.vault_path, "linkedin"))

            # LinkedIn post suggestion every Monday 10am
            scheduler.add_job("linkedin_post", "0 10 * * 1", create_linkedin_post_job(args.vault_path))

            scheduler.start()
            _components.append(scheduler.stop)
            print("  ✅ Job Scheduler        → briefings + social checks + weekly audit")
        except Exception as exc:
            print(f"  ⚠️  Job Scheduler failed to start: {exc}")

    # ── Approved email sender (Approved/) ────────────────────────────────────
    approved_sender = ApprovedEmailSender(
        vault_path=args.vault_path,
        check_interval=15,
        dry_run=args.dry_run,
    )
    _components.append(approved_sender.stop)
    start_daemon(approved_sender.run, "ApprovedEmailSender")
    dry_tag = " [DRY RUN]" if args.dry_run else ""
    print(f"  ✅ Approved email sender → watching Approved/{dry_tag}")

    # ── Dashboard updater ─────────────────────────────────────────────────────
    dashboard = DashboardUpdater(vault_path=Path(args.vault_path))
    _components.append(dashboard.stop)
    start_daemon(dashboard.run_loop, "DashboardUpdater", interval=30)
    print("  ✅ Dashboard updater    → refreshing every 30s")

    # ── Orchestrator (main thread, blocking) ──────────────────────────────────
    if args.mode in ("orchestrator", "both"):
        if args.mode == "both":
            time.sleep(1)  # let daemon threads initialise

        print(f"  ✅ Orchestrator         → polling Needs_Action/ every {args.check_interval}s")
        print("=" * 60)

        orchestrator = OrchestratorController()
        orchestrator.start_monitoring(check_interval=args.check_interval)
    else:
        print("=" * 60)
        # Keep main thread alive for daemon threads
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            signal_handler(None, None)


if __name__ == "__main__":
    main()
