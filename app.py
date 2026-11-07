"""PawPal+ Streamlit app.

Run with:  streamlit run app.py

All data lives in real backend objects (Owner -> Pet -> Task) that are kept in
``st.session_state`` so they survive Streamlit reruns. Every button and form
calls methods from ``pawpal_system.py``; the UI never edits task data directly.
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path

import streamlit as st

from pawpal_system import (
    VALID_FREQUENCIES,
    VALID_PRIORITIES,
    Owner,
    Pet,
    Scheduler,
    Task,
)

DATA_FILE = Path(__file__).with_name("pawpal_data.json")
PRIORITY_ICON = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}
SPECIES_ICON = {"dog": "🐶", "cat": "🐱", "other": "🐾"}
TOAST_ICON = {"success": "✅", "info": "ℹ️", "warning": "⚠️", "error": "❌"}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def init_state() -> None:
    """Create the Owner once per browser session."""
    if "owner" not in st.session_state:
        st.session_state.owner = Owner(name="Jordan")
    if "flash" not in st.session_state:
        st.session_state.flash = None


def flash_and_rerun(kind: str, message: str) -> None:
    """Remember a message, then rerun so metrics and tables show the new data.

    ``kind`` is the name of a Streamlit message function: success, info, warning or error.
    """
    st.session_state.flash = (kind, message)
    st.rerun()


def show_flash() -> None:
    """Show (once) the message stored by ``flash_and_rerun``.

    The message appears as a banner at the top of the page and as a toast
    popup, so it is visible even while you are scrolled down inside a tab.
    """
    if st.session_state.flash:
        kind, message = st.session_state.flash
        getattr(st, kind)(message)
        st.toast(message, icon=TOAST_ICON.get(kind, "🐾"))
        st.session_state.flash = None


def load_sample_data(owner: Owner) -> None:
    """Replace the owner's pets with a small demo data set."""
    owner.pets.clear()
    today = date.today()
    mochi = owner.add_pet(Pet("Mochi", "dog", breed="Shiba Inu", age=3))
    luna = owner.add_pet(Pet("Luna", "cat", breed="Siamese", age=5))
    mochi.add_task(Task("Morning walk", today, "07:30", frequency="daily", priority="high"))
    mochi.add_task(Task("Breakfast", today, "08:00", frequency="daily", priority="medium"))
    mochi.add_task(Task("Evening walk", today, "18:30", frequency="daily", priority="high"))
    luna.add_task(Task("Flea medication", today, "08:00", frequency="weekly", priority="high"))
    luna.add_task(Task("Brush fur", today, "12:00", priority="low"))
    luna.add_task(Task("Vet check-up", today + timedelta(days=2), "10:00", priority="high"))


def tasks_to_rows(tasks: list[Task]) -> list[dict]:
    """Turn Task objects into simple rows for st.dataframe."""
    return [
        {
            "Date": t.scheduled_date.strftime("%a %b %d"),
            "Time": t.scheduled_time.strftime("%H:%M"),
            "Pet": t.pet_name,
            "Task": t.description,
            "Priority": PRIORITY_ICON[t.priority],
            "Repeats": "—" if t.frequency == "once" else f"🔁 {t.frequency}",
            "Status": "✅ Done" if t.completed else "⏳ Pending",
        }
        for t in tasks
    ]


def show_tasks(tasks: list[Task], empty_message: str = "No tasks to show.") -> None:
    """Display tasks as a table, or an info message when empty."""
    if tasks:
        st.dataframe(tasks_to_rows(tasks), hide_index=True)
    else:
        st.info(empty_message)


def show_conflicts(warnings: list[str]) -> None:
    """Display conflict warnings from Scheduler.detect_conflicts()."""
    if warnings:
        for warning in warnings:
            st.warning(f"⚠️ {warning}")
    else:
        st.success("No scheduling conflicts. 🎉")


