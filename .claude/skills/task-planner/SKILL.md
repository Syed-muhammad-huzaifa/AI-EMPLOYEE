---
name: task-planner
description: "DETERMINISTIC PLANNING ENGINE (THINKING MODULE). Pure planning agent that ONLY THINKS. NEVER executes, NEVER calls MCP, NEVER sends messages. Creates structured, step-by-step execution plans that process-needs-action will execute. This is the brain that strategizes, NOT the hands that act."
version: 2.0.0
skill_type: planner
tier: core
architecture_role: strategist
dependencies:
  none: true
called_by:
  - process-needs-action
---

# task-planner - DETERMINISTIC PLANNING ENGINE

## ⚠️ CRITICAL: ROLE DEFINITION

**This skill is a PURE PLANNING AGENT.**

### STRICT RESPONSIBILITIES

`task-planner` **ONLY THINKS**:
- ✅ Analyze task requirements
- ✅ Create detailed, structured execution plans
- ✅ Define step-by-step workflows
- ✅ Identify HITL (Human-in-the-Loop) checkpoints
- ✅ Specify which MCP servers/skills to use
- ✅ Define success criteria and failure handling
- ✅ Save plans to `/Plans/{task_id}.md`

`task-planner` **MUST NEVER**:
- ❌ Call MCP servers
- ❌ Send emails or messages
- ❌ Post on social media
- ❌ Move tasks between folders
- ❌ Trigger execution of any kind
- ❌ Interact with external systems

---

## INPUT SPECIFICATION

### What task-planner Receives

```yaml
context:
  # Core task information
  task_file: /Needs_Action/EMAIL_client_invoice_001.md
  task_type: email | whatsapp | transaction | file_drop | manual
  task_content: |
    Full markdown content of the task including:
    - Frontmatter metadata
    - Body content
    - Any embedded instructions
  
  # Source information
  source: gmail_watcher | whatsapp_watcher | human | system
  
  # Business context (from vault)
  vault_state:
    handbook_rules: |
      Content from /Company_Handbook.md
      - Pricing rules
      - Communication templates
      - Approval requirements
    
    client_context: |
      Content from /Clients/{client}.md (if applicable)
      - Client history
      - Payment terms
      - Special instructions
    
    business_goals: |
      Content from /Business_Goals.md
      - Revenue targets
      - Key metrics
      - Active projects
    
    recent_similar_tasks: [
      # Last 5 similar tasks for pattern learning
      {task_id, outcome, duration}
    ]
```

---

## OUTPUT SPECIFICATION (REQUIRED FORMAT)

### Plan File Structure

Every plan **MUST** follow this exact structure:

