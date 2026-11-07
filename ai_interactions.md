# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

The work happened in two sessions with **Claude Code**. Exact prompt texts are not reproduced here. Each section summarizes what the prompt asked for and what was actually done.

### Session 1: full implementation

**What task did you give the agent?**

One "master prompt" was given to **Claude Code** (an AI coding agent running in VS Code), on the branch `feature/pawpal-complete-implementation`. It asked the agent to take the starter repository through all six phases autonomously:

0. Inspect the repo.
1. Design the system and draw the UML.
2. Build the core classes and a CLI demo.
3. Build the Streamlit UI on top of the backend.
4. Implement the scheduling algorithms: sorting, filtering, recurrence, conflicts, and optional priority.
5. Write and run the tests.
6. Write the final UML, README, reflection and this log.

Key constraints in the prompt: preserve useful starter code, use beginner-friendly Python, don't claim anything works unless it was verified, don't commit/push/merge, and don't invent the user's personal experiences.

**What did the agent do?**

1. **Inspected** the repo: README, reflection, this file, `requirements.txt`, `.gitignore`, `app.py`, `diagrams/uml.mmd`, the git branch and status, and the packages installed in `.venv`. Findings: there was no backend and no tests yet. `app.py` was a UI-only starter, and `uml.mmd` was a placeholder.
2. **Created `pawpal_system.py`** with `Task`, `Pet` and `Owner` (dataclasses with validation in `__post_init__`) and a `Scheduler` that reads tasks only through `Owner.get_all_tasks()`.
3. **Created the UML diagrams:** `diagrams/uml_draft.mmd` (initial design) and `diagrams/uml_final.mmd` (matches the code). It copied the final diagram into `diagrams/uml.mmd`, because the repo's latest commit had renamed the template to that name for grading.
4. **Created `main.py`**: a CLI demo with 2 pets and 6 tasks added out of order. It shows sorting, priority sorting, filters, conflicts (cross-pet and same-pet), daily and weekly recurrence, and the duplicate-completion guard.
5. **Created `tests/test_pawpal.py`** (79 tests) and `pytest.ini` (so plain `pytest` can import the module).
6. **Rewrote `app.py`** as a working app. It keeps the starter's title, page config, scenario expander and owner/pet/species/task/priority inputs, and adds `st.session_state`, forms, tabs, metrics, tables, conflict warnings, recurrence messages and JSON save/load.
7. **Verified:** ran `python -m pytest -v`, `python main.py`, `py_compile`, pyflakes, flake8 and ruff. Started `streamlit run app.py` headless and checked the health endpoint and the page. Drove the UI with Streamlit's `AppTest`: adding a pet, the empty-name error, conflicting tasks, completing a recurring task, sample data, filters, and save/load.
8. **Updated docs:** `README.md`, `reflection.md` (technical parts only; personal parts were left for me and completed later with my own answers), this file, and `.gitignore` (adds `pawpal_data.json`, `.env`, `.ruff_cache/`, `*.pyc`, `*.log`, `.streamlit/secrets.toml`).

**Decisions the agent made (and why)**

- **No task duration field.** Conflict detection checks exact date/time matches. This is documented in the README and the code, as the prompt allowed.
- **Completed tasks are ignored by conflict detection by default**, because a finished task no longer competes for the owner's time. `include_completed=True` is available.
- **Recurrence is created at completion time** (one next occurrence), not as a pre-generated calendar. There are two duplicate guards: `mark_complete()` returns False on a second call, and `Pet.has_task_at()` checks before adding.
- **Conflicts are warnings, not errors**, so adding an overlapping task is allowed but flagged.
- **Pet names are unique per owner** (case-insensitive), because tasks reference their pet by name.
- **Optional extras** (priority sorting and JSON save/load) were added only after the required features and tests passed.

**AI output that was corrected or rejected during the work**

