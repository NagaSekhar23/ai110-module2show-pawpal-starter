"""PawPal+ command-line demo.

Run with:  python main.py

Builds an owner with two pets, adds tasks, and shows every scheduling
feature: the daily schedule, sorting, filtering, conflict detection and
recurring tasks.
"""

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task

WIDTH = 72


def heading(title: str) -> None:
    """Print a section heading."""
    print()
    print("=" * WIDTH)
    print(f"  {title}")
    print("=" * WIDTH)


def print_tasks(tasks: list[Task], empty_message: str = "  (no tasks)") -> None:
    """Print tasks as a neat aligned table."""
    if not tasks:
        print(empty_message)
        return
    print(f"  {'Date':<10}  {'Time':<5}  {'Pet':<8}  {'Task':<22}  {'Priority':<8}  {'Repeat':<6}  Status")
    print(f"  {'-' * 10}  {'-' * 5}  {'-' * 8}  {'-' * 22}  {'-' * 8}  {'-' * 6}  {'-' * 7}")
    for t in tasks:
        status = "Done" if t.completed else "Pending"
        print(
            f"  {t.scheduled_date:%Y-%m-%d}  {t.scheduled_time:%H:%M}  {t.pet_name:<8}  "
            f"{t.description[:22]:<22}  {t.priority:<8}  {t.frequency:<6}  {status}"
        )


def build_demo_owner(today: date) -> Owner:
    """Create the demo owner, two pets and their tasks.

    Tasks are added deliberately OUT of time order so sorting is visible.
    """
    owner = Owner(name="Jordan", email="jordan@example.com")
    mochi = owner.add_pet(Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3))
    luna = owner.add_pet(Pet(name="Luna", species="cat", breed="Siamese", age=5))

    mochi.add_task(Task("Evening walk", today, "18:30", frequency="daily", priority="high"))
    mochi.add_task(Task("Morning walk", today, "07:30", frequency="daily", priority="high"))
    mochi.add_task(Task("Breakfast", today, "08:00", frequency="daily", priority="medium"))
    luna.add_task(Task("Flea medication", today, "08:00", frequency="weekly", priority="high"))
    luna.add_task(Task("Brush fur", today, "12:00", frequency="once", priority="low"))
    luna.add_task(Task("Vet check-up", today + timedelta(days=2), "10:00", priority="high"))
    return owner


def main() -> None:
    today = date.today()
    owner = build_demo_owner(today)
    scheduler = Scheduler(owner)

    heading("PawPal+  |  Smart Pet Care Management")
    print(f"  Owner: {owner.name}")
    for pet in owner.get_pets():
        print(f"  - {pet.name}: {pet.species}, {pet.breed}, age {pet.age}  ({len(pet.tasks)} tasks)")

    summary = scheduler.get_summary()
    print(
        f"\n  The scheduler read {summary['tasks']} tasks across {summary['pets']} pets "
        "through Owner.get_all_tasks()."
    )

    heading("Tasks in the order they were added (unsorted)")
    print_tasks(scheduler.get_all_tasks())

    heading(f"Today's Schedule  ({today:%A, %B %d, %Y})  - sorted by time")
    print_tasks(scheduler.get_daily_schedule(today))

    heading("Today's Schedule - sorted by priority, then time")
    print_tasks(scheduler.get_daily_schedule(today, by_priority=True))

    heading("Filter: only Luna's tasks")
    print_tasks(scheduler.sort_by_time(scheduler.filter_by_pet("Luna")))

    heading(f"Filter: tasks on {today + timedelta(days=2):%Y-%m-%d}")
    print_tasks(scheduler.filter_by_date(today + timedelta(days=2)))

    heading("Conflict detection")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  WARNING: {warning}")
    else:
        print("  No conflicts found.")

    # Add a same-pet conflict to show that case too.
    owner.get_pet("Mochi").add_task(Task("Play fetch", today, "18:30", priority="low"))
    print("\n  Added 'Play fetch' for Mochi at 18:30 (same time as 'Evening walk')...")
    for warning in scheduler.detect_conflicts():
        print(f"  WARNING: {warning}")

    heading("Recurring tasks: completing tasks")
    morning_walk = next(t for t in scheduler.get_all_tasks() if t.description == "Morning walk")
    flea_med = next(t for t in scheduler.get_all_tasks() if t.description == "Flea medication")
    brush = next(t for t in scheduler.get_all_tasks() if t.description == "Brush fur")

    for task in (morning_walk, flea_med, brush):
        new_task = scheduler.complete_task(task.task_id)
        if new_task:
            print(
                f"  Completed '{task.description}' ({task.frequency}) -> next occurrence "
                f"created for {new_task.scheduled_date:%Y-%m-%d} at {new_task.scheduled_time:%H:%M}"
            )
        else:
            print(f"  Completed '{task.description}' ({task.frequency}) -> one-time task, nothing new created")

    again = scheduler.complete_task(morning_walk.task_id)
    print(
        f"  Completed 'Morning walk' a second time -> "
        f"{'DUPLICATE created (bug!)' if again else 'ignored, no duplicate created'}"
    )

    heading("All Mochi tasks after completion (history is kept)")
    print_tasks(scheduler.sort_by_time(scheduler.filter_by_pet("Mochi")))

    heading("Filter: completed tasks")
    print_tasks(scheduler.sort_by_time(scheduler.filter_by_status(True)))

    heading("Filter: pending tasks")
    print_tasks(scheduler.sort_by_time(scheduler.filter_by_status(False)))

    summary = scheduler.get_summary()
    heading("Summary")
    print(
        f"  Pets: {summary['pets']}   Tasks: {summary['tasks']}   "
        f"Completed: {summary['completed']}   Pending: {summary['pending']}"
    )
    print()


if __name__ == "__main__":
    main()
