"""Orchestrator controller - watches folders and invokes process-needs-action skill."""

import time
import logging
from pathlib import Path

from src.vault.manager import VaultManager
from src.utils.file_lock import claim_task
from src.utils.config_loader import load_vault_config
from src.ralph.loop_manager import RalphLoopManager


logger = logging.getLogger(__name__)


class OrchestratorController:
    """Watches vault folders and invokes the process-needs-action skill."""

    def __init__(self, config_path: str = "config/vault_config.json"):
        self.config = load_vault_config(config_path)
        self.vault_manager = VaultManager()
        self.ralph_manager = RalphLoopManager()
        self.running = False
        self.retry_delay = self.config.get('retry_delay', 5)

    def start_monitoring(self, check_interval: int = 10):
        """Start monitoring the needs_action folder."""
        self.running = True
        logger.info("Starting orchestrator controller...")

        # On startup, recover any tasks stuck in In_Progress from a previous crash
        self._recover_stuck_tasks()

        while self.running:
            try:
                new_tasks = self.vault_manager.list_files_in_folder('needs_action')

                for task_file in new_tasks:
                    logger.info(f"Found new task: {task_file.name}")
                    claimed_path = claim_task(
                        task_file, "orchestrator",
                        self.vault_manager.directories['in_progress']
                    )
                    if claimed_path is not None:
                        logger.info(f"Claimed task: {task_file.name}")
                        self.process_task(claimed_path)
                    else:
                        logger.info(f"Task already claimed: {task_file.name}")

                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Orchestrator interrupted by user")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in orchestrator: {e}", exc_info=True)
                time.sleep(self.retry_delay)

    def _recover_stuck_tasks(self):
        """Move tasks stuck in In_Progress back to Needs_Action for reprocessing."""
        in_progress_dir = self.vault_manager.directories['in_progress']
        needs_action_dir = self.vault_manager.directories['needs_action']
        recovered = 0

        if not in_progress_dir.exists():
            return

        # In_Progress may contain agent sub-dirs (e.g. In_Progress/orchestrator/)
        for item in in_progress_dir.iterdir():
            task_files = [item] if item.is_file() else list(item.glob('*.md')) if item.is_dir() else []
            for task_file in task_files:
                if task_file.suffix != '.md':
                    continue
                dest = needs_action_dir / task_file.name
                try:
                    task_file.rename(dest)
                    recovered += 1
                    logger.info(f"Recovered stuck task → Needs_Action: {task_file.name}")
                except Exception as e:
                    logger.error(f"Failed to recover {task_file.name}: {e}")

        if recovered:
            logger.info(f"Startup recovery: moved {recovered} stuck task(s) back to Needs_Action")
            self.vault_manager.log_activity(
                "Startup recovery", {"recovered_tasks": recovered}
            )

    def process_task(self, task_file: Path):
        """Process a task by invoking the process-needs-action skill.

        The skill handles everything:
        - Calls task-planner if no plan exists
        - Executes plan steps
        - Enforces HITL for outbound actions
        - Moves files between folders
        - Logs all actions
        """
        try:
            vault_path = self.vault_manager.vault_path
            task_content = self.vault_manager.read_file(task_file)

            # Simple, clean prompt that invokes the skill
            prompt = f"""Process this task using the /process-needs-action skill.

Task File: {task_file}
Vault Path: {vault_path}

Task Content:
{task_content}

Instructions:
1. If no plan exists, call /task-planner to create one
2. Execute the plan step by step
3. For any outbound action (email, payment, etc), write to Pending_Approval/ and STOP
4. When complete, move task to Done/ and output: <promise>TASK_COMPLETE</promise>

Use the MCP servers (gmail, odoo) as needed for execution.
"""

            self.vault_manager.log_activity(
                "Orchestrator invoked process-needs-action skill",
                {"task_file": str(task_file)}
            )

            # Let the skill do all the work
            result = self.ralph_manager.execute_with_persistence(prompt, task_file)

            logger.info(f"Task processing completed: {task_file.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing task {task_file}: {e}", exc_info=True)

            # Move to Failed folder
            failed_dir = self.vault_manager.vault_path / "Failed"
            failed_dir.mkdir(exist_ok=True)
            try:
                if task_file.exists():
                    dest = failed_dir / task_file.name
                    task_file.rename(dest)
                    logger.info(f"Moved failed task to Failed/: {task_file.name}")
            except Exception as move_error:
                logger.error(f"Could not move failed task: {move_error}")

    def stop(self):
        """Stop the orchestrator."""
        self.running = False
        logger.info("Orchestrator stopped")
