# PawPal+ Project Reflection

> **Note:** Technical sections describe the code and project history as they actually happened. Personal opinions and the description of my own checks come from my own answers, given while preparing this reflection with Claude Code.

## 1. System Design

**a. Initial design**

The initial UML ([diagrams/uml_draft.mmd](diagrams/uml_draft.mmd)) has four classes, each with one clear responsibility:

| Class | Responsibility in the draft |
|-------|-----------------------------|
| **Task** | One care activity: description, date, time, frequency, priority, completion status, and `mark_complete()`. |
| **Pet** | A pet's basic info (name, species, optional breed and age) and its own list of tasks, with `add_task()` and `get_tasks()`. |
| **Owner** | The person and their pets, with `add_pet()`, `get_pets()` and `get_all_tasks()`. The last method gathers tasks from every pet into one list. |
| **Scheduler** | The "brain": sorting, filtering, conflict detection, recurrence and schedule generation. It works on an `Owner`, not a single `Pet`, so multi-pet scheduling is built into the design from the start. |

Relationships: an Owner *owns* 0..* Pets (aggregation), a Pet *has* 0..* Tasks (composition), and the Scheduler *uses* the Owner to read tasks.

The key design rule was that **the Scheduler never stores its own copy of tasks**. It always asks `owner.get_all_tasks()`. This means there is only one source of truth: a pet or task added anywhere is immediately visible to every schedule, filter and conflict check.

**b. Design changes**

The final UML ([diagrams/uml_final.mmd](diagrams/uml_final.mmd), the authoritative version) keeps the same four classes. Several details changed during implementation:

1. **`Task` gained `pet_name` and `task_id`.** Once tasks from all pets are merged into one list, each task needs to say which pet it belongs to, so the schedule and conflict warnings can name the pet. The Streamlit app needs a stable id to mark exactly the right task complete. `Pet.add_task()` fills in `pet_name` automatically, so callers can't get it wrong.
2. **Recurrence was split between two classes.** The draft had a vague `handle_recurring(task)` on the Scheduler. In the final code, `Task.next_occurrence()` knows *how* to copy itself one day or one week later, while `Scheduler.complete_task()` decides *when* to do it and *which pet* receives the new task. This keeps `Task` independent of pets and owners.
3. **`mark_complete()` returns a `bool`**: `True` the first time, `False` if the task was already done. This one return value is what makes "completing twice never creates a duplicate" simple to implement and to test.
4. **Scheduler methods accept an optional `tasks` list**, so operations can be chained, e.g. `sort_by_time(filter_tasks(pet_name="Luna"))`, without the Scheduler storing data.
5. **Additions beyond the draft:** `sort_by_priority()`, `get_daily_schedule()`, `get_recurring_tasks()`, `get_summary()` (for the dashboard metrics), `find_task()`, and JSON persistence (`to_dict`/`from_dict`, `save_to_json`/`load_from_json`).

I agree with these changes. They make the system more organized and reliable, and each one fixed an issue that only became clear during implementation, for example needing a task id once the UI had to mark one specific task complete. A UML draft is a starting point, and details like ids and return values only show up once real code has to use the classes.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers these constraints:

1. **Date and time (primary).** `sort_by_time()` sorts by the tuple `(scheduled_date, scheduled_time)`. Sorting by time alone would put tomorrow at 06:00 before today at 23:00, and a test (`test_sort_by_time_uses_date_before_time`) guards against that.
2. **Priority (secondary, optional).** `sort_by_priority()` sorts by `(-priority_rank, date, time)`, so high-priority tasks come first and ties are broken chronologically. In the UI and CLI it is a separate view; the default stays chronological.
3. **Completion status.** Completed tasks stay in the history and are filterable, but conflict detection ignores them because they no longer need the owner's time.
4. **Pet.** Tasks can be filtered by pet (case-insensitive), but the default schedule combines all pets.

**Filtering** is one method, `filter_tasks(pet_name, completed, on_date)`, where every argument is optional and filters are applied one after another. The shortcuts `filter_by_pet/status/date()` exist for readability. This design lets the Streamlit Schedule tab combine three dropdowns with a single call.

