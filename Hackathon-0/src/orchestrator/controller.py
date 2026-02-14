"""Orchestrator controller for monitoring folders and triggering Claude."""

import time
import logging
from datetime import date
from pathlib import Path

from src.vault.manager import VaultManager
from src.utils.file_lock import claim_task
from src.utils.config_loader import load_vault_config
from src.ralph.loop_manager import RalphLoopManager


logger = logging.getLogger(__name__)


class OrchestratorController:
    """Controls the orchestration of tasks between folders."""

    def __init__(self, config_path: str = "config/vault_config.json"):
        self.config = load_vault_config(config_path)
        self.vault_manager = VaultManager()
        self.ralph_manager = RalphLoopManager()
        self.running = False
        self.max_retries = self.config.get('max_retries', 5)
        self.retry_delay = self.config.get('retry_delay', 5)

    def start_monitoring(self, check_interval: int = 10):
        """Start monitoring the needs_action folder."""
        self.running = True
        logger.info("Starting orchestrator controller...")

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
                logger.error(f"Error in orchestrator: {e}")
                time.sleep(self.retry_delay)

    def process_task(self, task_file: Path):
        """Process a task file by triggering Claude."""
        try:
            vault = self.vault_manager.vault_path
            task_id = task_file.stem

            task_content          = self.vault_manager.read_file(task_file)
            handbook_content      = self.vault_manager.read_company_handbook()
            dashboard_content     = self.vault_manager.read_dashboard()
            business_goals        = self.vault_manager.read_business_goals()
            client_context        = self._load_client_context(task_content)
            recent_similar_tasks  = self._load_recent_similar_tasks(task_id)
            plan_exists           = (vault / "Plans" / task_file.name).exists()

            claude_prompt = self._create_claude_prompt(
                task_content, handbook_content, dashboard_content,
                business_goals, client_context, recent_similar_tasks,
                task_file, plan_exists
            )

            self.vault_manager.log_activity(
                "Orchestrator triggered Claude for task",
                {"task_file": str(task_file), "plan_exists": plan_exists}
            )

            self.ralph_manager.execute_with_persistence(claude_prompt, task_file)

        except Exception as e:
            logger.error(f"Error processing task {task_file}: {e}")

    # ── Context helpers ────────────────────────────────────────────────────────

    def _load_client_context(self, task_content: str) -> str:
        """Try to find a matching client file in /Clients/ based on task content."""
        clients_dir = self.vault_manager.vault_path / "Clients"
        if not clients_dir.exists():
            return "No client records found."

        task_lower = task_content.lower()
        for client_file in clients_dir.glob("*.md"):
            # Match if the client name or file stem appears in the task
            if client_file.stem.lower() in task_lower:
                try:
                    return client_file.read_text(encoding="utf-8")
                except OSError as exc:
                    logger.warning(f"Could not read client file '{client_file}': {exc}")

        return "No matching client record found for this task."

    def _load_recent_similar_tasks(self, task_id: str) -> str:
        """Return summaries of the last 5 completed tasks from /Done/."""
        done_dir = self.vault_manager.vault_path / "Done"
        if not done_dir.exists():
            return "No completed tasks yet."

        done_files = sorted(
            done_dir.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:5]

        if not done_files:
            return "No completed tasks yet."

        summaries = []
        for f in done_files:
            summaries.append(f"- {f.name}")
        return "\n".join(summaries)

    # ── Prompt builder ─────────────────────────────────────────────────────────

    def _create_claude_prompt(
        self,
        task_content: str,
        handbook_content: str,
        dashboard_content: str,
        business_goals: str,
        client_context: str,
        recent_similar_tasks: str,
        task_file: Path,
        plan_exists: bool,
    ) -> str:
        """Create a structured prompt that uses task-planner and process-needs-action skills."""
        vault      = self.vault_manager.vault_path
        task_name  = task_file.name
        task_id    = task_file.stem
        plan_file  = vault / "Plans" / task_name
        done_file  = vault / "Done"  / task_name
        log_file   = vault / "Logs"  / f"{date.today()}.json"
        pending_approval_file = vault / "Pending_Approval" / task_name

        # If a plan already exists, skip re-planning and go straight to execution
        plan_section = ""
        if plan_exists:
            plan_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — PLAN ALREADY EXISTS (SKIP RE-PLANNING)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A plan already exists at: {plan_file}
