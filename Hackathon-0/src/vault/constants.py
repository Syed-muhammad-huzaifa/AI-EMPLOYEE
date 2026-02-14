"""Constants for vault operations."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Vault root ────────────────────────────────────────────────────────────────
# Resolved at import time from the environment.  Falls back to the Windows
# mount point for local dev; production must set VAULT_PATH in .env.

_raw = os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")
VAULT_PATH = Path(_raw)

# ── Sub-folders ───────────────────────────────────────────────────────────────

IN_PROGRESS_DIR      = VAULT_PATH / "In_Progress"
NEEDS_ACTION_DIR     = VAULT_PATH / "Needs_Action"
PLAN_DIR             = VAULT_PATH / "Plans"
DONE_DIR             = VAULT_PATH / "Done"
PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
APPROVED_DIR         = VAULT_PATH / "Approved"
REJECTED_DIR         = VAULT_PATH / "Rejected"
ACCOUNTING_DIR       = VAULT_PATH / "Accounting"
BRIEFINGS_DIR        = VAULT_PATH / "Briefings"
LOGS_DIR             = VAULT_PATH / "Logs"

# ── Well-known files ──────────────────────────────────────────────────────────

DASHBOARD_FILE       = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK_FILE = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS_FILE  = VAULT_PATH / "Business_Goals.md"

# ── Bootstrap: create directories (best-effort; skipped in test envs) ─────────

_ALL_DIRS = [
    IN_PROGRESS_DIR, NEEDS_ACTION_DIR, PLAN_DIR, DONE_DIR,
    PENDING_APPROVAL_DIR, APPROVED_DIR, REJECTED_DIR,
    ACCOUNTING_DIR, BRIEFINGS_DIR, LOGS_DIR,
]

for _dir in _ALL_DIRS:
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError as _exc:
        # Vault root may not exist in CI / test environments — log and continue.
        logger.debug(f"Could not create vault directory '{_dir}': {_exc}")
