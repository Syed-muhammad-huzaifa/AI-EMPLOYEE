"""Ralph Wiggum loop manager for task persistence."""

import os
import time
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Callable, Any, Optional

from src.vault.manager import VaultManager


logger = logging.getLogger(__name__)

# Repo root = the directory that contains .claude/skills/.
# loop_manager.py lives at:  <repo>/Hackathon-0/src/ralph/loop_manager.py
# So four .parent calls climb back to <repo>/.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _find_ai_cli() -> Optional[str]:
    """
    Find available AI CLI in order of preference: claude > gemini > qwen.
    Returns full path to the CLI executable, or None if none found.
    """
    # Try claude first
    claude_path = shutil.which('claude')
    if claude_path:
        logger.info(f"Found Claude CLI at: {claude_path}")
        return claude_path

    # Fallback to gemini
    gemini_path = shutil.which('gemini')
    if gemini_path:
        logger.info(f"Claude CLI not found, using Gemini CLI at: {gemini_path}")
        return gemini_path

    # Fallback to qwen
    qwen_path = shutil.which('qwen')
    if qwen_path:
        logger.info(f"Claude/Gemini CLI not found, using Qwen CLI at: {qwen_path}")
        return qwen_path

    logger.error("No AI CLI found (tried: claude, gemini, qwen)")
    return None


