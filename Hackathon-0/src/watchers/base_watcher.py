"""Base watcher class for all watchers in the AI employee system."""

import logging
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

from src.vault.manager import VaultManager
from src.utils.secrets_manager import load_secrets

logger = logging.getLogger(__name__)


class BaseWatcher(ABC):
    """Abstract base class for all watchers."""

    def __init__(self, vault_path: str, check_interval: int = 60):
        if not vault_path or not vault_path.strip():
            raise ValueError("vault_path must be a non-empty string.")
        if check_interval <= 0:
            raise ValueError(f"check_interval must be > 0, got {check_interval}.")

        self.vault_path = Path(vault_path)
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vault_manager = VaultManager(vault_path=self.vault_path)
        self.secrets = load_secrets()

        self._stop_event = threading.Event()

        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {self.vault_path}")

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for new events. Returns a list of items to process."""

    @abstractmethod
    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Write a .md action file into Needs_Action/. Returns the new path."""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Signal the run loop to exit after the current iteration."""
        self._stop_event.set()
        self.logger.info(f"{self.__class__.__name__} stop requested.")

    def run(self) -> None:
        """Main poll loop. Exits cleanly when stop() is called."""
        self.logger.info(f"Starting {self.__class__.__name__}")

        while not self._stop_event.is_set():
            try:
                items = self.check_for_updates()
                for item in items:
                    action_path = self.create_action_file(item)
                    self.vault_manager.log_activity(
                        f"{self.__class__.__name__} created action file",
                        {"file_created": str(action_path)},
                    )
            except Exception as exc:
                self.logger.error(
                    f"Error in {self.__class__.__name__}: {exc}", exc_info=True
                )
                self.vault_manager.log_activity(
                    f"{self.__class__.__name__} error",
                    {"error": str(exc)},
                )

            # Use wait() so stop() wakes us immediately instead of sleeping the full interval.
            self._stop_event.wait(timeout=self.check_interval)

        self.logger.info(f"{self.__class__.__name__} stopped.")
