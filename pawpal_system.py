"""PawPal+ backend: the core classes for pet care scheduling.

The module contains four classes:

* ``Task``      - one pet care activity (walk, feeding, medication, ...).
* ``Pet``       - a pet and the list of tasks that belong to it.
* ``Owner``     - a pet owner who can have many pets.
* ``Scheduler`` - the scheduling "brain". It always reads tasks through
  ``Owner.get_all_tasks()`` so every pet is included.

Only the Python standard library is used, so the module works the same way
from the CLI (``main.py``), the Streamlit app (``app.py``) and the tests.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_FREQUENCIES = ("once", "daily", "weekly")
VALID_PRIORITIES = ("low", "medium", "high")

# Higher number = more important. Used when sorting by priority.
PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}

# How far ahead the next occurrence of a recurring task is scheduled.
RECURRENCE_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


# ---------------------------------------------------------------------------
# Small parsing helpers (used for validation)
# ---------------------------------------------------------------------------


def parse_date(value: date | str) -> date:
    """Return a ``date`` from a ``date`` object or a ``"YYYY-MM-DD"`` string.

    Raises:
        ValueError: if the value cannot be understood as a date.
    """
    if isinstance(value, datetime):  # datetime is a subclass of date
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date {value!r}. Use the format YYYY-MM-DD.")


def parse_time(value: time | str) -> time:
    """Return a ``time`` from a ``time`` object or an ``"HH:MM"`` string (24-hour).

    Raises:
        ValueError: if the value cannot be understood as a time.
    """
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%H:%M").time()
        except ValueError:
            pass
    raise ValueError(f"Invalid time {value!r}. Use 24-hour HH:MM, e.g. 08:30.")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single pet care activity scheduled for a specific date and time.

    Attributes:
        description: What needs to be done, e.g. "Morning walk".
        scheduled_date: The day the task happens.
        scheduled_time: The time of day the task happens.
        frequency: "once", "daily" or "weekly".
        priority: "low", "medium" or "high".
        pet_name: Name of the pet this task belongs to (set by ``Pet.add_task``).
        completed: Whether the task has been done.
        task_id: Short unique id, generated automatically.
    """

    description: str
    scheduled_date: date
    scheduled_time: time
    frequency: str = "once"
    priority: str = "medium"
    pet_name: str = ""
    completed: bool = False
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __post_init__(self) -> None:
        """Validate and normalise every field right after creation."""
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Task description cannot be empty.")
        self.description = self.description.strip()

        self.scheduled_date = parse_date(self.scheduled_date)
        self.scheduled_time = parse_time(self.scheduled_time)

        if not isinstance(self.frequency, str) or self.frequency.lower().strip() not in VALID_FREQUENCIES:
            raise ValueError(
                f"Invalid frequency {self.frequency!r}. Choose one of: {', '.join(VALID_FREQUENCIES)}."
            )
        self.frequency = self.frequency.lower().strip()

        if not isinstance(self.priority, str) or self.priority.lower().strip() not in VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority {self.priority!r}. Choose one of: {', '.join(VALID_PRIORITIES)}."
            )
        self.priority = self.priority.lower().strip()

    # -- behaviour ---------------------------------------------------------

    def mark_complete(self) -> bool:
        """Mark the task as completed.

        Returns:
            True if the task changed from pending to completed,
            False if it was already completed (nothing changes).
        """
        if self.completed:
            return False
        self.completed = True
        return True

    def is_recurring(self) -> bool:
        """Return True for daily or weekly tasks."""
        return self.frequency in RECURRENCE_STEP

    def next_occurrence(self) -> Task | None:
        """Build the next occurrence of a recurring task.

        Daily tasks move forward 1 day, weekly tasks 7 days. The new task keeps
        the same description, time, frequency, priority and pet, starts as
        pending and receives a new ``task_id``.

        Returns:
            The new ``Task``, or ``None`` for one-time tasks.
        """
        if not self.is_recurring():
            return None
        return Task(
            description=self.description,
            scheduled_date=self.scheduled_date + RECURRENCE_STEP[self.frequency],
            scheduled_time=self.scheduled_time,
            frequency=self.frequency,
            priority=self.priority,
            pet_name=self.pet_name,
        )

    @property
    def scheduled_at(self) -> datetime:
        """The combined date and time, handy for sorting and comparisons."""
        return datetime.combine(self.scheduled_date, self.scheduled_time)

    def __str__(self) -> str:
        status = "done" if self.completed else "pending"
        return (
            f"{self.scheduled_date:%Y-%m-%d} {self.scheduled_time:%H:%M}  "
            f"{self.description} ({self.pet_name or 'no pet'}) "
            f"[{self.priority}, {self.frequency}, {status}]"
        )

    # -- persistence -------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert the task into JSON-friendly data."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "scheduled_date": self.scheduled_date.isoformat(),
            "scheduled_time": self.scheduled_time.strftime("%H:%M"),
            "frequency": self.frequency,
            "priority": self.priority,
            "pet_name": self.pet_name,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Rebuild a task from ``to_dict`` output."""
        return cls(**data)


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str
    breed: str = ""
    age: int | None = None
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the pet's basic information."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Pet name cannot be empty.")
        if not isinstance(self.species, str) or not self.species.strip():
            raise ValueError("Pet species cannot be empty.")
        self.name = self.name.strip()
        self.species = self.species.strip()
        self.breed = (self.breed or "").strip()
        if self.age is not None and (isinstance(self.age, bool) or not isinstance(self.age, int) or self.age < 0):
            raise ValueError("Pet age must be a whole number of 0 or more.")

    def add_task(self, task: Task) -> Task:
        """Attach a task to this pet and return it.

        The task's ``pet_name`` is set to this pet's name.

        Raises:
            TypeError: if ``task`` is not a ``Task``.
            ValueError: if the same task object/id was already added.
        """
        if not isinstance(task, Task):
            raise TypeError("Only Task objects can be added to a pet.")
        if any(existing.task_id == task.task_id for existing in self.tasks):
            raise ValueError(f"Task {task.task_id} is already assigned to {self.name}.")
        task.pet_name = self.name
        self.tasks.append(task)
        return task

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)

    def get_pending_tasks(self) -> list[Task]:
        """Return tasks that are not completed yet."""
        return [task for task in self.tasks if not task.completed]

    def get_completed_tasks(self) -> list[Task]:
        """Return tasks that are completed."""
        return [task for task in self.tasks if task.completed]

    def has_task_at(self, description: str, on_date: date, at_time: time) -> bool:
        """Return True if a task with this description/date/time already exists."""
        return any(
            t.description == description and t.scheduled_date == on_date and t.scheduled_time == at_time
            for t in self.tasks
        )

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by id. Returns True if something was removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        return len(self.tasks) < before

    def to_dict(self) -> dict:
        """Convert the pet (and its tasks) into JSON-friendly data."""
        return {
            "name": self.name,
            "species": self.species,
            "breed": self.breed,
            "age": self.age,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Rebuild a pet from ``to_dict`` output."""
        pet = cls(name=data["name"], species=data["species"], breed=data.get("breed", ""), age=data.get("age"))
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------


