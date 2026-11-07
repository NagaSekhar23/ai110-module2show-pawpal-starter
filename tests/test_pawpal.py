"""Tests for the PawPal+ backend (pawpal_system.py).

Run with:  python -m pytest -v
"""

from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

DAY = date(2026, 1, 15)  # fixed date so tests never depend on "today"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def owner() -> Owner:
    """An owner with two pets and tasks added out of time order."""
    owner = Owner("Jordan")
    mochi = owner.add_pet(Pet("Mochi", "dog", breed="Shiba Inu", age=3))
    luna = owner.add_pet(Pet("Luna", "cat"))
    mochi.add_task(Task("Evening walk", DAY, "18:00", frequency="daily", priority="high"))
    mochi.add_task(Task("Morning walk", DAY, "07:00", frequency="daily", priority="medium"))
    luna.add_task(Task("Feed Luna", DAY, "09:00", priority="low"))
    luna.add_task(Task("Vet visit", DAY + timedelta(days=1), "08:00", priority="high"))
    return owner


@pytest.fixture
def scheduler(owner: Owner) -> Scheduler:
    return Scheduler(owner)


def find(scheduler: Scheduler, description: str) -> Task:
    """Helper: find the first task with this description."""
    return next(t for t in scheduler.get_all_tasks() if t.description == description)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class TestTask:
    def test_task_creation_defaults(self):
        task = Task("Walk", DAY, "08:30")
        assert task.description == "Walk"
        assert task.scheduled_date == DAY
        assert task.scheduled_time == time(8, 30)
        assert task.frequency == "once"
        assert task.priority == "medium"
        assert task.completed is False
        assert task.task_id

    def test_task_accepts_date_and_time_objects(self):
        task = Task("Walk", DAY, time(9, 15))
        assert task.scheduled_time == time(9, 15)

    def test_task_accepts_date_string(self):
        assert Task("Walk", "2026-01-15", "08:00").scheduled_date == DAY

    def test_frequency_and_priority_are_normalised(self):
        task = Task("Walk", DAY, "08:00", frequency=" Daily ", priority="HIGH")
        assert task.frequency == "daily"
        assert task.priority == "high"

    def test_mark_complete_changes_status(self):
        task = Task("Walk", DAY, "08:00")
        assert task.mark_complete() is True
        assert task.completed is True

    def test_mark_complete_twice_returns_false(self):
        task = Task("Walk", DAY, "08:00")
        task.mark_complete()
        assert task.mark_complete() is False
        assert task.completed is True

    def test_unique_ids(self):
        assert Task("A", DAY, "08:00").task_id != Task("A", DAY, "08:00").task_id

    def test_str_is_readable(self):
        text = str(Task("Walk", DAY, "08:00"))
        assert "Walk" in text and "08:00" in text and "Task(" not in text


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    @pytest.mark.parametrize("bad_time", ["25:00", "8am", "12:60", "", "noon", None, 830])
    def test_invalid_time(self, bad_time):
        with pytest.raises(ValueError):
            Task("Walk", DAY, bad_time)

    @pytest.mark.parametrize("bad_date", ["2026-13-01", "15/01/2026", "", None])
    def test_invalid_date(self, bad_date):
        with pytest.raises(ValueError):
            Task("Walk", bad_date, "08:00")

    @pytest.mark.parametrize("bad_freq", ["monthly", "", "every day", None])
    def test_invalid_frequency(self, bad_freq):
        with pytest.raises(ValueError):
            Task("Walk", DAY, "08:00", frequency=bad_freq)

    @pytest.mark.parametrize("bad_priority", ["urgent", "", None])
    def test_invalid_priority(self, bad_priority):
        with pytest.raises(ValueError):
            Task("Walk", DAY, "08:00", priority=bad_priority)

    @pytest.mark.parametrize("bad_description", ["", "   ", None])
    def test_empty_description(self, bad_description):
        with pytest.raises(ValueError):
            Task(bad_description, DAY, "08:00")

    def test_invalid_pet_data(self):
        with pytest.raises(ValueError):
            Pet("", "dog")
        with pytest.raises(ValueError):
            Pet("Mochi", "  ")
        with pytest.raises(ValueError):
            Pet("Mochi", "dog", age=-1)

    def test_invalid_owner_name(self):
        with pytest.raises(ValueError):
            Owner("  ")

    def test_add_non_task_to_pet(self):
        with pytest.raises(TypeError):
            Pet("Mochi", "dog").add_task("walk")

    def test_add_non_pet_to_owner(self):
        with pytest.raises(TypeError):
            Owner("Jordan").add_pet("Mochi")

    def test_duplicate_pet_name_rejected(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "dog"))
        with pytest.raises(ValueError):
            owner.add_pet(Pet("mochi", "cat"))

    def test_same_task_added_twice_rejected(self):
        pet = Pet("Mochi", "dog")
        task = Task("Walk", DAY, "08:00")
        pet.add_task(task)
        with pytest.raises(ValueError):
            pet.add_task(task)

    def test_scheduler_requires_owner(self):
        with pytest.raises(TypeError):
            Scheduler("Jordan")

    def test_complete_unknown_task_id(self, scheduler):
        with pytest.raises(ValueError):
            scheduler.complete_task("does-not-exist")


