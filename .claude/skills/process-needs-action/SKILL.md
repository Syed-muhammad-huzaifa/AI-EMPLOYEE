---
name: process-needs-action
description: "PRIMARY ORCHESTRATOR AGENT (SYSTEM BRAIN). This is the ONLY orchestrator and executor. Owns the system control loop: scans task states, routes tasks, invokes planning, executes steps, enforces HITL, calls MCP tools, logs everything, and moves tasks across folders. This is a finite state machine + control loop, NOT a free-form chat agent."
version: 2.0.0
skill_type: orchestrator
tier: core
architecture_role: executor
dependencies:
  required:
    - task-planner (creates all plans)
  optional:
    - simple-invoice-maker
    - email-responder
    - create-approval-request
---

# process-needs-action - PRIMARY ORCHESTRATOR

## ⚠️ CRITICAL: ROLE DEFINITION

**This skill is a FINITE STATE MACHINE + CONTROL LOOP.**

### STRICT RESPONSIBILITIES

`process-needs-action` **MUST**:
- ✅ Continuously scan folders (Inbox, Needs_Action, Pending_Approval, Failed)
- ✅ Route tasks based on state
- ✅ **Call `task-planner` for ALL planning** (NEVER create own plans)
- ✅ Execute plan steps strictly in order
- ✅ Call MCP servers for external actions
- ✅ Enforce Human-in-the-Loop (HITL) for outbound communication
- ✅ Log every action to `/Logs/`
- ✅ Move tasks across folders based on state transitions

`process-needs-action` **MUST NEVER**:
- ❌ Create its own plans (always delegate to `task-planner`)
- ❌ Skip HITL approval for external communications
- ❌ Execute steps out of order
- ❌ Make decisions without consulting vault state

---

## Folder State Machine

```
TASK LIFECYCLE (Folder-Based States):

/Inbox/ 
  ↓ (new task detected)
/Needs_Action/
  ↓ (no plan exists → call task-planner)
/Plans/{task_id}.md created
  ↓ (plan ready)
/In_Progress/ 
  ↓ (executing steps)
/Pending_Approval/ (if HITL required)
  ↓ (human moves to /Approved/)
/Approved/
  ↓ (continue execution)
/Done/ (task complete)
  ↓ (archive)
/Done/YYYY-MM/

ERROR PATHS:
/Failed/ (if execution fails after retries)
/Rejected/ (if human rejects approval)
```

---

## Decision Table

| Condition | Action |
|-----------|--------|
| Task has NO plan | Call `task-planner` skill |
| Task has plan + in Needs_Action | Move to In_Progress, execute next step |
| Task in Pending_Approval | Wait for human (poll folder) |
| Task in Approved | Continue execution from where stopped |
| Task in Rejected | Update plan OR escalate to human |
| Task Failed | Retry (max 3x) OR escalate |
| Task complete (all steps ✓) | Archive to /Done/ + log |

---

## PLANNING INVOCATION (CRITICAL RULE)

### Rule: ALWAYS Delegate Planning

```python
# CORRECT - Always call task-planner
if not plan_exists(task):
    plan = call_skill('task-planner', {
        'task_file': task_file,
        'task_content': task.content,
        'vault_state': get_vault_state()
    })
    save_plan(plan)

# WRONG - Never create plans yourself
if not plan_exists(task):
    plan = create_plan_internally()  # ❌ VIOLATION
```

### When to Call task-planner

1. **New task arrives** in /Needs_Action with no associated plan
2. **Plan needs update** (rejection, scope change)
3. **Complex multi-step workflow** detected

### What to Pass to task-planner

```yaml
context:
  task_file: /Needs_Action/EMAIL_xyz.md
  task_type: email | whatsapp | transaction | file_drop
  task_content: full task markdown
  source: gmail_watcher | whatsapp_watcher | human
  vault_state:
    handbook_rules: /Company_Handbook.md content
    client_context: /Clients/{client}.md (if exists)
    business_goals: /Business_Goals.md
    recent_tasks: last 5 similar tasks
```