class RalphLoopManager:
    """Manages the Ralph Wiggum loop for task persistence."""

    def __init__(self, max_iterations: int = 10, check_interval: int = 5):
        self.max_iterations = max_iterations
        self.check_interval = check_interval
        self.vault_manager = VaultManager()

        # Detect available AI CLI on initialization
        self.ai_cli_path = _find_ai_cli()
        if not self.ai_cli_path:
            logger.warning("No AI CLI found - orchestrator will not function")
    
    def execute_with_persistence(self, prompt: str, task_file: Path = None) -> Any:
        """
        Execute AI CLI with the given prompt using the Ralph Wiggum loop pattern.

        Args:
            prompt: The prompt to send to AI CLI
            task_file: Optional task file to monitor for completion

        Returns:
            Result of AI CLI's processing
        """
        # Check if AI CLI is available
        if not self.ai_cli_path:
            raise RuntimeError("No AI CLI available (claude/gemini/qwen not found in PATH)")

        iteration = 0

        while iteration < self.max_iterations:
            try:
                logger.info(f"Ralph loop iteration {iteration + 1}")

                # Validate vault path before using it
                vault_path_obj = self.vault_manager.vault_path.resolve()
                if not vault_path_obj.exists():
                    raise ValueError(f"Vault path does not exist: {vault_path_obj}")
                if not vault_path_obj.is_absolute():
                    raise ValueError(f"Vault path must be absolute: {vault_path_obj}")

                vault_path = str(vault_path_obj)

                # Validate prompt input
                if not prompt or not prompt.strip():
                    raise ValueError("Prompt cannot be empty")
                if len(prompt) > 1_000_000:  # 1MB limit
                    raise ValueError(f"Prompt too large: {len(prompt)} bytes (max 1MB)")

                # Run AI CLI with:
                #   cwd = repo root  → loads .claude/skills/ (task-planner,
                #                       process-needs-action) automatically
                #   --add-dir vault  → grants file-tool access to the vault
                #   --print          → non-interactive single-response mode
                #   --dangerously-skip-permissions → no confirmation prompts
                #
                # CLAUDECODE and CLAUDE_CODE_ENTRYPOINT are cleared so the subprocess
                # is treated as a fresh top-level session and won't reject nested execution.
                clean_env = os.environ.copy()
                clean_env.pop('CLAUDECODE', None)
                clean_env.pop('CLAUDE_CODE_ENTRYPOINT', None)

                # Ensure PATH includes npm-global bin directory
                npm_global_bin = '/home/syedhuzaifa/.npm-global/bin'
                if 'PATH' in clean_env:
                    if npm_global_bin not in clean_env['PATH']:
                        clean_env['PATH'] = f"{npm_global_bin}:{clean_env['PATH']}"
                else:
                    clean_env['PATH'] = npm_global_bin

                # Build CLI-specific arguments
                cli_name = Path(self.ai_cli_path).name.lower()

                if 'claude' in cli_name:
                    # Claude CLI arguments
                    cmd = [
                        self.ai_cli_path, '--print',
                        '--dangerously-skip-permissions',
                        '--output-format', 'text',
                        '--add-dir', vault_path,
                    ]
                elif 'gemini' in cli_name:
                    # Gemini CLI arguments (non-interactive mode with -p)
                    cmd = [self.ai_cli_path, '-p', prompt]
                elif 'qwen' in cli_name:
                    # Qwen CLI arguments (assume similar to gemini)
                    cmd = [self.ai_cli_path, '-p', prompt]
                else:
                    # Unknown CLI - try claude-style as fallback
                    logger.warning(f"Unknown CLI type: {cli_name}, using Claude-style args")
                    cmd = [
                        self.ai_cli_path, '--print',
                        '--dangerously-skip-permissions',
                        '--output-format', 'text',
                        '--add-dir', vault_path,
                    ]

                # For Claude, prompt goes via stdin; for others it's in the command
                stdin_input = prompt if 'claude' in cli_name else None

                result = subprocess.run(
                    cmd,
                    input=stdin_input,
                    text=True,
                    capture_output=True,
                    cwd=str(_REPO_ROOT),
                    env=clean_env,
                    timeout=300,  # 5 minute timeout
                )

                if result.returncode == 0:
                    logger.info(f"AI CLI completed iteration {iteration + 1}")

                    # Check completion: either promise marker OR task file moved to Done
                    if self._is_task_complete(result.stdout) or self._is_task_complete_in_vault(task_file):
                        logger.info("Task completed successfully")
                        return result.stdout
                else:
                    error_msg = (
                        f"AI CLI failed on iteration {iteration + 1} | "
                        f"returncode={result.returncode} | "
                        f"stderr={result.stderr[:500] if result.stderr else '(empty)'} | "
                        f"stdout={result.stdout[:500] if result.stdout else '(empty)'}"
                    )
                    logger.error(error_msg)

                    # Check if this is a rate limit error from Claude
                    if "hit your limit" in result.stdout.lower() or "rate limit" in result.stdout.lower():
                        logger.warning("Claude CLI rate limit detected - attempting fallback to gemini/qwen")

                        # Try gemini fallback
                        gemini_path = shutil.which('gemini')
                        if gemini_path and gemini_path != self.ai_cli_path:
                            logger.info(f"Falling back to Gemini CLI at: {gemini_path}")
                            self.ai_cli_path = gemini_path
                            continue  # Retry with gemini

                        # Try qwen fallback
                        qwen_path = shutil.which('qwen')
                        if qwen_path and qwen_path != self.ai_cli_path:
                            logger.info(f"Falling back to Qwen CLI at: {qwen_path}")
                            self.ai_cli_path = qwen_path
                            continue  # Retry with qwen

                        logger.error("No fallback AI CLI available - all options exhausted")
                
                # If not complete, continue the loop
                logger.info(f"Task not yet complete, continuing loop ({iteration + 1}/{self.max_iterations})")
                
            except subprocess.TimeoutExpired as e:
                logger.error(f"Claude subprocess timed out on iteration {iteration + 1}")
                self.vault_manager.log_activity(
                    "Ralph loop timeout",
                    {"iteration": iteration + 1, "timeout": "300s", "prompt_length": len(prompt)}
                )
                if iteration >= self.max_iterations - 1:
                    raise Exception(f"Claude subprocess timed out after {iteration + 1} iterations") from e

            except subprocess.SubprocessError as e:
                logger.error(f"Error calling Claude in Ralph loop iteration {iteration + 1}: {e}")

                self.vault_manager.log_activity(
                    "Ralph loop Claude error",
                    {"iteration": iteration + 1, "error": str(e), "prompt_length": len(prompt)},
                )

                if iteration >= self.max_iterations - 1:
                    raise  # re-raise preserving original traceback

            except ValueError as e:
                # Input validation errors should fail immediately without retrying.
                logger.error(f"Input validation failed: {e}")
                raise
            
            iteration += 1
            time.sleep(self.check_interval)
        
        # If we reach here, max iterations were exceeded
        logger.error(f"Max iterations ({self.max_iterations}) exceeded in Ralph loop")
        
        # Log the failure
        self.vault_manager.log_activity(
            "Ralph loop failure",
            {"max_iterations": self.max_iterations, "prompt_length": len(prompt)}
        )
        
        # Move task to Failed folder if task_file is provided
        if task_file:
            failed_dir = self.vault_manager.vault_path / "Failed"
            failed_dir.mkdir(exist_ok=True)
            self.vault_manager.move_file(task_file, failed_dir)
        
        raise Exception(f"Ralph loop failed after {self.max_iterations} iterations")
    
    def _is_task_complete_in_vault(self, task_file: Path = None) -> bool:
        """
        Check if task is complete by verifying if task file moved to Done folder.

        Args:
            task_file: The task file to check (should be in In_Progress)

        Returns:
            Boolean indicating if the task is complete
        """
        if task_file is None:
            return False

        # Check if task file no longer exists in In_Progress (was moved)
        if not task_file.exists():
            # Check if it's now in Done folder
            done_file = self.vault_manager.vault_path / "Done" / task_file.name
            if done_file.exists():
                logger.info(f"Task file moved to Done: {task_file.name}")
                return True

        return False
    
    def _is_task_complete(self, result: Any) -> bool:
        """
        Check if the task is complete by looking for the completion marker in the result.
        
        Args:
            result: The result of Claude's processing
            
        Returns:
            Boolean indicating if the task is complete
        """
        # Check if result contains the completion marker
        if isinstance(result, str):
            return "<promise>TASK_COMPLETE</promise>" in result
        elif hasattr(result, '__str__'):
            return "<promise>TASK_COMPLETE</promise>" in str(result)
        elif isinstance(result, dict) and 'output' in result:
            return "<promise>TASK_COMPLETE</promise>" in result.get('output', '')
        
        return False
    
    def monitor_completion_marker(self, file_path: Path) -> bool:
        """
        Monitor a file for the completion marker.
        
        Args:
            file_path: Path to the file to monitor
            
        Returns:
            Boolean indicating if the completion marker was found
        """
        try:
            content = self.vault_manager.read_file(file_path)
            return "<promise>TASK_COMPLETE</promise>" in content
        except Exception as e:
            logger.error(f"Error reading file {file_path} for completion marker: {e}")
            return False