def task_label(task: Task) -> str:
    """Readable label for a task in select boxes."""
    return (
        f"{task.scheduled_date:%b %d} {task.scheduled_time:%H:%M} · {task.pet_name} · "
        f"{task.description} ({task.frequency})"
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

init_state()
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

# ---- Sidebar: owner + data ------------------------------------------------
with st.sidebar:
    st.header("👤 Owner")
    new_name = st.text_input("Owner name", value=owner.name)
    if not new_name.strip():
        st.error("Owner name cannot be empty.")
    elif new_name.strip() != owner.name:
        owner.name = new_name.strip()

    st.divider()
    st.header("💾 Data")
    if st.button("Load sample data"):
        load_sample_data(owner)
        flash_and_rerun("success", "Sample pets and tasks loaded.")
    if st.button("Save to file"):
        owner.save_to_json(DATA_FILE)
        flash_and_rerun("success", f"Saved to {DATA_FILE.name}.")
    if st.button("Load from file", disabled=not DATA_FILE.exists()):
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except (ValueError, KeyError, TypeError) as err:
            st.error(f"Could not load file: {err}")
        else:
            flash_and_rerun("success", f"Loaded data from {DATA_FILE.name}.")
    if st.button("Clear all pets & tasks"):
        owner.pets.clear()
        flash_and_rerun("info", "All pets and tasks were removed.")

# ---- Header + metrics -----------------------------------------------------
st.title("🐾 PawPal+")
st.caption(f"Smart pet care management for **{owner.name}** — {date.today():%A, %B %d, %Y}")

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a busy pet owner stay consistent
with care tasks (walks, feeding, meds, grooming…) across **all** of their pets.
Add pets, schedule tasks with a date, time, frequency and priority, then use the
schedule view to sort, filter, spot conflicts and complete recurring tasks.
"""
    )

show_flash()

summary = scheduler.get_summary()
m1, m2, m3, m4 = st.columns(4)
m1.metric("🐾 Total pets", summary["pets"])
m2.metric("📋 Total tasks", summary["tasks"])
m3.metric("✅ Completed", summary["completed"])
m4.metric("⏳ Pending", summary["pending"])

tab_dash, tab_pets, tab_tasks, tab_schedule = st.tabs(["🏠 Dashboard", "🐶 Pets", "📝 Tasks", "📅 Schedule"])

# ---- Dashboard ------------------------------------------------------------
with tab_dash:
    if not owner.pets:
        st.info("Welcome! Add your first pet in the **Pets** tab, or click **Load sample data** in the sidebar.")

    # "Next up": the earliest pending task that is not in the past.
    now = datetime.now()
    next_up = [t for t in scheduler.sort_by_time(scheduler.filter_by_status(False)) if t.scheduled_at >= now]
    if next_up:
        nxt = next_up[0]
        st.info(
            f"**Next up:** {nxt.description} for **{nxt.pet_name}** — "
            f"{nxt.scheduled_date:%a %b %d} at {nxt.scheduled_time:%H:%M} ({PRIORITY_ICON[nxt.priority]} priority)"
        )

    st.subheader("📅 Today's schedule")
    today_tasks = scheduler.get_daily_schedule(date.today())
    show_tasks(today_tasks, "Nothing scheduled for today.")
    if today_tasks:
        done_today = sum(t.completed for t in today_tasks)
        st.progress(done_today / len(today_tasks), text=f"{done_today} of {len(today_tasks)} done today")

    st.subheader("⚠️ Conflicts today")
    show_conflicts(scheduler.detect_conflicts(today_tasks))

    st.subheader("🔜 Upcoming (next 7 days)")
    upcoming = [
        t
        for t in scheduler.sort_by_time(scheduler.filter_by_status(False))
        if date.today() < t.scheduled_date <= date.today() + timedelta(days=7)
    ]
    show_tasks(upcoming, "No upcoming pending tasks this week.")

# ---- Pets -----------------------------------------------------------------
with tab_pets:
    col_form, col_list = st.columns([1, 2])

    with col_form:
        st.subheader("Add a pet")
        with st.form("add_pet_form", clear_on_submit=True):
            pet_name = st.text_input("Pet name", placeholder="Mochi")
            species = st.selectbox("Species", ["dog", "cat", "other"])
            breed = st.text_input("Breed (optional)")
            age = st.number_input("Age in years (optional, 0 = unknown)", min_value=0, max_value=40, value=0)
            if st.form_submit_button("➕ Add pet", type="primary"):
                try:
                    owner.add_pet(Pet(pet_name, species, breed=breed, age=int(age) if age else None))
                except (ValueError, TypeError) as err:
                    st.error(str(err))
                else:
                    flash_and_rerun("success", f"Added {pet_name.strip()} the {species}!")

    with col_list:
        st.subheader("Your pets")
        if not owner.pets:
            st.info("No pets yet. Add one with the form.")
        else:
            # One bordered "card" per pet, three per row.
            pets = owner.get_pets()
            for row_start in range(0, len(pets), 3):
                for col, p in zip(st.columns(3), pets[row_start:row_start + 3]):
                    with col.container(border=True):
                        st.markdown(f"### {SPECIES_ICON.get(p.species, '🐾')} {p.name}")
                        details = [p.species]
                        if p.breed:
                            details.append(p.breed)
                        if p.age is not None:
                            details.append(f"{p.age} yr")
                        st.caption(" · ".join(details))
                        st.markdown(
                            f"⏳ **{len(p.get_pending_tasks())}** pending &nbsp; "
                            f"✅ **{len(p.get_completed_tasks())}** done"
                        )
            selected_name = st.selectbox("Select a pet to view its tasks", [p.name for p in owner.get_pets()])
            selected_pet = owner.get_pet(selected_name)
            show_tasks(scheduler.sort_by_time(selected_pet.get_tasks()), f"{selected_name} has no tasks yet.")
            if st.button(f"🗑️ Remove {selected_name}", key="remove_pet"):
                owner.remove_pet(selected_name)
                flash_and_rerun("info", f"Removed {selected_name} and their tasks.")

# ---- Tasks ----------------------------------------------------------------
with tab_tasks:
    col_form, col_done = st.columns([1, 2])

    with col_form:
        st.subheader("Add a task")
        if not owner.pets:
            st.info("Add a pet first.")
        else:
            with st.form("add_task_form", clear_on_submit=True):
                task_pet = st.selectbox("Pet", [p.name for p in owner.get_pets()])
                task_title = st.text_input("Task title", placeholder="Morning walk")
                c1, c2 = st.columns(2)
                task_date = c1.date_input("Date", value=date.today())
                task_time = c2.time_input("Time", value=time(8, 0), step=timedelta(minutes=5))
                c3, c4 = st.columns(2)
                frequency = c3.selectbox("Frequency", VALID_FREQUENCIES)
                priority = c4.selectbox("Priority", VALID_PRIORITIES, index=1)
                if st.form_submit_button("➕ Add task", type="primary"):
                    try:
                        task = Task(task_title, task_date, task_time, frequency=frequency, priority=priority)
                        owner.get_pet(task_pet).add_task(task)
                    except (ValueError, TypeError) as err:
                        st.error(str(err))
                    else:
                        # Ask the scheduler whether the new task clashes with anything.
                        same_slot = [t for t in scheduler.get_all_tasks() if t.scheduled_at == task.scheduled_at]
                        if scheduler.detect_conflicts(same_slot):
                            flash_and_rerun(
                                "warning",
                                f"Added '{task.description}' for {task_pet}, but another task is already "
                                f"scheduled on {task.scheduled_date:%b %d} at {task.scheduled_time:%H:%M}.",
                            )
                        else:
                            flash_and_rerun("success", f"Added '{task.description}' for {task_pet}.")

    with col_done:
        st.subheader("Mark a task complete")
        pending = scheduler.sort_by_time(scheduler.filter_by_status(False))
        if not pending:
            st.info("No pending tasks. 🎉")
        else:
            labels = {t.task_id: task_label(t) for t in pending}
            task_id = st.selectbox("Pending task", list(labels), format_func=labels.get)
            if st.button("✅ Mark complete", type="primary"):
                task = scheduler.find_task(task_id)
                next_task = scheduler.complete_task(task_id)
                if next_task:
                    flash_and_rerun(
                        "success",
                        f"Completed '{task.description}'. Next {task.frequency} occurrence scheduled for "
                        f"{next_task.scheduled_date:%a %b %d} at {next_task.scheduled_time:%H:%M}.",
                    )
                else:
                    flash_and_rerun("success", f"Completed '{task.description}'.")

    st.subheader("⏳ Pending tasks")
    show_tasks(pending, "No pending tasks.")
    st.subheader("✅ Completed tasks")
    show_tasks(scheduler.sort_by_time(scheduler.filter_by_status(True)), "No completed tasks yet.")

# ---- Schedule -------------------------------------------------------------
with tab_schedule:
    st.subheader("Combined schedule for all pets")
    f1, f2, f3, f4 = st.columns(4)
    pet_choice = f1.selectbox("Pet", ["All pets"] + [p.name for p in owner.get_pets()])
    status_choice = f2.selectbox("Status", ["All", "Pending", "Completed"])
    date_mode = f3.selectbox("Date", ["All dates", "Today", "Pick a date"])
    sort_choice = f4.selectbox("Sort by", ["Time", "Priority, then time"])

    chosen_date = None
    if date_mode == "Today":
        chosen_date = date.today()
    elif date_mode == "Pick a date":
        chosen_date = st.date_input("Show tasks on", value=date.today(), key="schedule_date")

    filtered = scheduler.filter_tasks(
        pet_name=None if pet_choice == "All pets" else pet_choice,
        completed={"All": None, "Pending": False, "Completed": True}[status_choice],
        on_date=chosen_date,
    )
    ordered = scheduler.sort_by_time(filtered) if sort_choice == "Time" else scheduler.sort_by_priority(filtered)
    st.caption(f"Showing {len(ordered)} of {summary['tasks']} tasks.")
    show_tasks(ordered, "No tasks match these filters.")

    st.subheader("⚠️ Conflict check")
    st.caption("Pending tasks scheduled at exactly the same date and time (tasks have no duration).")
    show_conflicts(scheduler.detect_conflicts())

    st.subheader("🔁 Recurring tasks")
    st.caption("Completing a daily task schedules it again 1 day later; weekly tasks move 7 days later.")
    show_tasks(scheduler.get_recurring_tasks(), "No recurring tasks yet.")