---

## EXECUTION BEHAVIOR

### Step-by-Step Execution

Once a plan exists:

```python
def execute_plan(task, plan):
    """Execute plan steps strictly in order"""
    
    # 1. Move task to In_Progress
    move_task(task, '/In_Progress/')
    
    # 2. Execute each step sequentially
    for step in plan.steps:
        if step.completed:
            continue  # Skip already done steps
        
        # 3. Execute based on step type
        if step.type == 'mcp_action':
            result = execute_mcp_step(step)
        elif step.type == 'skill_call':
            result = call_skill(step.skill_name, step.context)
        elif step.type == 'file_operation':
            result = execute_file_operation(step)
        
        # 4. Check if HITL required
        if step.requires_approval and result.needs_approval:
            create_approval_request(task, step, result)
            update_task_status(task, 'awaiting_approval')
            return  # STOP - wait for human
        
        # 5. Mark step complete
        mark_step_complete(plan, step.id)
        log_action(task, step, result)
    
    # 6. All steps done
    mark_task_complete(task)
    archive_task(task)
```

### MCP Server Usage

```python
# Email MCP
def draft_email(to, subject, body):
    return call_mcp('email', 'draft', {
        'to': to,
        'subject': subject,
        'body': body
    })

def send_email(draft_id):
    return call_mcp('email', 'send', {
        'draft_id': draft_id
    })

# Browser MCP
def navigate_and_fill(url, form_data):
    return call_mcp('browser', 'navigate_and_fill', {
        'url': url,
        'form_data': form_data
    })

# Social Media MCP
def post_linkedin(content):
    return call_mcp('linkedin', 'post', {
        'content': content
    })
```

---

## HUMAN-IN-THE-LOOP (MANDATORY)

### Rule: All Outbound Communication Requires Approval

**HITL Required For**:
- Sending emails (drafts OK, sending requires approval)
- Posting on social media
- Making payments
- Creating contracts/commitments
- Sharing confidential information
- Deleting data

### HITL Workflow

```python
def enforce_hitl(action_type, action_data):
    """
    1. Draft content using MCP
    2. Save draft to Pending_Approval
    3. STOP execution
    4. Wait for human approval
    5. Only after approval: execute + log
    """
    
    # Step 1: Draft
    if action_type == 'email':
        draft = draft_email(**action_data)
    
    # Step 2: Create approval file
    approval_file = create_approval_request({
        'action': action_type,
        'data': action_data,
        'draft': draft,
        'task_id': current_task.id
    })
    
    # Step 3: STOP
    update_task_status(current_task, 'awaiting_approval')
    save_state()  # Persist where we stopped
    
    # Execution continues ONLY when human approves
    # (detected by file move to /Approved/)
```

### Approval File Format (CRITICAL - EXACT FORMAT REQUIRED)

**IMPORTANT**: The approval file MUST be machine-readable YAML + Markdown.
The ApprovedEmailSender parses this file automatically.

#### Email with PDF Attachment (e.g., Invoice)

⚠️ **DO NOT embed base64 PDF content in the approval file.**
The system automatically fetches and attaches the PDF from Odoo using the `invoice_id`.
Just include the `invoice_id` — the ApprovedEmailSender handles the rest.

```markdown
---
action: send_email
task_id: invoice_task_123
to: customer@example.com
subject: Invoice #INV-2026-001 - Consulting Services
invoice_id: 70
---

Dear Customer,

Please find attached your invoice for services rendered.

Invoice Details:
- Invoice Number: INV-2026-001
- Amount: $250.00
- Due Date: March 17, 2026

Thank you for your business!

Best regards,
Your Company
```

**Key Requirements**:
1. `action: send_email` (exact string, not "send_email_with_invoice")
2. `to:` field is REQUIRED
3. `subject:` field is REQUIRED for emails
4. `invoice_id:` include the numeric Odoo invoice ID — system auto-attaches the PDF
5. Email body goes AFTER the `---` closing the YAML frontmatter
6. `thread_id` and `in_reply_to` are optional (for email replies)
7. **NEVER** include `content_base64` — that's too large and breaks the system