# ---------------------------------------------------------------------------
# Pet and Owner
# ---------------------------------------------------------------------------


class TestPetAndOwner:
    def test_pet_creation(self):
        pet = Pet("Mochi", "dog", breed="Shiba Inu", age=3)
        assert (pet.name, pet.species, pet.breed, pet.age) == ("Mochi", "dog", "Shiba Inu", 3)
        assert pet.get_tasks() == []

    def test_adding_task_increases_count_and_sets_pet(self):
        pet = Pet("Mochi", "dog")
        task = pet.add_task(Task("Walk", DAY, "08:00"))
        assert len(pet.get_tasks()) == 1
        assert task.pet_name == "Mochi"

    def test_pending_and_completed_lists(self):
        pet = Pet("Mochi", "dog")
        a = pet.add_task(Task("A", DAY, "08:00"))
        pet.add_task(Task("B", DAY, "09:00"))
        a.mark_complete()
        assert [t.description for t in pet.get_completed_tasks()] == ["A"]
        assert [t.description for t in pet.get_pending_tasks()] == ["B"]

    def test_remove_task(self):
        pet = Pet("Mochi", "dog")
        task = pet.add_task(Task("Walk", DAY, "08:00"))
        assert pet.remove_task(task.task_id) is True
        assert pet.remove_task(task.task_id) is False

    def test_adding_pets(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "dog"))
        assert [p.name for p in owner.get_pets()] == ["Mochi"]

    def test_multiple_pets(self, owner):
        assert [p.name for p in owner.get_pets()] == ["Mochi", "Luna"]
        assert owner.get_pet("luna").species == "cat"
        assert owner.get_pet("Rex") is None

    def test_remove_pet(self, owner):
        assert owner.remove_pet("Luna") is True
        assert owner.remove_pet("Luna") is False
        assert len(owner.get_all_tasks()) == 2

    def test_get_all_tasks_aggregates_every_pet(self, owner):
        tasks = owner.get_all_tasks()
        assert len(tasks) == 4
        assert {t.pet_name for t in tasks} == {"Mochi", "Luna"}

    def test_get_all_tasks_empty_owner(self):
        assert Owner("Jordan").get_all_tasks() == []


# ---------------------------------------------------------------------------
# Scheduler: retrieval, sorting, filtering
# ---------------------------------------------------------------------------


