"""Tests for skills module."""

import pytest
from datetime import datetime, date, timedelta
import tempfile
import os
from pathlib import Path

from habitloop.memory import MemoryStore
from habitloop.skills import (
    DailyNudgeSkill, PlanAdjustSkill, HabitStats,
    calculate_streak, calculate_adherence
)


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


class TestStreakCalculation:
    """Tests for streak calculation."""
    
    def test_empty_logs(self, store):
        """Test streak with no logs."""
        streak = calculate_streak([], "exercise")
        assert streak == 0
    
    def test_single_day_streak(self, store):
        """Test streak with one day of logging."""
        today = date.today()
        log = store.log_habit("exercise", logged_at=datetime.combine(today, datetime.min.time()))
        
        logs = store.get_logs_by_habit("exercise")
        streak = calculate_streak(logs, "exercise")
        assert streak == 1
    
    def test_multi_day_streak(self, store):
        """Test streak with consecutive days."""
        today = date.today()
        
        for i in range(5):
            day = today - timedelta(days=i)
            store.log_habit("exercise", logged_at=datetime.combine(day, datetime.min.time()))
        
        logs = store.get_logs_by_habit("exercise")
        streak = calculate_streak(logs, "exercise")
        assert streak == 5
    
    def test_broken_streak(self, store):
        """Test that broken streak resets."""
        today = date.today()
        
        # Log today
        store.log_habit("exercise", logged_at=datetime.combine(today, datetime.min.time()))
        
        # Skip yesterday, log 2 days ago
        two_days_ago = today - timedelta(days=2)
        store.log_habit("exercise", logged_at=datetime.combine(two_days_ago, datetime.min.time()))
        
        logs = store.get_logs_by_habit("exercise")
        streak = calculate_streak(logs, "exercise")
        assert streak == 1  # Only counts today


class TestAdherenceCalculation:
    """Tests for adherence calculation."""
    
    def test_empty_logs(self):
        """Test adherence with no logs."""
        adherence = calculate_adherence([], days=7)
        assert adherence == 0.0
    
    def test_perfect_adherence(self, store):
        """Test 100% adherence."""
        today = date.today()
        
        for i in range(7):
            day = today - timedelta(days=i)
            store.log_habit("exercise", logged_at=datetime.combine(day, datetime.min.time()))
        
        logs = store.get_logs_by_habit("exercise")
        adherence = calculate_adherence(logs, days=7)
        assert adherence == 100.0
    
    def test_partial_adherence(self, store):
        """Test partial adherence."""
        today = date.today()
        
        # Log on 3 out of 7 days
        for i in [0, 2, 4]:
            day = today - timedelta(days=i)
            store.log_habit("exercise", logged_at=datetime.combine(day, datetime.min.time()))
        
        logs = store.get_logs_by_habit("exercise")
        adherence = calculate_adherence(logs, days=7)
        expected = (3 / 7) * 100.0
        assert abs(adherence - expected) < 0.1


class TestHabitStats:
    """Tests for HabitStats class."""
    
    def test_no_logs(self, store):
        """Test stats with no logs."""
        stats = HabitStats("exercise", store)
        result = stats.compute()
        
        assert result["habit_key"] == "exercise"
        assert result["total_logs"] == 0
        assert result["current_streak"] == 0
        assert result["adherence_7d"] == 0.0
        assert result["adherence_30d"] == 0.0
    
    def test_with_logs(self, store):
        """Test stats with some logs."""
        today = date.today()
        
        for i in range(5):
            day = today - timedelta(days=i)
            store.log_habit("exercise", logged_at=datetime.combine(day, datetime.min.time()))
        
        stats = HabitStats("exercise", store)
        result = stats.compute()
        
        assert result["habit_key"] == "exercise"
        assert result["total_logs"] == 5
        assert result["current_streak"] == 5
        assert result["adherence_7d"] > 0


class TestDailyNudgeSkill:
    """Tests for DailyNudgeSkill (offline mode)."""
    
    def test_nudge_no_logs(self, store):
        """Test nudge with no habits logged today."""
        skill = DailyNudgeSkill(store, llm_client=None)
        result = skill.execute()
        
        assert result.success
        assert "logged yet" in result.message.lower() or "no habits" in result.message.lower()
        assert "NOT medical advice" in result.message
    
    def test_nudge_with_logs(self, store):
        """Test nudge with some habits logged."""
        store.log_habit("exercise")
        store.log_habit("water")
        
        skill = DailyNudgeSkill(store, llm_client=None)
        result = skill.execute()
        
        assert result.success
        assert "NOT medical advice" in result.message
        assert result.data.get("llm_available") == False


class TestPlanAdjustSkill:
    """Tests for PlanAdjustSkill (offline mode)."""
    
    def test_plan_adjust_no_logs(self, store):
        """Test plan adjust with no data."""
        skill = PlanAdjustSkill(store, llm_client=None)
        result = skill.execute()
        
        assert result.success
        assert "NOT medical advice" in result.message
    
    def test_plan_adjust_with_habit(self, store):
        """Test plan adjust for specific habit."""
        # Create some logs
        for i in range(5):
            store.log_habit("exercise")
        
        skill = PlanAdjustSkill(store, llm_client=None)
        result = skill.execute(habit_key="exercise")
        
        assert result.success
        assert "NOT medical advice" in result.message
