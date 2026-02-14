"""
Job Scheduler
=============
Cron-style scheduler for periodic AI Employee tasks.

Silver tier requirements:
- Daily briefings (Monday morning CEO briefing)
- Periodic LinkedIn posts (business updates)
- Social media checks (LinkedIn/Twitter/Facebook messages)

Usage:
  from src.scheduler.job_scheduler import JobScheduler

  scheduler = JobScheduler(vault_path)
  scheduler.add_job("daily_briefing", "0 8 * * 1", briefing_callback)  # Monday 8am
  scheduler.add_job("linkedin_check", "*/30 * * * *", linkedin_check)  # Every 30min
  scheduler.start()
"""

import os
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, Optional
from dataclasses import dataclass

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(_BASE_DIR / ".env")

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Scheduled job definition."""
    name: str
    cron_expr: str      # simplified: "*/5 * * * *" = every 5 min
    callback: Callable
    last_run: Optional[float] = None
    enabled: bool = True


class JobScheduler:
    """
    Simple cron-style scheduler for periodic tasks.

    Supports simplified cron expressions:
      "*/5 * * * *"  → every 5 minutes
      "0 8 * * 1"    → Monday 8:00 AM
      "0 0 * * *"    → daily at midnight
    """

    def __init__(self, vault_path: Optional[str] = None):
        vault_path = vault_path or os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
        self.vault = Path(vault_path)
        self._jobs: Dict[str, Job] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_job(self, name: str, cron_expr: str, callback: Callable):
        """Register a new scheduled job."""
        self._jobs[name] = Job(name=name, cron_expr=cron_expr, callback=callback)
        logger.info(f"Scheduler: registered job '{name}' with schedule '{cron_expr}'")

    def remove_job(self, name: str):
        """Remove a scheduled job."""
        if name in self._jobs:
            del self._jobs[name]
            logger.info(f"Scheduler: removed job '{name}'")

    def _should_run(self, job: Job) -> bool:
        """Return True if the job's cron expression triggers now."""
        now = datetime.now()

        parts = job.cron_expr.split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron expression for '{job.name}': '{job.cron_expr}' (expected 5 fields)")
            return False

        minute, hour, day, month, weekday = parts

        try:
            # Interval-based minute (e.g. "*/5") — check elapsed time only.
            if minute.startswith("*/"):
                interval = int(minute[2:])
                if interval <= 0:
                    raise ValueError(f"Interval must be > 0, got {interval}")
                return job.last_run is None or (time.time() - job.last_run) >= interval * 60

            # Exact-match fields
            if minute != "*" and now.minute != int(minute):
                return False
            if hour != "*" and now.hour != int(hour):
                return False
            if day != "*" and now.day != int(day):
                return False
            if month != "*" and now.month != int(month):
                return False
            if weekday != "*" and now.weekday() != int(weekday):
                return False

        except (ValueError, TypeError) as exc:
            logger.warning(f"Could not parse cron expression for '{job.name}': {exc}")
            return False

        # Prevent duplicate runs within the same minute.
        if job.last_run and (time.time() - job.last_run) < 60:
            return False

        return True

    def _run_loop(self):
        """Main scheduler loop."""
        logger.info("JobScheduler started")

        while self._running:
            try:
                for job in list(self._jobs.values()):
                    if not job.enabled:
                        continue

                    if self._should_run(job):
                        logger.info(f"Scheduler: executing job '{job.name}'")
                        try:
                            job.callback()
                            job.last_run = time.time()
                        except Exception as exc:
                            logger.error(f"Scheduler: job '{job.name}' failed: {exc}")

                time.sleep(30)  # Check every 30 seconds

            except Exception as exc:
                logger.error(f"Scheduler loop error: {exc}")
                time.sleep(60)

        logger.info("JobScheduler stopped")

    def start(self):
        """Start the scheduler in a background thread."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="JobScheduler")
        self._thread.start()
        logger.info("JobScheduler thread started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("JobScheduler stopped")


# ── Predefined job callbacks ──────────────────────────────────────────────────

def create_daily_briefing_job(vault_path: str) -> Callable:
    """
    Factory for daily briefing job.
    Scans Done/ folder, Business_Goals.md, and creates Monday briefing.
    """
    def _briefing():
        vault = Path(vault_path)
        briefings_dir = vault / "Briefings"
        briefings_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}_Monday_Briefing.md"
        briefing_file = briefings_dir / filename

        if briefing_file.exists():
            logger.info("Daily briefing already exists for today")
            return

        # Create a task for Claude to generate the briefing
        needs_action = vault / "Needs_Action"
        task_file = needs_action / f"BRIEFING_{today.strftime('%Y%m%d')}.md"

        content = f"""---
action: generate_briefing
task_id: BRIEFING_{today.strftime('%Y%m%d')}
created: {today.isoformat()}
risk_level: low
---

# Weekly Business Briefing Request

## Objective
Generate a Monday Morning CEO Briefing for the week ending {today.strftime('%Y-%m-%d')}.

## Instructions
1. Read Business_Goals.md for targets and metrics
2. Scan Done/ folder for completed tasks this week
3. Check Logs/ for activity patterns
4. Identify bottlenecks and proactive suggestions

## Output
Write the briefing to: {briefing_file}