class TestScheduler:
    def test_scheduler_retrieves_tasks_through_owner(self, owner, scheduler):
        assert scheduler.get_all_tasks() == owner.get_all_tasks()

    def test_scheduler_sees_newly_added_pets(self, owner, scheduler):
        rex = owner.add_pet(Pet("Rex", "dog"))
        rex.add_task(Task("Bath", DAY, "15:00"))
        assert "Bath" in [t.description for t in scheduler.get_all_tasks()]

    def test_sort_by_time_is_chronological(self, scheduler):
        result = [t.description for t in scheduler.sort_by_time()]
        assert result == ["Morning walk", "Feed Luna", "Evening walk", "Vet visit"]

    def test_sort_by_time_uses_date_before_time(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Mochi", "dog"))
        pet.add_task(Task("Tomorrow early", DAY + timedelta(days=1), "06:00"))
        pet.add_task(Task("Today late", DAY, "23:00"))
        result = [t.description for t in Scheduler(owner).sort_by_time()]
        assert result == ["Today late", "Tomorrow early"]

    def test_sort_does_not_change_original_order(self, owner, scheduler):
        before = [t.description for t in owner.get_all_tasks()]
        scheduler.sort_by_time()
        assert [t.description for t in owner.get_all_tasks()] == before

    def test_sort_by_priority_then_time(self, scheduler):
        result = [t.description for t in scheduler.sort_by_priority()]
        assert result == ["Evening walk", "Vet visit", "Morning walk", "Feed Luna"]

    def test_filter_by_pet(self, scheduler):
        assert {t.description for t in scheduler.filter_by_pet("Luna")} == {"Feed Luna", "Vet visit"}
        assert scheduler.filter_by_pet("mochi")  # case-insensitive
        assert scheduler.filter_by_pet("Nobody") == []

    def test_filter_by_completion_status(self, scheduler):
        scheduler.complete_task(find(scheduler, "Feed Luna").task_id)
        assert [t.description for t in scheduler.filter_by_status(True)] == ["Feed Luna"]
        assert "Feed Luna" not in [t.description for t in scheduler.filter_by_status(False)]

    def test_filter_by_date(self, scheduler):
        assert [t.description for t in scheduler.filter_by_date(DAY + timedelta(days=1))] == ["Vet visit"]
        assert len(scheduler.filter_by_date("2026-01-15")) == 3

    def test_combined_filters(self, scheduler):
        result = scheduler.filter_tasks(pet_name="Mochi", completed=False, on_date=DAY)
        assert {t.description for t in result} == {"Morning walk", "Evening walk"}

    def test_daily_schedule_sorted(self, scheduler):
        result = [t.description for t in scheduler.get_daily_schedule(DAY)]
        assert result == ["Morning walk", "Feed Luna", "Evening walk"]

    def test_daily_schedule_by_priority(self, scheduler):
        result = [t.description for t in scheduler.get_daily_schedule(DAY, by_priority=True)]
        assert result == ["Evening walk", "Morning walk", "Feed Luna"]

    def test_empty_schedule(self):
        scheduler = Scheduler(Owner("Jordan"))
        assert scheduler.get_all_tasks() == []
        assert scheduler.sort_by_time() == []
        assert scheduler.filter_tasks(pet_name="Mochi") == []
        assert scheduler.get_daily_schedule(DAY) == []
        assert scheduler.detect_conflicts() == []
        assert scheduler.get_summary() == {"pets": 0, "tasks": 0, "completed": 0, "pending": 0}

    def test_pet_with_no_tasks(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "dog"))
        assert Scheduler(owner).get_daily_schedule(DAY) == []

    def test_summary_counts(self, scheduler):
        scheduler.complete_task(find(scheduler, "Feed Luna").task_id)
        assert scheduler.get_summary() == {"pets": 2, "tasks": 4, "completed": 1, "pending": 3}

    def test_get_recurring_tasks(self, scheduler):
        assert [t.description for t in scheduler.get_recurring_tasks()] == ["Morning walk", "Evening walk"]


# ---------------------------------------------------------------------------
# Recurrence
# ---------------------------------------------------------------------------


