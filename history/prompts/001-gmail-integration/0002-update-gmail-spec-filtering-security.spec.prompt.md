---
id: 0002
title: update-gmail-spec-filtering-security
stage: spec
date: 2026-02-12
surface: agent
model: claude-sonnet-4-5
feature: 001-gmail-integration
branch: 001-gmail-integration
user: syedhuzaifa
command: continuation
labels: ["gmail", "email-filtering", "security", "credentials", "classification", "actionable-detection"]
links:
  spec: ../spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-gmail-integration/spec.md
  - specs/001-gmail-integration/checklists/requirements.md
tests:
  - N/A (specification phase)
---

## Prompt

update specs i added client id and client secret in .env file don expose in code also i wanna ask one questions with you sometime unnessary emails comes in like sponsored and other platform emails that i dont wanna make reply and just ignore these replies so first i like watcher first label it in email gmail is_actionatable or not then list to needs_action for further automation

## Response snapshot

Updated Gmail integration specification to address two critical requirements:

**1. Security Enhancement - Credential Management:**
- Added FR-019: System MUST load OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET) from .env file and NEVER expose credentials in code or logs
- Updated Security & Privacy Considerations section with explicit prohibition on credential exposure
- Emphasized .env file must be gitignored to prevent credential leakage to version control

**2. Intelligent Email Filtering:**
- Enhanced User Story 1 (P1) to "Email Detection with Intelligent Filtering"
- Added 6 acceptance scenarios covering:
  - Filtering multiple email types (client emails vs sponsored vs newsletters)
  - Platform notification detection (noreply@linkedin.com patterns)
  - Keyword-based filtering (unsubscribe, promotional, sponsored)
  - Known client domain detection from Company_Handbook.md
  - Duplicate prevention across watcher restarts
  - Initial authentication validation
- Added FR-017: Email classification rules based on sender domain patterns, subject keywords, and Company_Handbook.md
- Added FR-018: Gmail labeling system - apply "actionable" or "non-actionable" labels, only create action files for actionable emails
- Added 4 new edge cases:
  - Uncertain classification handling (defaults to actionable, logs for review)
  - Unknown sender handling (keyword + domain pattern filtering)
  - Missing Company_Handbook.md handling (continues with pattern filtering only)
  - Misclassification correction workflow (manual override + handbook updates)
- Added SC-009: 95% classification accuracy for known patterns
- Added SC-010: <2% false negative rate to ensure important emails aren't missed
- Updated Email Message entity to include classification and classification_reason attributes

**Specification Metrics After Update:**
- 19 functional requirements (was 16)
- 12 edge cases (was 8)
- 10 success criteria (was 8)
- 6 acceptance scenarios in User Story 1 (was 0)

**Validation:**
- Updated requirements checklist to reflect all enhancements
- All 14 checklist items remain PASSED
- Specification ready for `/sp.plan` phase

## Outcome

- ✅ Impact: Enhanced Gmail integration specification with intelligent email filtering to reduce noise from non-actionable emails (sponsored, newsletters, platform notifications) and strengthened security by mandating .env-based credential management
- 🧪 Tests: N/A (specification phase - acceptance scenarios defined for implementation testing)
- 📁 Files: Updated spec.md (added 3 FRs, 4 edge cases, 2 success criteria, 6 acceptance scenarios) and requirements.md checklist (validation passed)
- 🔁 Next prompts: `/sp.plan` to create implementation plan with email classification logic and credential loading architecture
- 🧠 Reflection: Specification now addresses critical user pain point (email noise) with measurable success criteria (95% accuracy, <2% false negatives) while ensuring credentials are never exposed in code. Classification system balances conservative approach (defaults to actionable when uncertain) with user control (Company_Handbook.md rules, manual overrides).

## Evaluation notes (flywheel)

- Failure modes observed: None - specification updates completed successfully with all validation checks passing
- Graders run and results (PASS/FAIL): All 14 checklist items PASSED (content quality, requirement completeness, feature readiness)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
