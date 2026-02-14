"""File locking utilities for the claim-by-move pattern."""

import os
import time
import errno
from pathlib import Path
from typing import Optional, Union


class FileLock:
    """Simple file-based locking mechanism."""
    
    def __init__(self, file_path: Path, timeout: int = 10):
        self.file_path = file_path
        self.lock_file_path = file_path.with_suffix(file_path.suffix + '.lock')
        self.timeout = timeout
        self.acquired = False
    
    def acquire(self) -> bool:
        """Acquire the lock.

        Always makes at least one attempt regardless of timeout value.
        Retries until timeout is exceeded if the lock is already held.
        """
        start_time = time.time()

        while True:
            try:
                # Attempt to create the lock file exclusively
                fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.acquired = True
                return True
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                # Lock file already exists; give up if timeout exceeded
                if time.time() - start_time >= self.timeout:
                    return False
                time.sleep(0.1)
    
    def release(self):
        """Release the lock."""
        if self.acquired:
            try:
                self.lock_file_path.unlink()
                self.acquired = False
            except FileNotFoundError:
                # Lock file was already removed
                pass


def claim_task(task_file: Path, agent_name: str, in_progress_dir: Path) -> Optional[Path]:
    """Attempt to claim a task using the claim-by-move pattern.

    Returns the new path of the task file on success, or None if the task
    could not be claimed (already taken by another worker).
    """
    lock = FileLock(task_file)

    if lock.acquire():
        try:
            # Guard: file may have been removed between listing and claiming.
            if not task_file.exists():
                return None

            # Move the task to the agent's in-progress directory
            agent_in_progress = in_progress_dir / agent_name
            agent_in_progress.mkdir(exist_ok=True)

            new_task_path = agent_in_progress / task_file.name
            task_file.rename(new_task_path)

            return new_task_path
        finally:
            lock.release()

    return None  # Could not acquire lock, task already claimed