I think time should come first. Feeding, medication and other pet care tasks often need to happen at specific times, so the default schedule is chronological. Priority is still useful for deciding what to handle first when several tasks are pending, so it's available as a separate view, but time stays the default.

**b. Recurrence implementation**

When `Scheduler.complete_task(task_id)` is called:

1. `task.mark_complete()` runs. If it returns `False` (the task was already done), the method stops and returns `None`.
2. For `daily` or `weekly` tasks, `task.next_occurrence()` creates a new pending task. The date is moved by `timedelta(days=1)` or `timedelta(weeks=1)`. The description, time, priority, frequency and pet are copied, and the new task gets a new `task_id`.
3. A second safety check, `Pet.has_task_at()`, refuses to add the new task if that pet already has one with the same description, date and time.
4. The original stays in the pet's list as completed history.

Using `timedelta` means month and year boundaries are handled correctly (a test checks Jan 31 → Feb 1).

**c. Tradeoffs**

- **Exact-time conflict detection instead of overlap detection.** Tasks have no duration field, so `detect_conflicts()` groups pending tasks in a dictionary keyed by their combined `datetime` and reports any group of two or more. This is one pass over the list (O(n)), easy to read and easy to test. The cost is that a 30-minute walk at 08:00 and a feeding at 08:15 are *not* flagged. Supporting overlaps would need a `duration_minutes` field and an interval comparison.
- **Warnings, not errors.** A conflicting task is still added, and the UI shows a yellow warning. Some overlaps are fine in real life, e.g. feeding two cats at the same moment.
- **One next occurrence at a time.** Recurrence creates only the next task when the current one is completed, instead of pre-generating weeks of tasks. The list stays short and duplicates are easy to prevent. The downside is that future occurrences aren't visible until the current one is done.

I think these tradeoffs are reasonable for a single owner managing a daily pet care routine. Keeping the system simple and predictable is important. The first improvement I would make is adding task durations, so the scheduler can detect overlapping activities and not just tasks at exactly the same time.

---

## 3. AI Collaboration

**a. How Claude Code helped**

The project was built with **Claude Code** (an AI coding agent in VS Code) across two working sessions, each driven by one detailed prompt that I wrote:

- **Session 1 ("master prompt"):** described all six CodePath phases, the required classes, algorithms and tests. It also set strict rules: inspect before changing, keep the code beginner-readable, don't claim anything works without verifying it, don't commit or push, and don't invent personal experiences. Claude Code inspected the starter repo and then wrote `pawpal_system.py`, `main.py`, `tests/test_pawpal.py`, the new `app.py`, the UML files and the documentation. It ran pytest, the CLI, linters and an automated UI test.
- **Session 2 ("final completion prompt"):** I reported that the browser showed *"localhost refused to connect — ERR_CONNECTION_REFUSED"* and asked for a fix plus a final review. Claude Code found that no Streamlit server was running (the earlier check had used a temporary server on another port, which was then stopped). It started the server on port 8501, verified it over HTTP and in Chrome, made small UI improvements, and finished the documentation.

The most helpful prompts were **specific and checkable**: exact method names (`get_all_tasks()`, `detect_conflicts()`), exact behaviours ("weekly tasks recur seven days later", "completing twice must not create duplicates"), and explicit verification rules ("a successful import or AppTest is not proof the HTTP server works").

**b. Suggestions accepted or modified**

Accepted as designed: the four-class structure, dataclasses with validation in `__post_init__`, the dictionary-based conflict check, and `timedelta`-based recurrence.

Modified during development, after checks run by the AI agent (recorded in [ai_interactions.md](ai_interactions.md)):

- A JSON test first compared `sorted(dict.items())` views, which compare like sets and could pass incorrectly. It was rewritten to compare lists of dictionaries directly.
- The "mark complete" dropdown was first keyed by its display text, so two identical tasks could collapse into one option. It was changed to use `task_id`.
- The success message after completing a task appeared only at the top of the page, out of sight while working inside a tab. A pop-up toast was added after this was seen in the real browser.
- To check the tests could catch real bugs, two bugs were planted on purpose in a scratch copy. The suite failed both times.

