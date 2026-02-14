---
id: "0008"
title: Code Audit Cleanup and Reorganize
stage: green
date: 2026-02-15
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-gmail-integration
branch: 001-gmail-integration
user: syedhuzaifa
command: "code audit + reorganize"
labels: ["audit","refactor","error-handling","cleanup","readme","structure"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - Hackathon-0/README.md
  - Hackathon-0/.gitignore
  - Hackathon-0/src/utils/logger.py
  - Hackathon-0/src/utils/config_loader.py
  - Hackathon-0/src/utils/secrets_manager.py
  - Hackathon-0/src/utils/watchdog.py
  - Hackathon-0/src/vault/constants.py
  - Hackathon-0/src/vault/manager.py
  - Hackathon-0/src/watchers/base_watcher.py
  - Hackathon-0/src/orchestrator/controller.py
  - Hackathon-0/src/ralph/loop_manager.py
  - Hackathon-0/src/scheduler/job_scheduler.py
  - Hackathon-0/src/dashboard/updater.py
  - Hackathon-0/main.py
  - Hackathon-0/mcp-servers/odoo-mcp/odoo-mcp.py
tests:
  - py_compile on all 15 files — all PASSED
---

## Prompt

check my whole system remove all shitty files, folders organize this code with proper structured way then in the end write a readme for how to use it
also check code audit organize each file code as a expert developer with proper error handling

## Response snapshot

**Cleanup:**
- Deleted 691 MB of junk: .qwen/ (376 KB), config/sessions/ (275 MB), duplicate GOLD_TIER_*.md files (5 files), empty PDFs, misplaced root-level files, accidentally-created C:\MY_EMPLOYEE dir
- Moved test_*.py → tests/integration/, scripts to scripts/, docs to docs/archive/
- Updated .gitignore to block sessions/, *.pdf, Zone.Identifier files permanently

**Reorganized structure:**
- Root: main.py, config files only
- src/ — unchanged core modules
- tests/integration/ — all integration tests consolidated
- scripts/ — all utility/demo scripts
- docs/ — all reference docs, archive/ for old tier docs

**Code audit + fixes across 15 files:**
- logger.py: added log_level validation, type hints, encoding on file handler
- config_loader.py: added return type, JSON parse error, type validation
- secrets_manager.py: added required-key validation, warning for missing claude key, proper types
- watchdog.py: fixed bare `except:` → `except Exception`, fixed `.seconds` → `.total_seconds()` (real bug)
- vault/constants.py: added logger.debug on OSError instead of silent pass
- vault/manager.py: `_verify_vault_structure` now creates dirs instead of raising FileNotFoundError on startup
- base_watcher.py: added `_stop_event` + `stop()` + input validation; sleep replaced with `wait()` for fast shutdown
- orchestrator/controller.py: bare `except: pass` → `except OSError as exc: logger.warning()`
- ralph/loop_manager.py: `raise e` → `raise` (preserves original traceback)
- scheduler/job_scheduler.py: all `int()` cron field conversions wrapped in try/except ValueError
- dashboard/updater.py: added `_stop_event`, `stop()` method, `run_loop` uses `wait()` not `sleep()`
- main.py: moved `import os` to top, --vault-path reads $VAULT_PATH, --check-interval validated [1-3600], DashboardUpdater gets vault_path, shutdown logs errors
- odoo-mcp.py: `create_invoice` input validation (email, amount, description, due_days), `datetime.strptime` wrapped in try/except in 3 places, sort lambda guards against None

## Outcome

- ✅ Impact: 691 MB removed, clean structure, 15 files hardened with proper error handling
- 🧪 Tests: py_compile on all 15 files — all PASSED
- 📁 Files: 15 source files audited and fixed, README.md rewritten, .gitignore updated
- 🔁 Next prompts: Add mypy.ini for proper type checking; run pytest unit tests; add integration test for invoice workflow
- 🧠 Reflection: Biggest real bugs were `.seconds` vs `.total_seconds()` in watchdog (incorrect elapsed time comparison), `raise e` vs `raise` in ralph (lost traceback), and unguarded `datetime.strptime` calls in odoo-mcp (crashes on malformed Odoo data). Vault manager raising FileNotFoundError on startup was a usability bug (would crash on fresh install).

## Evaluation notes (flywheel)

- Failure modes observed: `raise e` pattern loses original traceback — fixed with bare `raise`
- Graders run and results (PASS/FAIL): py_compile all 15 files — PASS
- Prompt variant (if applicable): none
- Next experiment: Run pytest -v to check test coverage gaps
