# System Bugs vs Hackathon Requirements

## Critical Bugs Preventing Task Completion

### Bug #1: Completion Detection Broken
**File:** `src/ralph/loop_manager.py:147-170`

**Problem:**
- Checks folder `'done'` but actual folder is `'Done'` (case mismatch)
- Searches for promise marker in random files
- Never checks if the task file actually moved from In_Progress to Done

**Fix:** Check if task file moved to Done folder

### Bug #2: Skills Not Invoked in --print Mode
**File:** `src/ralph/loop_manager.py:72-85`

**Problem:**
- Claude called with `--print` (non-interactive mode)
- Orchestrator prompt tells Claude to "invoke skills"
- Skills don't work or aren't invoked in --print mode

**Fix:** Either:
- Option A: Simplify prompt to not require skills (Bronze tier)
- Option B: Test if skills work in --print mode
- Option C: Use interactive mode instead

### Bug #3: _is_task_complete_in_vault() Missing task_file Parameter
**File:** `src/ralph/loop_manager.py:147`

**Problem:**
- Function doesn't receive which task file to check
- Can't verify if THAT specific file moved to Done

**Fix:** Pass task_file parameter and check its location

### Bug #4: Prompt Too Complex for Bronze Tier
**File:** `src/orchestrator/controller.py:106-162`

**Problem:**
- Requires skills that may not work
- Too structured for simple tasks
- Doesn't match Bronze tier simplicity

**Fix:** Simplify to direct instructions without skills

## Recommended Fix Order

1. **First:** Fix completion detection (Bug #1 + #3)
2. **Second:** Simplify prompt (Bug #4)
3. **Third:** Test and iterate
4. **Later:** Add skills back for Silver/Gold tier

## Bronze Tier Status

✅ Obsidian vault with Dashboard.md and Company_Handbook.md
✅ Gmail Watcher working
✅ Filesystem Watcher working
✅ Claude Code reading/writing vault
✅ Folder structure correct
✅ PM2 process management
❌ Tasks not completing (bugs above)

**Once bugs fixed:** Bronze tier complete!