```markdown
---
task_id: EMAIL_client_invoice_001
task_type: email
created: 2026-01-07T10:30:00Z
created_by: task-planner
status: ready_to_execute
priority: high
estimated_duration: 15 minutes
requires_approval: true
---

# Task Plan — {task_id}

## Objective
[Clear, one-sentence description of what this task aims to accomplish]

Example: "Generate and send January 2026 invoice to Client A via email"

## Task Classification
[Categorize the task]

- **Type**: email | whatsapp | social | accounting | ops | support
- **Category**: invoice_request | question | payment | lead | support
- **Urgency**: low | medium | high | critical
- **Client**: Known | New | Internal

## Preconditions
[What must be true/available before execution can start]

Example:
- [ ] Client email address available
- [ ] January work hours logged
- [ ] Pricing rates confirmed in handbook
- [ ] Invoice template accessible

## Execution Steps

### Step 1: [Action Name]
- **Type**: mcp_call | skill_call | file_operation | wait
- **Tool/Skill**: email_mcp | simple-invoice-maker | etc.
- **Action**: Draft invoice content
- **Parameters**:
  ```yaml
  client: Client A
  period: January 2026
  rate_source: /Company_Handbook.md
  ```
- **Output**: /Temp/invoice_draft.md
- **Expected Duration**: 3 minutes
- **HITL Required**: No

### Step 2: [Action Name]
- **Type**: skill_call
- **Skill**: simple-invoice-maker
- **Action**: Generate formatted invoice
- **Input**: /Temp/invoice_draft.md
- **Output**: /Invoices/INV-2026-001.pdf
- **Expected Duration**: 2 minutes
- **HITL Required**: No

### Step 3: [Action Name]
- **Type**: mcp_call
- **MCP Server**: email
- **Action**: draft_email
- **Parameters**:
  ```yaml
  to: client_a@example.com
  subject: "Invoice January 2026 - $1,500"
  body: [use template: invoice_delivery]
  attachment: /Invoices/INV-2026-001.pdf
  ```
- **Output**: /Temp/email_draft.json
- **Expected Duration**: 2 minutes
- **HITL Required**: No

### Step 4: [Action Name] ⚠️ HUMAN APPROVAL REQUIRED
- **Type**: hitl_checkpoint
- **Action**: Request approval to send email
- **Approval Type**: email_send
- **Risk Level**: low
- **Create**: /Pending_Approval/SEND_email_invoice_client_a.md
- **Wait For**: Human to move file to /Approved/
- **Expected Wait**: 1-4 hours
- **HITL Required**: YES ✓

### Step 5: [Action Name]
- **Type**: mcp_call
- **MCP Server**: email
- **Action**: send_email
- **Input**: /Temp/email_draft.json (from Step 3)
- **Precondition**: Approval received from Step 4
- **Expected Duration**: 30 seconds
- **HITL Required**: No (already approved in Step 4)

### Step 6: [Action Name]
- **Type**: file_operation
- **Action**: Log transaction
- **Target**: /Logs/2026-01-07.json
- **Data**:
  ```json
  {
    "action": "invoice_sent",
    "client": "Client A",
    "amount": 1500,
    "invoice_number": "INV-2026-001"
  }
  ```
- **Expected Duration**: 10 seconds
- **HITL Required**: No

### Step 7: [Action Name]
- **Type**: file_operation
- **Action**: Update dashboard
- **Target**: /Dashboard.md
- **Update**: Recent Activity section
- **Expected Duration**: 10 seconds
- **HITL Required**: No

## HITL Checkpoints
[Summary of all steps requiring human approval]

1. **Step 4**: Approve email send
   - **Risk**: Low (known client, routine invoice)
   - **Timeout**: 24 hours
   - **Fallback**: Alert human if not approved

## Success Criteria
[How to know the task is complete]

- [x] Invoice generated with correct amount
- [x] Email drafted with professional tone
- [x] Human approved sending
- [x] Email sent successfully
- [x] Transaction logged
- [x] Dashboard updated
- [x] All files archived to /Done/

## Failure Handling

### Step 1-3 Failure (Draft/Generation)
- **Action**: Retry up to 3 times
- **If Still Fails**: Move to /Failed/, alert human with details

### Step 4 Timeout (Approval Not Received)
- **After 24 hours**: Send reminder to human
- **After 48 hours**: Mark as stale, move to manual queue

### Step 5 Failure (Email Send)
- **Action**: Do NOT retry automatically
- **Move to**: /Failed/
- **Alert**: Human with error details (MCP logs)
- **Reason**: Email might have partially sent

### Step 6-7 Failure (Logging)
- **Action**: Retry up to 3 times
- **If Fails**: Log error but don't fail entire task
- **Note**: These are cleanup steps, main task (email) succeeded

## Dependencies

### Files Required
- /Company_Handbook.md (rates, templates)
- /Clients/client_a.md (client details)
- /Invoices/ folder (writable)

### Skills Required
- simple-invoice-maker (optional but recommended)
- email-responder (for template)

### MCP Servers Required
- email_mcp (critical - cannot proceed without)

## Estimated Timeline

| Phase | Duration |
|-------|----------|
| Preparation (Steps 1-2) | 5 min |
| Draft (Step 3) | 2 min |
| Human Approval (Step 4) | 1-4 hours |
| Execution (Steps 5-7) | 1 min |
| **Total** | **~1-4 hours** |

## Risk Assessment

- **Overall Risk**: Low
- **Financial Impact**: None (invoice, not payment)
- **Reputation Impact**: Low (routine communication)
- **Reversibility**: No (email cannot be unsent)
- **Mitigation**: HITL approval before send

---

*Plan created by task-planner v2.0.0*
*Execution will be handled by process-needs-action*
```