READ IT. Do NOT rewrite it. Proceed directly to STEP 2.
"""
        else:
            plan_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — task-planner skill (PLAN ONLY — DO NOT EXECUTE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read .claude/skills/task-planner/SKILL.md and act as that skill.
Create a structured plan and WRITE IT to: {plan_file}

The plan MUST include (YAML front-matter + markdown body):
  task_id: {task_id}
  task_type: email | file_drop | question | invoice | support
  status: ready_to_execute
  requires_approval: true | false
  created_by: task-planner

Sections required: Objective, Task Classification, Preconditions,
Execution Steps (with id/name/type/HITL flag), HITL Checkpoints,
Success Criteria, Failure Handling.

task-planner MUST NOT execute anything — only create the plan file.
"""

        prompt = f"""You are an autonomous AI Employee agent with two skills:
- task-planner           → pure planner, NEVER executes anything
- process-needs-action   → executor, NEVER creates its own plans

Read skill definitions before proceeding:
  .claude/skills/task-planner/SKILL.md
  .claude/skills/process-needs-action/SKILL.md

Vault  : {vault}
Task   : {task_file}
Task ID: {task_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK CONTENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{task_content}
{plan_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — process-needs-action skill (EXECUTE THE PLAN)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read .claude/skills/process-needs-action/SKILL.md and act as that skill.
Read the plan at {plan_file} and execute every step in order.

══════════════════════════════════════════════
⛔ HITL RULE — ABSOLUTELY MANDATORY — NEVER BYPASS
══════════════════════════════════════════════
For ANY outbound action (email, payment, social post, message):

  1. Write the draft to PENDING_APPROVAL ONLY:
       {pending_approval_file}

  2. Use THE CORRECT frontmatter format for the channel:

     FOR EMAIL (action: send_email):
       ---
       action: send_email
       task_id: {task_id}
       to: <recipient email address>
       subject: <email subject line>
       thread_id: <Gmail thread_id from task metadata, or omit if new email>
       in_reply_to: <Gmail message_id from task metadata, or omit if new email>
       created: <ISO timestamp>
       expires: <ISO timestamp +24h>
       risk_level: low | medium | high
       ---

       ## Email Body
       <full professional email body here>

     FOR WHATSAPP (action: send_whatsapp) — when task came from WhatsApp:
       ---
       action: send_whatsapp
       task_id: {task_id}
       to: <whatsapp:+phonenumber from task metadata>
       created: <ISO timestamp>
       risk_level: low
       ---

       ## Message Body
       <short conversational WhatsApp reply here>

       ## To Approve
       Move this file to {vault}/Approved/

       ## To Reject
       Move this file to {vault}/Rejected/

  3. DO NOT write to /Approved/ yourself — EVER.
     /Approved/ is ONLY for humans to move files into.
     Writing to /Approved/ directly = security violation.

  4. After writing to /Pending_Approval/, move the task file to Done:
       mv "{task_file}" "{done_file}"
     Then output: <promise>TASK_COMPLETE</promise>
     The human will approve later — your job is done.

══════════════════════════════════════════════
LOGGING (mandatory for every step executed)
══════════════════════════════════════════════
Append one JSON entry per step to: {log_file}
Format:
  {{"timestamp":"<ISO>","task_id":"{task_id}","step_name":"<name>",
    "result":"success|pending_approval|failed","approval_required":<bool>}}

══════════════════════════════════════════════
COMPLETION (for non-HITL tasks)
══════════════════════════════════════════════
When ALL steps are done (no HITL) OR after writing Pending_Approval file:
  1. mv "{task_file}" "{done_file}"
  2. Append to {vault}/Dashboard.md:
       - [{date.today()}] {task_id}: <one-line summary>
  3. Output exactly: <promise>TASK_COMPLETE</promise>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUSINESS CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Company Handbook:
{handbook_content}

Dashboard:
{dashboard_content}

Business Goals:
{business_goals}

Client Context:
{client_context}

Recent Completed Tasks (for pattern learning):
{recent_similar_tasks}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return prompt

    def stop(self):
        """Stop the orchestrator."""
        self.running = False
        logger.info("Orchestrator stopped")
