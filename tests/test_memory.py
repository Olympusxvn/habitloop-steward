"""Tests for memory store (SQLite CRUD operations)."""

import pytest
from datetime import datetime, date, timedelta
import tempfile
import os
from pathlib import Path

from habitloop.memory import MemoryStore
from habitloop.models import Profile, HabitLog, Constraint


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def store(temp_db):
    """Create a memory store with temporary database."""
    store = MemoryStore(temp_db)
    yield store
    store.close()


class TestProfile:
    """Tests for profile CRUD operations."""

    def test_no_profile_initially(self, store):
        """Test that no profile exists initially."""
        profile = store.get_profile()
        assert profile is None

    def test_create_profile(self, store):
        """Test creating a new profile."""
        profile = store.upsert_profile(
            timezone="America/New_York",
            goals={"exercise": "5 days/week"},
            quiet_hours={"start": "22:00", "end": "07:00"},
            preferences={"notifications": True}
        )
        
        assert profile is not None
        assert profile.id == 1
        assert profile.timezone == "America/New_York"
        assert profile.goals == {"exercise": "5 days/week"}
        assert profile.quiet_hours == {"start": "22:00", "end": "07:00"}
        assert profile.preferences == {"notifications": True}

    def test_update_profile(self, store):
        """Test updating an existing profile."""
        store.upsert_profile(timezone="UTC")
        
        updated = store.upsert_profile(
            timezone="Europe/London",
            goals={"reading": "30 min/day"}
        )
        
        assert updated.timezone == "Europe/London"
        assert updated.goals == {"reading": "30 min/day"}
        
        profile = store.get_profile()
        assert profile.id == 1
        assert profile.timezone == "Europe/London"

    def test_profile_updated_at(self, store):
        """Test that updated_at is set correctly."""
        before = datetime.utcnow()
        profile = store.upsert_profile(timezone="UTC")
        after = datetime.utcnow()
        
        assert before <= profile.updated_at <= after


class TestHabitLog:
    """Tests for habit log CRUD operations."""

    def test_log_habit_minimal(self, store):
        """Test logging a habit with minimal data."""
        log = store.log_habit("exercise")
        
        assert log.id is not None
        assert log.habit_key == "exercise"
        assert log.value is None
        assert log.note is None
        assert log.source == "cli"
        assert isinstance(log.logged_at, datetime)

    def test_log_habit_full(self, store):
        """Test logging a habit with all data."""
        now = datetime.utcnow()
        log = store.log_habit(
            habit_key="water",
            value="500ml",
            note="morning routine",
            logged_at=now,
            source="app"
        )
        
        assert log.habit_key == "water"
        assert log.value == "500ml"
        assert log.note == "morning routine"
        assert log.source == "app"
        assert log.logged_at == now

    def test_get_logs_for_date(self, store):
        """Test retrieving logs for a specific date."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        store.log_habit("exercise", logged_at=datetime.combine(today, datetime.min.time()))
        store.log_habit("water", logged_at=datetime.combine(today, datetime.max.time()))
        store.log_habit("meditation", logged_at=datetime.combine(yesterday, datetime.min.time()))
        
        today_logs = store.get_logs_for_date(today)
        assert len(today_logs) == 2
        assert {log.habit_key for log in today_logs} == {"exercise", "water"}
        
        yesterday_logs = store.get_logs_for_date(yesterday)
        assert len(yesterday_logs) == 1
        assert yesterday_logs[0].habit_key == "meditation"

    def test_get_logs_by_habit(self, store):
        """Test retrieving logs for a specific habit."""
        for i in range(5):
            store.log_habit("exercise", value=f"session_{i}")
        
        store.log_habit("water")
        
        exercise_logs = store.get_logs_by_habit("exercise", limit=3)
        assert len(exercise_logs) == 3
        assert all(log.habit_key == "exercise" for log in exercise_logs)
        
        all_exercise = store.get_logs_by_habit("exercise", limit=10)
        assert len(all_exercise) == 5

    def test_logs_ordered_desc(self, store):
        """Test that logs are returned in descending order."""
        times = [
            datetime(2026, 1, 1, 10, 0),
            datetime(2026, 1, 1, 12, 0),
            datetime(2026, 1, 1, 8, 0),
        ]
        
        for t in times:
            store.log_habit("test", logged_at=t)
        
        logs = store.get_logs_by_habit("test")
        assert logs[0].logged_at == datetime(2026, 1, 1, 12, 0)
        assert logs[1].logged_at == datetime(2026, 1, 1, 10, 0)
        assert logs[2].logged_at == datetime(2026, 1, 1, 8, 0)


class TestConstraints:
    """Tests for constraints CRUD operations."""

    def test_add_constraint(self, store):
        """Test adding a new constraint."""
        constraint = store.add_constraint(
            rule_text="Exercise at least 3 times per week",
            source="user"
        )
        
        assert constraint.id is not None
        assert constraint.rule_text == "Exercise at least 3 times per week"
        assert constraint.source == "user"
        assert constraint.active is True

    def test_get_active_constraints(self, store):
        """Test retrieving active constraints."""
        c1 = store.add_constraint("Rule 1", active=True)
        c2 = store.add_constraint("Rule 2", active=True)
        c3 = store.add_constraint("Rule 3", active=False)
        
        active = store.get_active_constraints()
        assert len(active) == 2
        assert {c.rule_text for c in active} == {"Rule 1", "Rule 2"}

    def test_deactivate_constraint(self, store):
        """Test deactivating a constraint."""
        constraint = store.add_constraint("Test rule")
        assert constraint.active is True
        
        store.deactivate_constraint(constraint.id)
        
        active = store.get_active_constraints()
        assert len(active) == 0

    def test_constraints_ordered_desc(self, store):
        """Test that constraints are ordered by creation date descending."""
        c1 = store.add_constraint("First")
        c2 = store.add_constraint("Second")
        c3 = store.add_constraint("Third")
        
        constraints = store.get_active_constraints()
        assert constraints[0].rule_text == "Third"
        assert constraints[1].rule_text == "Second"
        assert constraints[2].rule_text == "First"


class TestContextManager:
    """Tests for context manager usage."""

    def test_context_manager(self, temp_db):
        """Test using store as context manager."""
        with MemoryStore(temp_db) as store:
            store.log_habit("test")
        
        with MemoryStore(temp_db) as store:
            logs = store.get_logs_by_habit("test")
            assert len(logs) == 1