Use the template from hackathon_full_doc.md (CEO Briefing Template).
"""
        task_file.write_text(content, encoding="utf-8")
        logger.info(f"Created briefing task: {task_file.name}")

    return _briefing


def create_linkedin_post_job(vault_path: str) -> Callable:
    """
    Factory for periodic LinkedIn post generation.
    Creates a task for Claude to draft a business update post.
    """
    def _linkedin_post():
        vault = Path(vault_path)
        needs_action = vault / "Needs_Action"

        today = datetime.now()
        task_file = needs_action / f"LINKEDIN_POST_{today.strftime('%Y%m%d_%H%M')}.md"

        if task_file.exists():
            return

        content = f"""---
action: draft_linkedin_post
task_id: LINKEDIN_POST_{today.strftime('%Y%m%d_%H%M')}
created: {today.isoformat()}
risk_level: low
---

# LinkedIn Business Update Post

## Objective
Draft a professional LinkedIn post to generate business leads and showcase expertise.

## Guidelines
- Highlight recent project completions or milestones
- Share a business insight or lesson learned
- Include a subtle call-to-action
- Keep it under 300 words
- Professional but conversational tone

## Output
Write the draft to Pending_Approval/ with action: post_linkedin
"""
        task_file.write_text(content, encoding="utf-8")
        logger.info(f"Created LinkedIn post task: {task_file.name}")

    return _linkedin_post


def create_weekly_audit_job(vault_path: str) -> Callable:
    """
    Factory for weekly business audit & CEO briefing.
    Creates a task for Claude to generate CEO briefing using Odoo MCP.
    """
    def _weekly_audit():
        vault = Path(vault_path)
        needs_action = vault / "Needs_Action"
        briefings_dir = vault / "Briefings"
        briefings_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now()
        task_file = needs_action / f"WEEKLY_AUDIT_{today.strftime('%Y%m%d')}.md"

        # Check if briefing already exists for today
        briefing_file = briefings_dir / f"CEO_Briefing_{today.strftime('%Y-%m-%d')}.md"
        if briefing_file.exists():
            logger.info("Weekly audit briefing already exists for today")
            return

        if task_file.exists():
            return

        content = f"""---
action: weekly_audit
task_id: WEEKLY_AUDIT_{today.strftime('%Y%m%d')}
created: {today.isoformat()}
risk_level: low
skill: weekly-audit
---

# Weekly Business Audit & CEO Briefing

## Objective
Generate comprehensive CEO briefing with financial data from Odoo.

## Instructions
Use the weekly-audit skill to:
1. Fetch financial summary from Odoo (last 30 days)
2. Get top customers and revenue data
3. Identify overdue invoices for follow-up
4. Analyze Business_Goals.md for target vs actual
5. Scan /Done/ folder for completed tasks
6. Generate actionable recommendations

## Output
Create briefing file: {briefing_file}

## Required MCP Tools
- odoo: get_financial_summary(days=30)
- odoo: get_customers(limit=10)
- odoo: get_overdue_invoices(min_days_overdue=1)

## Success Criteria
- All financial metrics populated with real data
- Top 5-10 customers listed
- Overdue invoices identified with amounts
- 5-7 actionable recommendations
- Briefing saved to /Briefings/
"""
        task_file.write_text(content, encoding="utf-8")
        logger.info(f"Created weekly audit task: {task_file.name}")

    return _weekly_audit


def _session_exists(platform: str) -> bool:
    """Check if a browser session exists for the given platform."""
    session_dir = _BASE_DIR / "config" / "sessions" / platform
    # Chromium session markers
    if (session_dir / "Default").exists():
        return True
    # Firefox session markers
    if (session_dir / "4886ce72.sqlite").exists():
        return True
    return False


def create_social_check_job(vault_path: str, platform: str) -> Callable:
    """Factory for periodic social media message checks."""
    def _check():
        # Skip if no session saved yet — avoids opening headed browser repeatedly
        if not _session_exists(platform):
            logger.info(f"Scheduler: skipping {platform} check — no session saved (run --login first)")
            return
        try:
            if platform == "linkedin":
                from src.social.linkedin import LinkedInWatcher
                LinkedInWatcher(vault_path).check_and_create_action_files()
            elif platform == "whatsapp":
                from src.watchers.whatsapp_watcher import WhatsAppWatcher
                watcher = WhatsAppWatcher(vault_path)
                items = watcher.check_for_updates()
                for item in items:
                    watcher.create_action_file(item)
        except Exception as exc:
            logger.error(f"Social check ({platform}) failed: {exc}")

    return _check


if __name__ == "__main__":
    from src.utils.logger import setup_logging
    setup_logging()

    vault = os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
    scheduler = JobScheduler(vault)

    # Example: Monday 8am briefing
    scheduler.add_job("daily_briefing", "0 8 * * 1", create_daily_briefing_job(vault))

    # Example: LinkedIn check every 30 minutes
    scheduler.add_job("linkedin_check", "*/30 * * * *", create_social_check_job(vault, "linkedin"))

    # Example: WhatsApp check every 5 minutes
    scheduler.add_job("whatsapp_check", "*/5 * * * *", create_social_check_job(vault, "whatsapp"))

    scheduler.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