#### Email without Attachment

```markdown
---
action: send_email
task_id: reply_task_456
to: customer@example.com
subject: Re: Your inquiry
thread_id: 18a1b2c3d4e5f6g7
in_reply_to: <message-id@mail.gmail.com>
---

Dear Customer,

Thank you for reaching out. Here's the information you requested...

Best regards,
Your Company
```
action: send_email | post_social | make_payment
task_id: EMAIL_client_001
created: 2026-01-07T10:00:00Z
expires: 2026-01-08T10:00:00Z
risk_level: low | medium | high
---

## Action Summary
Send invoice email to client@example.com

## Draft Content
Subject: Invoice January 2026
Body: Please find attached...
Attachment: /Invoices/INV-2026-001.pdf

## To Approve
Move this file to /Approved/

## To Reject
Move this file to /Rejected/
```

---

## LOGGING & AUDIT (MANDATORY)

### Log Every Action

```python
def log_action(task, step, result):
    """Write to /Logs/YYYY-MM-DD.json"""
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'task_id': task.id,
        'task_type': task.type,
        'step_id': step.id,
        'step_name': step.name,
        'tool_used': step.tool or step.mcp_server,
        'result': result.status,
        'approval_required': step.requires_approval,
        'approved_by': result.approved_by if result.approved else None,
        'error': result.error if result.failed else None
    }
    
    log_file = f"/Vault/Logs/{datetime.now().strftime('%Y-%m-%d')}.json"
    append_to_log(log_file, log_entry)
```

### Log Structure

```json
{
  "timestamp": "2026-01-07T10:30:00Z",
  "task_id": "EMAIL_client_invoice_001",
  "task_type": "email",
  "step_id": "step_002",
  "step_name": "Send invoice email",
  "tool_used": "email_mcp",
  "result": "success",
  "approval_required": true,
  "approved_by": "human",
  "error": null
}
```

---

## CONTROL LOOP (Ralph Wiggum Pattern)

### Continuous Operation

```python
def control_loop():
    """
    Main execution loop - runs continuously
    This implements the Ralph Wiggum pattern
    """
    
    while system_active:
        try:
            # 1. Scan vault folders
            pending_tasks = scan_folders([
                '/Inbox/',
                '/Needs_Action/',
                '/Pending_Approval/',
                '/Approved/',
                '/Failed/'
            ])
            
            # 2. Process each task by state
            for task in pending_tasks:
                process_task_by_state(task)
            
            # 3. Check for stale tasks
            handle_stale_tasks()
            
            # 4. Update dashboard
            update_dashboard()
            
            # 5. Sleep interval
            time.sleep(CHECK_INTERVAL)  # Default: 30 seconds
        
        except Exception as e:
            log_error(e)
            alert_human_if_critical(e)
```

### Task Processing by State

```python
def process_task_by_state(task):
    """Route task based on current folder/state"""
    
    state = get_task_state(task)
    
    if state == 'inbox':
        # New arrival - move to Needs_Action
        move_task(task, '/Needs_Action/')
    
    elif state == 'needs_action':
        # Check if plan exists
        if not plan_exists(task):
            # NO PLAN - call task-planner
            call_task_planner(task)
        else:
            # Has plan - start execution
            move_task(task, '/In_Progress/')
            execute_next_step(task)
    
    elif state == 'in_progress':
        # Continue execution
        execute_next_step(task)
    
    elif state == 'pending_approval':
        # Wait for human (check if moved to /Approved/)
        check_approval_status(task)
    
    elif state == 'approved':
        # Human approved - continue execution
        move_task(task, '/In_Progress/')
        execute_next_step(task)
    
    elif state == 'rejected':
        # Human rejected - update plan or escalate
        handle_rejection(task)
    
    elif state == 'failed':
        # Retry or escalate
        handle_failure(task)
    
    elif state == 'done':
        # Archive
        archive_task(task)
