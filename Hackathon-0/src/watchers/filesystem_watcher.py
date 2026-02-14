"""Filesystem watcher implementation for the AI employee system."""

import re
import time
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from src.watchers.base_watcher import BaseWatcher


class FilesystemWatcher(BaseWatcher):
    """Filesystem watcher that monitors for file changes."""

    def __init__(self, vault_path: str, monitor_paths: List[str], check_interval: int = 10):
        super().__init__(vault_path, check_interval)
        self.monitor_paths = [Path(p) for p in monitor_paths]
        self.file_hashes: Dict[str, str] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Snapshot existing files so we don't re-trigger on startup
        self._update_initial_hashes()

    # ── Hashing ───────────────────────────────────────────────────────────────

    def _update_initial_hashes(self):
        """Snapshot all current files so we only react to NEW arrivals later."""
        for path in self.monitor_paths:
            if not path.exists():
                continue
            if path.is_file():
                self.file_hashes[str(path)] = self._get_file_hash(path)
            elif path.is_dir():
                for fp in path.rglob('*'):
                    if fp.is_file() and '_processed' not in fp.parts:
                        self.file_hashes[str(fp)] = self._get_file_hash(fp)

    def _get_file_hash(self, file_path: Path) -> str:
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not hash {file_path}: {e}")
            return hashlib.md5(b'').hexdigest()

    # ── Change detection ──────────────────────────────────────────────────────

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Return only NEWLY dropped files (previous_hash is None).
        Modifications to already-known files are ignored — they are likely
        being edited by the user while in progress.
        """
        new_files: List[Dict[str, Any]] = []

        for path in self.monitor_paths:
            if not path.exists():
                continue

            if path.is_file():
                self._check_single_file(path, new_files)
            elif path.is_dir():
                for fp in path.rglob('*'):
                    # Skip the _processed archive sub-folder
                    if '_processed' in fp.parts:
                        continue
                    if fp.is_file():
                        self._check_single_file(fp, new_files)

                # Clean up deleted-file entries from the cache
                stale = [k for k in list(self.file_hashes)
                         if k.startswith(str(path)) and not Path(k).exists()]
                for k in stale:
                    del self.file_hashes[k]

        return new_files

    def _check_single_file(self, file_path: Path, out: List[Dict[str, Any]]):
        try:
            current_hash = self._get_file_hash(file_path)
            previous_hash = self.file_hashes.get(str(file_path))

            if previous_hash is None:
                # Brand-new file → create an action
                out.append({
                    'type': 'new_file',
                    'path': str(file_path),
                    'timestamp': datetime.now().isoformat(),
                })
            # Always keep the hash up-to-date so we don't re-trigger
            self.file_hashes[str(file_path)] = current_hash
        except Exception as e:
            self.logger.error(f"Error checking {file_path}: {e}")

    # ── Action file creation ───────────────────────────────────────────────────

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """
        Create a descriptive .md task file in Needs_Action/ for a dropped inbox file.

        - File name is derived from the inbox file's own name (slugified).
        - The CONTENT of the inbox file is embedded so Claude knows the actual task.
        - The original inbox file is moved to Inbox/_processed/ to clear the inbox.
        """
        inbox_path = Path(item['path'])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ── Read actual task content from the dropped file ─────────────────
        task_content = ""
        if inbox_path.exists():
            try:
                task_content = inbox_path.read_text(encoding='utf-8').strip()
            except Exception as e:
                self.logger.warning(f"Could not read inbox file content: {e}")

        # ── Build descriptive filename from the inbox file's stem ──────────
        raw_name = inbox_path.stem          # e.g. "write an email for my client..."
        slug = re.sub(r'[^a-z0-9]+', '_', raw_name.lower()).strip('_')[:60]
        if not slug:
            slug = "inbox_task"
        filename = f"{slug}_{timestamp}.md"
        action_file = self.needs_action_dir / filename

        # ── Compose action file content ────────────────────────────────────
        # If the inbox file had no body, the task description IS the filename
        if task_content:
            task_section = task_content
        else:
            task_section = raw_name

        content = f"""# Task: {raw_name}

## Source
- **From**: Inbox (file drop)
- **File**: {inbox_path.name}
- **Received**: {item['timestamp']}

## Task Description

{task_section}
"""

        try:
            self.needs_action_dir.mkdir(parents=True, exist_ok=True)
            action_file.write_text(content, encoding='utf-8')
            self.logger.info(f"Created action file: {action_file.name}")
        except Exception as e:
            self.logger.error(f"Error writing action file: {e}")
            raise

        # ── Archive the original inbox file so it leaves the Inbox ────────
        if inbox_path.exists():
            processed_dir = inbox_path.parent / "_processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            dest = processed_dir / f"{inbox_path.stem}_{timestamp}{inbox_path.suffix}"
            try:
                inbox_path.rename(dest)
                self.logger.info(f"Archived '{inbox_path.name}' → Inbox/_processed/")
                # Remove from hash cache so we don't track the moved file
                self.file_hashes.pop(str(inbox_path), None)
            except Exception as e:
                self.logger.warning(f"Could not archive inbox file: {e}")

        return action_file