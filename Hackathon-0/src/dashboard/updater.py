"""
Dashboard updater — reads real vault folder counts and rewrites Dashboard.md.

Can be run as a one-shot update or as a background loop:

    from src.dashboard.updater import DashboardUpdater
    updater = DashboardUpdater()
    updater.update()          # single update
    updater.run_loop(30)      # update every 30 s
"""

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict

from src.vault.manager import VaultManager

logger = logging.getLogger(__name__)


class DashboardUpdater:
    """Reads live vault state and rewrites Dashboard.md."""

    def __init__(self, vault_path: Path = None):
        self.vm = VaultManager(vault_path=vault_path)
        self.vault = self.vm.vault_path
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ #
    # Stats gathering
    # ------------------------------------------------------------------ #

    def _count_folder(self, key: str) -> int:
        """Count .md files in a named vault folder (top-level only)."""
        try:
            return len([f for f in self.vm.list_files_in_folder(key)
                        if f.suffix == '.md'])
        except Exception as e:
            logger.debug(f"Could not count folder '{key}': {e}")
            return 0

    def _count_in_progress(self) -> int:
        """In_Progress uses agent sub-dirs; scan recursively."""
        try:
            return len(list((self.vault / "In_Progress").rglob("*.md")))
        except Exception as e:
            logger.debug(f"Could not count in_progress folder: {e}")
            return 0

    def _count_failed(self) -> int:
        try:
            failed_dir = self.vault / "Failed"
            if not failed_dir.exists():
                return 0
            return len(list(failed_dir.glob("*.md")))
        except Exception as e:
            logger.debug(f"Could not count failed folder: {e}")
            return 0

    def _recent_log_entries(self, limit: int = 10):
        """Read last N lines from today's .md log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.vault / "Logs" / f"{today}.md"
        if not log_file.exists():
            return []
        lines = log_file.read_text(encoding="utf-8").splitlines()
        # Return non-empty, non-header lines
        entries = [l for l in lines if l.startswith("- ")]
        return entries[-limit:]

    def _pending_approval_items(self):
        """Return list of filenames waiting in Pending_Approval/."""
        try:
            return [f.name for f in self.vm.list_files_in_folder('pending_approval')
                    if f.suffix == '.md']
        except Exception as e:
            logger.debug(f"Could not list pending_approval items: {e}")
            return []

    def get_stats(self) -> Dict:
        return {
            "needs_action":     self._count_folder("needs_action"),
            "in_progress":      self._count_in_progress(),
            "pending_approval": self._count_folder("pending_approval"),
            "approved":         self._count_folder("approved"),
            "rejected":         self._count_folder("rejected"),
            "done":             self._count_folder("done"),
            "failed":           self._count_failed(),
            "total_processed":  self._count_folder("done") + self._count_failed(),
        }

    # ------------------------------------------------------------------ #
    # Dashboard rendering
    # ------------------------------------------------------------------ #

    def _render(self, stats: Dict) -> str:
        now = datetime.now()
        now_str = now.strftime("%b %d, %Y at %I:%M %p")
        now_iso = now.isoformat()

        pending_items = self._pending_approval_items()
        pending_block = ""
        if pending_items:
            pending_block = "\n".join(
                f"- ⏸️ **{name}** → [Review](Pending_Approval/{name})"
                for name in pending_items
            )
        else:
            pending_block = "_Nothing waiting — all clear! 🎉_"

        recent = self._recent_log_entries(10)
        recent_block = "\n".join(recent) if recent else "_No activity yet today._"

        needs_status   = "⚠️" if stats["needs_action"] > 0   else "🟢"
        pending_status = "⏸️" if stats["pending_approval"] > 0 else "🟢"
        failed_status  = "🔴" if stats["failed"] > 0          else "🟢"
        progress_status= "▶️" if stats["in_progress"] > 0     else "🟢"

        return f"""---
last_updated: {now_iso}
system_status: active
vault_path: {self.vault}
---

# 🤖 AI Employee Dashboard

> **Last Updated**: {now_str}
> **System Status**: 🟢 **ACTIVE**

---

## 📊 Live Task Summary

| Metric | Count | Status |
|---|---|---|
| **Needs Action** | {stats['needs_action']} | {needs_status} |
| **In Progress** | {stats['in_progress']} | {progress_status} |
| **Awaiting Approval** | {stats['pending_approval']} | {pending_status} |
| **Approved** | {stats['approved']} | ✅ |
| **Rejected** | {stats['rejected']} | ❌ |
| **Done** | {stats['done']} | ✅ |
| **Failed** | {stats['failed']} | {failed_status} |
| **Total Processed** | {stats['total_processed']} | 📦 |

---

## 🔔 Pending Approvals (Need Your Attention)

{pending_block}

---

## ⚡ Recent Activity (Today)

{recent_block}

---

## 🔗 Quick Links

- [📥 Needs Action](Needs_Action/)
- [⚙️ In Progress](In_Progress/)
- [🔔 Pending Approval](Pending_Approval/)
- [✅ Done](Done/)
- [📋 Plans](Plans/)
- [📝 Logs](Logs/)
- [📖 Company Handbook](Company_Handbook.md)
- [🎯 Business Goals](Business_Goals.md)

---

_Auto-updated every 30 seconds by DashboardUpdater_
"""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def update(self):
        """Read vault state and rewrite Dashboard.md once."""
        try:
            stats = self.get_stats()
            content = self._render(stats)
            self.vm.write_file(self.vault / "Dashboard.md", content)
            logger.info(
                f"Dashboard updated — needs_action={stats['needs_action']} "
                f"pending={stats['pending_approval']} done={stats['done']}"
            )
        except Exception as e:
            logger.exception(f"Dashboard update failed: {e}")

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._stop_event.set()

    def run_loop(self, interval: int = 30) -> None:
        """Continuously update Dashboard.md every `interval` seconds.

        Exits cleanly when stop() is called.
        """
        if interval <= 0:
            raise ValueError(f"interval must be > 0, got {interval}")

        logger.info(f"Dashboard updater started (interval={interval}s)")
        while not self._stop_event.is_set():
            self.update()
            self._stop_event.wait(timeout=interval)