```

---

## IMPLEMENTATION

### Main Entry Point

```python
#!/usr/bin/env python3
"""
process-needs-action skill
PRIMARY ORCHESTRATOR - System control loop
"""

from pathlib import Path
import json
import time
from datetime import datetime

VAULT_PATH = Path('/Vault')
CHECK_INTERVAL = 30  # seconds

def main():
    """Entry point - start control loop"""
    
    print("🤖 Starting process-needs-action orchestrator...")
    print(f"📁 Vault: {VAULT_PATH}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL}s")
    
    # Initialize
    ensure_folder_structure()
    load_state()
    
    # Run control loop
    try:
        control_loop()
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        save_state()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        save_state()
        raise

def ensure_folder_structure():
    """Create required folders if missing"""
    folders = [
        'Inbox',
        'Needs_Action',
        'In_Progress',
        'Plans',
        'Pending_Approval',
        'Approved',
        'Rejected',
        'Failed',
        'Done',
        'Logs'
    ]
    
    for folder in folders:
        (VAULT_PATH / folder).mkdir(exist_ok=True)

def scan_folders(folder_list):
    """Scan folders and return all task files"""
    tasks = []
    
    for folder in folder_list:
        folder_path = VAULT_PATH / folder.strip('/')
        for file in folder_path.glob('*.md'):
            task = load_task(file)
            tasks.append(task)
    
    return tasks

def load_task(file_path):
    """Load task metadata and content"""
    content = file_path.read_text()
    
    # Parse frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        metadata = yaml.safe_load(parts[1])
        body = parts[2].strip()
    else:
        metadata = {}
        body = content
    
    return {
        'file': file_path,
        'id': file_path.stem,
        'folder': file_path.parent.name,
        'metadata': metadata,
        'content': body
    }

def call_task_planner(task):
    """
    CRITICAL: Call task-planner skill for planning
    NEVER create plans internally
    """
    
    print(f"📋 Calling task-planner for {task['id']}...")
    
    context = {
        'task_file': str(task['file']),
        'task_type': task['metadata'].get('type'),
        'task_content': task['content'],
        'vault_state': gather_vault_context()
    }
    
    # Call task-planner skill via Claude Code
    # In production: this would be actual skill invocation
    plan = invoke_skill('task-planner', context)
    
    # Save plan
    plan_file = VAULT_PATH / 'Plans' / f"PLAN_{task['id']}.md"
    plan_file.write_text(plan)
    
    # Update task metadata
    update_task_metadata(task, {
        'plan_file': str(plan_file),
        'status': 'planned'
    })
    
    print(f"✅ Plan created: {plan_file}")

def execute_next_step(task):
    """Execute next uncompleted step from plan"""
    
    plan = load_plan(task)
    
    for step in plan['steps']:
        if not step.get('completed'):
            print(f"▶️ Executing: {step['name']}")
            
            # Execute based on step type
            if step['type'] == 'mcp_call':
                result = call_mcp(step['mcp_server'], step['action'], step['params'])
            elif step['type'] == 'skill_call':
                result = invoke_skill(step['skill'], step['context'])
            
            # Check HITL
            if step.get('requires_approval'):
                create_approval_request(task, step, result)
                return  # Stop and wait
            
            # Mark complete
            mark_step_complete(plan, step['id'])
            log_action(task, step, result)
            
            # Continue to next step
            break
    
    # Check if all steps done
    if all(s.get('completed') for s in plan['steps']):
        mark_task_complete(task)

def create_approval_request(task, step, result):
    """Create approval file and move task to Pending_Approval"""
    
    approval_content = f"""---
action: {step['action']}
task_id: {task['id']}
step_id: {step['id']}
created: {datetime.now().isoformat()}
expires: {(datetime.now() + timedelta(hours=24)).isoformat()}
risk_level: {step.get('risk_level', 'medium')}
---

## Action Summary
{step['description']}

## Preview
{result.get('preview', 'N/A')}

## To Approve
Move this file to /Approved/

## To Reject
Move this file to /Rejected/
"""
    
    approval_file = VAULT_PATH / 'Pending_Approval' / f"{step['action']}_{task['id']}.md"
    approval_file.write_text(approval_content)
    
    # Move task
    move_task(task, '/Pending_Approval/')
    update_task_metadata(task, {
        'status': 'awaiting_approval',
        'approval_file': str(approval_file)
    })