**What I checked myself.** I checked the project directory (`pwd`), confirmed I was on the correct feature branch (`git branch --show-current`), checked the working-tree status (`git status -sb`), and activated the project's virtual environment. I then tried opening the Streamlit app in my browser, got a "localhost refused to connect" error, and reported it so it could be investigated. That report started session 2, where I asked for stricter proof that the app works: a real HTTP server, not just an import.

To be clear about who did what: Claude ran the final automated tests, the CLI demo, the lint checks and the browser verification after fixing the server issue. I did not personally run those final checks or independently re-test the app after the fix.

**c. How separate phases and sessions helped**

Splitting the work into six phases (inspect → design → core code → UI → algorithms → tests and docs) meant each step had a clear "done" check. The backend was tested on its own before the UI was connected, so when the UI was built, any bug was clearly a UI bug. Running the final review as a separate session with a fresh, stricter prompt surfaced a problem (the server not running) that the first session's checks had missed.

**d. Acting as the lead architect**

I was responsible for defining the project requirements, deciding which features were important, and setting expectations for the final result. Claude implemented most of the code, but I guided the development, reviewed the reported results, found the browser connection problem, and asked for it to be fixed and verified. I learned that using AI does not remove my responsibility for the quality of the final project.

---

## 4. Testing and Verification

**a. What was tested**

`tests/test_pawpal.py` contains **79 tests, all passing** (`python -m pytest -v`), in seven groups:

- **Task:** creation, defaults, normalisation, `mark_complete()`, unique ids, readable `str()`.
- **Validation:** invalid times (`"25:00"`, `"8am"`, `None`…), dates, frequencies, priorities, empty descriptions/names, negative age, wrong types, duplicate pets/tasks, unknown task id.
- **Pet and Owner:** adding pets and tasks, multiple pets, case-insensitive lookup, removal, `get_all_tasks()` aggregation.
- **Scheduler:** reading tasks through the owner (including pets added later), chronological sorting where the date matters before the time, priority sorting, each filter alone and combined, empty schedules.
- **Recurrence:** daily +1 day, weekly +7 days, month boundary, history kept, no duplicate when completed twice, one-time tasks don't recur, chained occurrences.
- **Conflicts:** same pet, different pets, no false positives (different times or dates), empty list, 3-way conflict, completed tasks ignored.
- **Persistence:** JSON save/load round trip.

These matter because sorting, recurrence and conflicts are the "smart" parts of the app. A silent bug there, such as a duplicated recurring task or a missed conflict, would make the whole schedule untrustworthy. Tests use a fixed date (2026-01-15), so results don't depend on the day they are run.

Beyond the unit tests:

- `python main.py` runs cleanly.
- `py_compile`, pyflakes, flake8 and ruff report no issues.
- The real server was started with `python -m streamlit run app.py --server.port 8501`, checked over HTTP (health `ok`, page `200`), and used in Chrome.
- The UI was also driven with Streamlit's `AppTest`.

**b. Confidence**

I'm fairly confident, around 4 out of 5, in the backend logic, because the required behaviours are covered by 79 passing automated tests. I'm somewhat less confident about the UI, because its verification was limited compared with extended real-world use. I would want to use the app regularly before considering it fully production-ready.

**Edge cases to test next:** overlapping durations (if durations are added), daylight-saving time changes, very large task lists, loading a corrupted or hand-edited JSON file, renaming a pet that already has tasks, and more automated UI tests.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the separation between the backend and the interfaces. The same `Scheduler` logic is used by the CLI, the Streamlit app and the tests. I'm also proud of the recurring-task feature and its duplicate-protection logic.

**b. What I would improve**

I would improve the project by:

- Adding task durations to detect overlapping activities.
- Letting users edit and delete tasks in the UI (the backend already has `Pet.remove_task()`).
- Saving data automatically.
- Adding a weekly calendar view.

**c. Key takeaway**

My biggest takeaway is that passing tests does not automatically mean an application is ready for users. Even though the project had 79 passing tests, I couldn't open it in my browser at first because the Streamlit server wasn't running. AI can speed up development, but I still need to understand the requirements, check the results, and make sure the application works in practice.

I also learned how Streamlit session state keeps application data alive while users interact with the interface, and how pytest can test individual components and catch bugs before they reach the user. Together, these helped me understand how backend logic, frontend interactions and automated testing fit together in a real application.