class TestRecurrence:
    def test_daily_recurrence(self, scheduler):
        walk = find(scheduler, "Morning walk")
        new = scheduler.complete_task(walk.task_id)
        assert new is not None
        assert new.scheduled_date == DAY + timedelta(days=1)
        assert new.scheduled_time == walk.scheduled_time
        assert new.frequency == "daily"
        assert new.priority == walk.priority
        assert new.pet_name == "Mochi"
        assert new.completed is False
        assert new.task_id != walk.task_id

    def test_weekly_recurrence(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Luna", "cat"))
        med = pet.add_task(Task("Flea medicine", DAY, "08:00", frequency="weekly"))
        new = Scheduler(owner).complete_task(med.task_id)
        assert new.scheduled_date == DAY + timedelta(days=7)
        assert new.frequency == "weekly"

    def test_recurrence_across_month_boundary(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Luna", "cat"))
        task = pet.add_task(Task("Feed", date(2026, 1, 31), "08:00", frequency="daily"))
        new = Scheduler(owner).complete_task(task.task_id)
        assert new.scheduled_date == date(2026, 2, 1)

    def test_original_task_remains_completed_in_history(self, owner, scheduler):
        walk = find(scheduler, "Morning walk")
        scheduler.complete_task(walk.task_id)
        mochi_tasks = owner.get_pet("Mochi").get_tasks()
        assert walk in mochi_tasks
        assert walk.completed is True
        assert len(mochi_tasks) == 3

    def test_no_duplicate_recurrence_when_completed_twice(self, owner, scheduler):
        walk = find(scheduler, "Morning walk")
        first = scheduler.complete_task(walk.task_id)
        second = scheduler.complete_task(walk.task_id)
        assert first is not None
        assert second is None
        walks = [t for t in owner.get_pet("Mochi").get_tasks() if t.description == "Morning walk"]
        assert len(walks) == 2

    def test_no_duplicate_if_next_occurrence_already_exists(self, owner, scheduler):
        mochi = owner.get_pet("Mochi")
        mochi.add_task(Task("Morning walk", DAY + timedelta(days=1), "07:00", frequency="daily"))
        assert scheduler.complete_task(find(scheduler, "Morning walk").task_id) is None
        assert len([t for t in mochi.get_tasks() if t.description == "Morning walk"]) == 2

    def test_one_time_task_does_not_recur(self, owner, scheduler):
        feed = find(scheduler, "Feed Luna")
        assert scheduler.complete_task(feed.task_id) is None
        assert feed.completed is True
        assert len(owner.get_pet("Luna").get_tasks()) == 2

    def test_next_occurrence_chain(self, scheduler):
        first = find(scheduler, "Morning walk")
        second = scheduler.complete_task(first.task_id)
        third = scheduler.complete_task(second.task_id)
        assert third.scheduled_date == DAY + timedelta(days=2)

    def test_next_occurrence_none_for_once(self):
        assert Task("Bath", DAY, "10:00").next_occurrence() is None


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestConflicts:
    def test_same_time_same_pet(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Mochi", "dog"))
        pet.add_task(Task("Walk", DAY, "08:00"))
        pet.add_task(Task("Feed", DAY, "08:00"))
        warnings = Scheduler(owner).detect_conflicts()
        assert len(warnings) == 1
        assert "same pet (Mochi)" in warnings[0]
        assert "Walk" in warnings[0] and "Feed" in warnings[0]

    def test_same_time_different_pets(self):
        owner = Owner("Jordan")
        owner.add_pet(Pet("Mochi", "dog")).add_task(Task("Walk", DAY, "08:00"))
        owner.add_pet(Pet("Luna", "cat")).add_task(Task("Feed", DAY, "08:00"))
        warnings = Scheduler(owner).detect_conflicts()
        assert len(warnings) == 1
        assert "different pets" in warnings[0]
        assert "Mochi" in warnings[0] and "Luna" in warnings[0]

    def test_no_false_conflict_for_different_times(self, scheduler):
        assert scheduler.detect_conflicts() == []

    def test_same_time_different_dates_is_not_conflict(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Mochi", "dog"))
        pet.add_task(Task("Walk", DAY, "08:00"))
        pet.add_task(Task("Walk", DAY + timedelta(days=1), "08:00"))
        assert Scheduler(owner).detect_conflicts() == []

    def test_empty_task_list(self):
        assert Scheduler(Owner("Jordan")).detect_conflicts() == []
        assert Scheduler(Owner("Jordan")).detect_conflicts(tasks=[]) == []

    def test_three_way_conflict_is_one_warning(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Mochi", "dog"))
        for name in ("A", "B", "C"):
            pet.add_task(Task(name, DAY, "08:00"))
        warnings = Scheduler(owner).detect_conflicts()
        assert len(warnings) == 1
        assert all(name in warnings[0] for name in ("'A'", "'B'", "'C'"))

    def test_completed_tasks_ignored_by_default(self):
        owner = Owner("Jordan")
        pet = owner.add_pet(Pet("Mochi", "dog"))
        done = pet.add_task(Task("Walk", DAY, "08:00"))
        pet.add_task(Task("Feed", DAY, "08:00"))
        done.mark_complete()
        scheduler = Scheduler(owner)
        assert scheduler.detect_conflicts() == []
        assert len(scheduler.detect_conflicts(include_completed=True)) == 1


# ---------------------------------------------------------------------------
# JSON persistence (optional extension)
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_and_load_round_trip(self, owner, scheduler, tmp_path):
        scheduler.complete_task(find(scheduler, "Morning walk").task_id)
        path = tmp_path / "data.json"
        owner.save_to_json(path)
        loaded = Owner.load_from_json(path)

        assert loaded.name == owner.name
        assert [p.name for p in loaded.get_pets()] == ["Mochi", "Luna"]
        original = [t.to_dict() for t in owner.get_all_tasks()]
        restored = [t.to_dict() for t in loaded.get_all_tasks()]
        assert len(restored) == 5
        assert original == restored
