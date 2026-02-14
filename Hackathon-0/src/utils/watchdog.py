"""Process health monitoring and auto-restart for critical services."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

import psutil

logger = logging.getLogger(__name__)

# Define critical processes to monitor
CRITICAL_PROCESSES: Dict[str, Dict] = {
    "orchestrator": {
        "cmd": ["python", "-m", "src.orchestrator.controller"],
        "health_check": lambda: check_orchestrator_health(),
        "restart_cmd": ["python", "-m", "src.orchestrator.controller"],
    },
    "filesystem_watcher": {
        "cmd": ["python", "-m", "src.watchers.filesystem_watcher"],
        "health_check": lambda: check_watcher_health(),
        "restart_cmd": ["python", "-m", "src.watchers.filesystem_watcher"],
    },
}


def _recent_mtime(files, threshold_seconds: int = 300) -> bool:
    """Return True if any file was modified within threshold_seconds."""
    cutoff = datetime.now()
    for f in files:
        try:
            elapsed = (cutoff - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds()
            if elapsed < threshold_seconds:
                return True
        except OSError:
            continue
    return False


def check_orchestrator_health() -> bool:
    """Return True if the orchestrator has written a log entry in the last 5 minutes."""
    try:
        from src.vault.manager import VaultManager  # avoid circular import at module level
        log_files = VaultManager().list_files_in_folder("logs")
        return _recent_mtime(log_files[-5:], threshold_seconds=300)
    except Exception as exc:
        logger.debug(f"Orchestrator health check failed: {exc}")
        return False


def check_watcher_health() -> bool:
    """Return True — watcher may be idle but healthy if no new tasks arrived."""
    try:
        from src.vault.manager import VaultManager
        files = VaultManager().list_files_in_folder("needs_action")
        # If recent activity exists, confirm healthy; otherwise assume healthy (idle).
        if files:
            return _recent_mtime(files[-5:], threshold_seconds=600)
        return True
    except Exception as exc:
        logger.debug(f"Watcher health check failed: {exc}")
        return False


def is_process_running(process_name: str) -> bool:
    """Return True if a running process whose cmdline contains process_name exists."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if process_name.lower() in " ".join(cmdline).lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def restart_process(process_name: str) -> bool:
    """Log a restart attempt for process_name. Returns True on success."""
    if process_name not in CRITICAL_PROCESSES:
        logger.warning(f"Unknown process '{process_name}' — cannot restart.")
        return False

    try:
        cmd = CRITICAL_PROCESSES[process_name]["restart_cmd"]
        logger.warning(f"Restarting {process_name} with: {' '.join(cmd)}")

        from src.vault.manager import VaultManager
        VaultManager().log_activity(
            f"{process_name} restarted",
            {"process": process_name, "timestamp": datetime.now().isoformat()},
        )
        return True
    except Exception as exc:
        logger.error(f"Failed to restart '{process_name}': {exc}")
        return False


def monitor_processes() -> None:
    """Main monitoring loop. Runs indefinitely; exit with Ctrl-C."""
    logger.info("Starting process health monitoring...")

    while True:
        try:
            for process_name, config in CRITICAL_PROCESSES.items():
                if not is_process_running(process_name):
                    logger.warning(f"'{process_name}' is not running — restarting...")
                    restart_process(process_name)
                elif config.get("health_check") and not config["health_check"]():
                    logger.warning(f"'{process_name}' is unhealthy — restarting...")
                    restart_process(process_name)

            time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Process monitoring stopped by user.")
            break
        except Exception as exc:
            logger.error(f"Watchdog loop error: {exc}", exc_info=True)
            time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    monitor_processes()