@dataclass
class Owner:
    """A pet owner who manages one or more pets."""

    name: str
    email: str = ""
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the owner's name."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Owner name cannot be empty.")
        self.name = self.name.strip()
        self.email = (self.email or "").strip()

    def add_pet(self, pet: Pet) -> Pet:
        """Add a pet. Pet names must be unique for this owner (case-insensitive).

        Raises:
            TypeError: if ``pet`` is not a ``Pet``.
            ValueError: if a pet with the same name already exists.
        """
        if not isinstance(pet, Pet):
            raise TypeError("Only Pet objects can be added to an owner.")
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"{self.name} already has a pet named {pet.name}.")
        self.pets.append(pet)
        return pet

    def get_pets(self) -> list[Pet]:
        """Return a copy of the owner's pet list."""
        return list(self.pets)

    def get_pet(self, name: str) -> Pet | None:
        """Find a pet by name (case-insensitive). Returns None if not found."""
        wanted = name.strip().lower()
        for pet in self.pets:
            if pet.name.lower() == wanted:
                return pet
        return None

    def remove_pet(self, name: str) -> bool:
        """Remove a pet (and its tasks) by name. Returns True if removed."""
        pet = self.get_pet(name)
        if pet is None:
            return False
        self.pets.remove(pet)
        return True

    def get_all_tasks(self) -> list[Task]:
        """Return every task from every pet in one list."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks

    # -- persistence (optional extension) ----------------------------------

    def to_dict(self) -> dict:
        """Convert the owner, pets and tasks into JSON-friendly data."""
        return {"name": self.name, "email": self.email, "pets": [p.to_dict() for p in self.pets]}

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Rebuild an owner from ``to_dict`` output."""
        owner = cls(name=data["name"], email=data.get("email", ""))
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, path: str | Path) -> None:
        """Save the owner and all pets/tasks to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_from_json(cls, path: str | Path) -> Owner:
        """Load an owner previously saved with ``save_to_json``."""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class Scheduler:
    """Organises tasks across all of an owner's pets.

    The scheduler never stores its own copy of the tasks. Every method reads
    the current tasks through ``Owner.get_all_tasks()``, so newly added pets
    and tasks are always included.

    Most methods accept an optional ``tasks`` list. When it is omitted, all of
    the owner's tasks are used. This lets methods be chained, e.g.
    ``scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi"))``.
    """

    def __init__(self, owner: Owner) -> None:
        if not isinstance(owner, Owner):
            raise TypeError("Scheduler needs an Owner.")
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks across every pet (delegates to the owner)."""
        return self.owner.get_all_tasks()

    def _tasks_or_all(self, tasks: list[Task] | None) -> list[Task]:
        return self.get_all_tasks() if tasks is None else list(tasks)

    # -- sorting -------------------------------------------------------------

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks ordered chronologically by date, then time."""
        return sorted(self._tasks_or_all(tasks), key=lambda t: (t.scheduled_date, t.scheduled_time))

    def sort_by_priority(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks ordered by priority (high first), then date and time."""
        return sorted(
            self._tasks_or_all(tasks),
            key=lambda t: (-PRIORITY_RANK[t.priority], t.scheduled_date, t.scheduled_time),
        )

    # -- filtering -----------------------------------------------------------

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
        on_date: date | str | None = None,
        tasks: list[Task] | None = None,
    ) -> list[Task]:
        """Return tasks matching every filter that is given.

        Args:
            pet_name: Keep only this pet's tasks (case-insensitive).
            completed: True = only completed, False = only pending, None = both.
            on_date: Keep only tasks scheduled on this date.
            tasks: Optional list to filter instead of all tasks.
        """
        result = self._tasks_or_all(tasks)
        if pet_name is not None:
            wanted = pet_name.strip().lower()
            result = [t for t in result if t.pet_name.lower() == wanted]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        if on_date is not None:
            day = parse_date(on_date)
            result = [t for t in result if t.scheduled_date == day]
        return result

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks for one pet."""
        return self.filter_tasks(pet_name=pet_name)

    def filter_by_status(self, completed: bool) -> list[Task]:
        """Return completed (True) or pending (False) tasks."""
        return self.filter_tasks(completed=completed)

    def filter_by_date(self, on_date: date | str) -> list[Task]:
        """Return tasks scheduled on a specific date."""
        return self.filter_tasks(on_date=on_date)

    def get_recurring_tasks(self) -> list[Task]:
        """Return daily and weekly tasks, sorted by time."""
        return self.sort_by_time([t for t in self.get_all_tasks() if t.is_recurring()])

    # -- schedule generation -------------------------------------------------

    def get_daily_schedule(self, on_date: date | str | None = None, by_priority: bool = False) -> list[Task]:
        """Return the schedule for one day (default: today).

        Args:
            on_date: The day to build the schedule for.
            by_priority: If True, order high-priority tasks first; otherwise
                order purely by time.
        """
        day = date.today() if on_date is None else parse_date(on_date)
        tasks = self.filter_tasks(on_date=day)
        return self.sort_by_priority(tasks) if by_priority else self.sort_by_time(tasks)

    # -- conflicts -----------------------------------------------------------

    def detect_conflicts(self, tasks: list[Task] | None = None, include_completed: bool = False) -> list[str]:
        """Find tasks scheduled at exactly the same date and time.

        Tasks have no duration, so this checks *exact* date/time matches, not
        overlapping time ranges. Completed tasks are ignored by default because
        they no longer need the owner's time.

        Returns:
            A list of human-readable warning messages (empty if no conflicts).
            This method never raises for conflicting data.
        """
        candidates = self._tasks_or_all(tasks)
        if not include_completed:
            candidates = [t for t in candidates if not t.completed]

        groups: dict[datetime, list[Task]] = {}
        for task in candidates:
            groups.setdefault(task.scheduled_at, []).append(task)

        warnings: list[str] = []
        for when in sorted(groups):
            clashing = groups[when]
            if len(clashing) < 2:
                continue
            pets = {t.pet_name for t in clashing}
            kind = f"same pet ({clashing[0].pet_name})" if len(pets) == 1 else "different pets"
            details = ", ".join(f"'{t.description}' ({t.pet_name})" for t in clashing)
            warnings.append(f"Conflict on {when:%Y-%m-%d at %H:%M} [{kind}]: {details}")
        return warnings

    # -- completion & recurrence ----------------------------------------------

    def find_task(self, task_id: str) -> Task | None:
        """Return the task with this id, or None."""
        for task in self.get_all_tasks():
            if task.task_id == task_id:
                return task
        return None

    def complete_task(self, task_id: str) -> Task | None:
        """Mark a task complete and schedule its next occurrence if it recurs.

        * The original task stays in the pet's list as completed (history).
        * Daily tasks get a new task 1 day later, weekly tasks 7 days later.
        * Completing an already-completed task does nothing, so no duplicate
          occurrences are ever created.

        Returns:
            The newly created next occurrence, or ``None`` if none was created.

        Raises:
            ValueError: if no task has this id.
        """
        task = self.find_task(task_id)
        if task is None:
            raise ValueError(f"No task found with id {task_id!r}.")

        newly_completed = task.mark_complete()
        if not newly_completed or not task.is_recurring():
            return None

        pet = self.owner.get_pet(task.pet_name)
        next_task = task.next_occurrence()
        if pet is None or next_task is None:
            return None
        # Extra safety: never add the same next occurrence twice.
        if pet.has_task_at(next_task.description, next_task.scheduled_date, next_task.scheduled_time):
            return None
        return pet.add_task(next_task)

    # -- summary ------------------------------------------------------------

    def get_summary(self) -> dict[str, int]:
        """Return simple counts for dashboards."""
        tasks = self.get_all_tasks()
        done = sum(1 for t in tasks if t.completed)
        return {
            "pets": len(self.owner.pets),
            "tasks": len(tasks),
            "completed": done,
            "pending": len(tasks) - done,
        }