---

## PLAN CREATION LOGIC

### Step-by-Step Planning Process

```python
def create_plan(task_context):
    """
    Main planning function
    NEVER executes - ONLY creates plan document
    """
    
    # 1. Analyze task
    analysis = analyze_task(task_context)
    
    # 2. Determine task type and category
    classification = classify_task(
        task_context['task_type'],
        task_context['task_content']
    )
    
    # 3. Load relevant context
    context = load_context(
        classification,
        task_context['vault_state']
    )
    
    # 4. Generate step-by-step plan
    steps = generate_steps(analysis, classification, context)
    
    # 5. Identify HITL checkpoints
    hitl_steps = identify_hitl_requirements(steps, classification)
    
    # 6. Define success criteria
    success_criteria = define_success(analysis, steps)
    
    # 7. Add failure handling
    failure_handlers = create_failure_handlers(steps)
    
    # 8. Format as markdown
    plan_markdown = format_plan({
        'task_id': task_context['task_file'].stem,
        'classification': classification,
        'steps': steps,
        'hitl_checkpoints': hitl_steps,
        'success_criteria': success_criteria,
        'failure_handling': failure_handlers,
        'context': context
    })
    
    # 9. Return plan (do NOT save - that's orchestrator's job)
    return plan_markdown
```

### Task Classification

```python
TASK_PATTERNS = {
    'invoice_request': {
        'keywords': ['invoice', 'bill', 'payment request'],
        'steps_template': 'invoice_generation_workflow',
        'hitl_required': True,
        'estimated_time': '15 minutes'
    },
    'question': {
        'keywords': ['question', 'how', 'what', 'when', '?'],
        'steps_template': 'simple_reply_workflow',
        'hitl_required': False,  # Simple questions can auto-reply
        'estimated_time': '5 minutes'
    },
    'payment_received': {
        'keywords': ['payment', 'received', 'deposit'],
        'steps_template': 'payment_tracking_workflow',
        'hitl_required': False,
        'estimated_time': '3 minutes'
    },
    'support_request': {
        'keywords': ['help', 'issue', 'problem', 'urgent'],
        'steps_template': 'support_handling_workflow',
        'hitl_required': True,
        'estimated_time': '20 minutes'
    },
    'lead_inquiry': {
        'keywords': ['interested', 'pricing', 'quote', 'services'],
        'steps_template': 'lead_qualification_workflow',
        'hitl_required': True,
        'estimated_time': '30 minutes'
    }
}

def classify_task(task_type, content):
    """Identify task category and select appropriate template"""
    
    content_lower = content.lower()
    
    for category, pattern in TASK_PATTERNS.items():
        if any(kw in content_lower for kw in pattern['keywords']):
            return {
                'category': category,
                'template': pattern['steps_template'],
                'hitl_required': pattern['hitl_required'],
                'estimated_time': pattern['estimated_time']
            }
    
    # Default to manual review
    return {
        'category': 'unknown',
        'template': 'manual_review_workflow',
        'hitl_required': True,
        'estimated_time': 'varies'
    }
```

---

## WORKFLOW TEMPLATES

### Invoice Generation Workflow