def check_approval_status(task):
    """Check if human has approved/rejected"""
    
    approval_file = task['metadata'].get('approval_file')
    if not approval_file:
        return
    
    approval_path = Path(approval_file)
    
    # Check if moved to Approved
    approved_path = VAULT_PATH / 'Approved' / approval_path.name
    if approved_path.exists():
        print(f"✅ Approved: {task['id']}")
        move_task(task, '/In_Progress/')
        update_task_metadata(task, {'status': 'in_progress'})
        return 'approved'
    
    # Check if moved to Rejected
    rejected_path = VAULT_PATH / 'Rejected' / approval_path.name
    if rejected_path.exists():
        print(f"❌ Rejected: {task['id']}")
        handle_rejection(task)
        return 'rejected'
    
    # Still pending
    return 'pending'

if __name__ == '__main__':
    main()
```

---

## ERROR HANDLING

### Retry Logic

```python
MAX_RETRIES = 3

def execute_with_retry(func, *args, **kwargs):
    """Retry transient failures"""
    
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except TransientError as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt  # Exponential backoff
                print(f"⚠️ Retry {attempt+1}/{MAX_RETRIES} in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise
```

### Failure Handling

```python
def handle_failure(task):
    """Move to /Failed/ and alert human"""
    
    move_task(task, '/Failed/')
    update_task_metadata(task, {
        'status': 'failed',
        'failed_at': datetime.now().isoformat(),
        'retry_count': task['metadata'].get('retry_count', 0) + 1
    })
    
    alert_human({
        'severity': 'high',
        'task_id': task['id'],
        'message': f"Task failed after {MAX_RETRIES} attempts"
    })
```

---

## DASHBOARD UPDATES

```python
def update_dashboard():
    """Update Dashboard.md with current stats"""
    
    stats = {
        'last_updated': datetime.now().isoformat(),
        'tasks_pending': count_tasks('/Needs_Action'),
        'tasks_in_progress': count_tasks('/In_Progress'),
        'tasks_awaiting_approval': count_tasks('/Pending_Approval'),
        'tasks_completed_today': count_tasks_today('/Done')
    }
    
    dashboard_path = VAULT_PATH / 'Dashboard.md'
    update_dashboard_stats(dashboard_path, stats)
```

---

## ARCHITECTURE COMPLIANCE

### Separation of Concerns

```
✅ process-needs-action: EXECUTES
✅ task-planner: PLANS
✅ MCP Servers: ACT
✅ Human: APPROVES

❌ process-needs-action does NOT plan
❌ task-planner does NOT execute
❌ MCP servers do NOT decide
```

### State Machine Enforcement

- **Folders = States**: Each folder represents a task state
- **Files = Tasks**: Moving files between folders = state transitions
- **Plans = Blueprints**: Separate from execution
- **Logs = Audit Trail**: Immutable record of all actions

---

## HARD CONSTRAINTS (NEVER VIOLATE)

1. ✅ **ONLY** `process-needs-action` controls flow
2. ✅ **ONLY** `task-planner` creates plans
3. ✅ Folder structure = state machine (do not bypass)
4. ✅ NO auto-sending without approval (HITL mandatory)
5. ✅ ALL actions logged (no exceptions)
6. ✅ Planner NEVER executes
7. ✅ Orchestrator NEVER plans

---

## VERSION HISTORY

- **v2.0.0** (2026-01-07): CORE SKILL architecture
  - Strict separation: orchestrator vs planner
  - Mandatory HITL for all outbound communication
  - Ralph Wiggum control loop
  - State machine folder architecture

---

End of SKILL.md