- A persistence test first compared `sorted(d.items() for ...)`. Sorting `dict_items` views compares them like sets, so that assertion was unreliable. It was replaced with a direct list-of-dicts comparison plus a count check.
- The first UI draft keyed the "Pending task" dropdown by label text. Duplicate labels would collapse, so it was changed to key by `task_id` with a `format_func`.
- The first UI draft called a "flash then rerun" helper twice in a row and relied on `st.rerun()` stopping the script. It was rewritten with explicit `if/else` / `try/except/else` so the control flow is obvious to a reader. Conflict checking after adding a task also moved from string-matching warning text to calling `detect_conflicts()` on tasks in the same time slot.
- Ruff's style suggestions were applied (`Optional[X]` → `X | None`, sorted imports, one merged `if`). They didn't change behaviour, and the tests were re-run afterwards.
- **Test-strength check:** two deliberate bugs were planted in a scratch copy (wrong weekly interval; `mark_complete()` no longer idempotent). The suite failed in both cases, so the tests do detect regressions.

### Session 2: fix, review and submission preparation

**Task given:** A second prompt reported that opening the app in the browser showed *"This site can't be reached — localhost refused to connect — ERR_CONNECTION_REFUSED"*. It asked the agent to find and fix the cause, re-verify all six phases, improve the UI where useful, finish the README, reflection and this log, and prepare the git commands. It also set an explicit rule: an import or AppTest is *not* proof that the HTTP server works.

**What the agent did:**

1. **Diagnosed the connection error.** Checked the git state, the port (`lsof -iTCP:8501` showed nothing listening), running processes (no Streamlit process), and the venv's `streamlit` launcher. The project path contains a space; the launcher handles this correctly. Streamlit credentials already existed, so no first-run email prompt blocks startup. **Root cause:** no server was running. In session 1, the server check used a temporary server on port 8599 that was stopped right after the check, so nothing ever listened on 8501.
2. **Fixed and verified it.** Started `python -m streamlit run app.py --server.port 8501 --server.headless true` as a long-running process. `curl` showed `/_stcore/health` → `ok` and `/` → HTTP 200 on both `localhost` and `127.0.0.1`. Then opened `http://localhost:8501` in Chrome: the app rendered, *Load sample data* showed 2 pets and 6 tasks, and *Mark complete* on a daily task changed the metrics to 7 tasks / 1 completed (next occurrence created).
3. **UI improvements, after seeing the real browser:**
   - Success and warning messages now also appear as a **toast**, because the banner at the top of the page was out of view while working inside a tab.
   - The Pets tab table was replaced with **pet cards**.
   - The Dashboard gained a **"Next up"** banner.
   - A real screenshot was saved to `assets/dashboard.jpg`.
4. **UML check.** Compared every public method in `pawpal_system.py` with `uml_final.mmd` and added notes: it is the authoritative diagram, `uml.mmd` is an identical copy, and `scheduled_at` is a property.
5. **Docs.** README: macOS commands, a "localhost refused to connect" troubleshooting section, the screenshot, and updated verification notes. Reflection: technical sections completed, with opinion drafts left for my review (finalized in session 3 with my own answers). This log: added this session.
6. **Re-ran everything:** pytest, the CLI, compile checks, linters, AppTest and the live HTTP check.

**What did you have to verify or fix manually?**

**Performed by me (the student):**

- Checked the project directory with `pwd`.
- Confirmed I was on the correct feature branch with `git branch --show-current`.
- Checked the git working-tree status with `git status -sb`.
- Activated the project's virtual environment.
- Tried opening the Streamlit app in my browser, got `ERR_CONNECTION_REFUSED`, and reported it instead of accepting the earlier "Streamlit verified" claim. In the session 2 prompt I required stricter proof: a real HTTP server, not only AppTest.

**Performed by Claude (not by me):**

- The final automated test runs (`python -m pytest -v`, 79 passed).
- Running the CLI demo (`python main.py`).
- Compile and lint checks (pyflakes, flake8, ruff).
- Starting the Streamlit server, checking it over HTTP, and the browser walkthrough after the fix.

I did not personally re-run those final checks or independently re-test the app after the server fix.

### Session 3: completing the reflection

Claude Code asked me the remaining personal reflection questions: design agreement, scheduling priorities, tradeoffs, my own checks, the lead architect role, confidence, what went well, improvements, key takeaway, and what I learned. It then updated `reflection.md` and this file using only my answers. No code was changed in this session.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

*Optional extension: **not performed.** Only one model (Claude Code) was used, and no second prompt or model was run on the same task. The table is left empty on purpose rather than filled with invented output. Fill it in only if you run a real comparison yourself.*

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