```python
def invoice_generation_workflow(context):
    """Standard workflow for invoice requests"""
    
    return [
        {
            'id': 'step_001',
            'name': 'Extract invoice details',
            'type': 'skill_call',
            'skill': 'invoice-data-extractor',
            'params': {
                'source': context['task_content'],
                'handbook': context['vault_state']['handbook_rules']
            },
            'hitl': False
        },
        {
            'id': 'step_002',
            'name': 'Generate invoice document',
            'type': 'skill_call',
            'skill': 'simple-invoice-maker',
            'params': 'from step_001 output',
            'hitl': False
        },
        {
            'id': 'step_003',
            'name': 'Draft delivery email',
            'type': 'mcp_call',
            'mcp_server': 'email',
            'action': 'draft',
            'hitl': False
        },
        {
            'id': 'step_004',
            'name': 'Request approval',
            'type': 'hitl_checkpoint',
            'action': 'send_email',
            'risk_level': 'low',
            'hitl': True  # MANDATORY STOP
        },
        {
            'id': 'step_005',
            'name': 'Send email',
            'type': 'mcp_call',
            'mcp_server': 'email',
            'action': 'send',
            'precondition': 'step_004 approved',
            'hitl': False
        },
        {
            'id': 'step_006',
            'name': 'Log transaction',
            'type': 'file_operation',
            'action': 'append_log',
            'hitl': False
        }
    ]
```

### Simple Reply Workflow

```python
def simple_reply_workflow(context):
    """For straightforward questions"""
    
    return [
        {
            'id': 'step_001',
            'name': 'Draft response',
            'type': 'skill_call',
            'skill': 'email-responder',
            'params': {
                'question': context['task_content'],
                'handbook': context['vault_state']['handbook_rules']
            },
            'hitl': False
        },
        {
            'id': 'step_002',
            'name': 'Review and send',
            'type': 'hitl_checkpoint',
            'action': 'send_email',
            'risk_level': 'low',
            'hitl': True
        },
        {
            'id': 'step_003',
            'name': 'Send reply',
            'type': 'mcp_call',
            'mcp_server': 'email',
            'action': 'send',
            'hitl': False
        }
    ]
```

---

## HITL CHECKPOINT IDENTIFICATION

### Rules for HITL Requirements

```python
def identify_hitl_requirements(steps, classification):
    """Determine which steps need human approval"""
    
    hitl_checkpoints = []
    
    for step in steps:
        # Mandatory HITL for outbound communication
        if step['type'] == 'mcp_call' and step['action'] in ['send', 'post', 'publish']:
            hitl_checkpoints.append({
                'step_id': step['id'],
                'reason': 'Outbound communication',
                'risk_level': 'medium',
                'required': True
            })
        
        # Mandatory HITL for financial actions
        if 'payment' in step['name'].lower() or 'invoice' in step['name'].lower():
            if step['action'] in ['send', 'process', 'transfer']:
                hitl_checkpoints.append({
                    'step_id': step['id'],
                    'reason': 'Financial transaction',
                    'risk_level': 'high',
                    'required': True
                })
        
        # Optional HITL for complex decisions
        if classification['category'] == 'unknown':
            hitl_checkpoints.append({
                'step_id': step['id'],
                'reason': 'Manual review needed',
                'risk_level': 'medium',
                'required': True
            })
    
    return hitl_checkpoints
```

---

## FAILURE HANDLING STRATEGIES

```python
def create_failure_handlers(steps):
    """Define what to do if each step fails"""
    
    handlers = {}
    
    for step in steps:
        if step['type'] == 'mcp_call':
            if step['action'] == 'send':
                # Never auto-retry sends
                handlers[step['id']] = {
                    'retry': False,
                    'action': 'alert_human',
                    'move_to': '/Failed/',
                    'reason': 'Email might have partially sent'
                }
            else:
                # Draft/read operations can retry
                handlers[step['id']] = {
                    'retry': True,
                    'max_attempts': 3,
                    'backoff': 'exponential'
                }
        
        elif step['type'] == 'skill_call':
            # Skills can generally retry
            handlers[step['id']] = {
                'retry': True,
                'max_attempts': 3,
                'fallback': 'manual_queue'
            }
        
        elif step['type'] == 'hitl_checkpoint':
            # Timeouts for approval
            handlers[step['id']] = {
                'timeout': '24 hours',
                'reminder': '12 hours',
                'action_on_timeout': 'mark_stale'
            }
    
    return handlers
```

---

## EXAMPLE PLANS

### Example 1: Email Invoice Request

```markdown
---
task_id: EMAIL_client_invoice_001
task_type: email
created: 2026-01-07T10:30:00Z
status: ready_to_execute
priority: high
---

# Task Plan — EMAIL_client_invoice_001

## Objective
Generate and send January invoice to Client A

## Task Classification
- Type: email
- Category: invoice_request
- Urgency: high
- Client: Known

## Execution Steps

### Step 1: Gather invoice data
- Type: skill_call
- Skill: invoice-data-extractor
- HITL: No

### Step 2: Generate invoice PDF
- Type: skill_call
- Skill: simple-invoice-maker
- HITL: No

### Step 3: Draft email
- Type: mcp_call
- MCP: email
- Action: draft
- HITL: No

### Step 4: Request approval ⚠️
- Type: hitl_checkpoint
- Action: send_email
- Risk: low
- HITL: YES

### Step 5: Send email
- Type: mcp_call
- MCP: email
- Action: send
- Precondition: Step 4 approved
- HITL: No

### Step 6: Log and archive
- Type: file_operation
- HITL: No
```

### Example 2: WhatsApp Lead Inquiry

```markdown
---
task_id: WHATSAPP_lead_restaurant_002
task_type: whatsapp
created: 2026-01-07T11:00:00Z
status: ready_to_execute
priority: high
---

# Task Plan — WHATSAPP_lead_restaurant_002

## Objective
Qualify and respond to new lead inquiry about web design

## Task Classification
- Type: whatsapp
- Category: lead_inquiry
- Urgency: high (new business)
- Client: New

## Execution Steps

### Step 1: Extract lead info
- Type: skill_call
- Skill: lead-qualifier
- HITL: No

### Step 2: Check service fit
- Type: skill_call
- Skill: service-matcher
- HITL: No

### Step 3: Draft response
- Type: skill_call
- Skill: whatsapp-responder
- Template: lead_inquiry
- HITL: No

### Step 4: Review response ⚠️
- Type: hitl_checkpoint
- Action: send_whatsapp
- Risk: medium (first contact)
- HITL: YES

### Step 5: Send WhatsApp
- Type: mcp_call
- MCP: whatsapp
- Action: send
- HITL: No

### Step 6: Create lead record
- Type: file_operation
- Target: /Clients/lead_restaurant.md
- HITL: No
```

---

## STRICT RULES (NEVER VIOLATE)

### What task-planner MUST DO
1. ✅ Create detailed, structured plans
2. ✅ Save plans to `/Plans/{task_id}.md`
3. ✅ Identify all HITL checkpoints
4. ✅ Define clear success criteria
5. ✅ Specify failure handling for each step
6. ✅ Include estimated timelines
7. ✅ List all dependencies (files, skills, MCPs)

### What task-planner MUST NEVER DO
1. ❌ Execute any step (that's orchestrator's job)
2. ❌ Call MCP servers directly
3. ❌ Send emails, messages, or posts
4. ❌ Move tasks between folders
5. ❌ Trigger any external action
6. ❌ Make assumptions without context
7. ❌ Create plans without clear approval points

---

## INTEGRATION WITH ORCHESTRATOR

### How process-needs-action Calls task-planner

```python
# In process-needs-action:

def handle_new_task(task):
    if not plan_exists(task):
        # Call task-planner skill
        plan = invoke_skill('task-planner', {
            'task_file': task['file'],
            'task_type': task['type'],
            'task_content': task['content'],
            'vault_state': gather_vault_state()
        })
        
        # Save returned plan
        plan_file = f"/Plans/PLAN_{task['id']}.md"
        save_file(plan_file, plan)
        
        # Update task metadata
        update_task(task, {
            'plan_file': plan_file,
            'status': 'planned'
        })
```

### What task-planner Returns

```python
# task-planner returns a complete markdown plan:

plan_markdown = """---
task_id: {task_id}
created: {timestamp}
status: ready_to_execute
---

# Task Plan — {task_id}
...
[Complete plan content]
"""

return plan_markdown
```

---

## VERSION HISTORY

- **v2.0.0** (2026-01-07): CORE SKILL architecture
  - Pure planning agent (no execution)
  - Mandatory HITL identification
  - Structured plan format
  - Template-based workflows
  - Comprehensive failure handling

---

End of SKILL.md