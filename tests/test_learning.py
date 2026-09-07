"""Tests for learning module."""

import pytest
from datetime import datetime, timedelta, date
import tempfile
import os
from pathlib import Path

from habitloop.memory import MemoryStore
from habitloop.learning import ConstraintLearner, WeeklyReviewSkill


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


class TestConstraintLearner:
    """Tests for constraint learning."""
    
    def test_no_patterns_with_no_data(self, store):
        """Test that no patterns detected with no data."""
        learner = ConstraintLearner(store)
        patterns = learner.detect_failure_patterns()
        
        assert len(patterns) == 0
    
    def test_learning_cycle_no_data(self, store):
        """Test learning cycle with no data."""
        learner = ConstraintLearner(store)
        result = learner.run_learning_cycle()
        
        assert result["patterns_detected"] == 0
        assert result["constraints_created"] == 0
    
    def test_learning_cycle_with_good_adherence(self, store):
        """Test that good adherence doesn't trigger learning."""
        # Log consistently for 14 days
        for i in range(14):
            day = date.today() - timedelta(days=i)
            store.log_habit("exercise", logged_at=datetime.combine(day, datetime.min.time()))
        
        learner = ConstraintLearner(store)
        result = learner.run_learning_cycle()
        
        # Should not create constraints for good habits
        assert result["constraints_created"] == 0
    
    def test_no_duplicate_constraints(self, store):
        """Test that duplicate constraints are not created."""
        # Manually add a constraint
        store.add_constraint("Review exercise", source="user")
        
        # Create low adherence pattern
        store.log_habit("exercise", logged_at=datetime.now() - timedelta(days=10))
        store.log_habit("exercise", logged_at=datetime.now() - timedelta(days=9))
        store.log_habit("exercise", logged_at=datetime.now() - timedelta(days=8))
        
        learner = ConstraintLearner(store)
        result = learner.run_learning_cycle()
        
        # Should not create duplicate constraint
        assert result["constraints_created"] == 0


class TestWeeklyReviewSkill:
    """Tests for weekly review (offline mode)."""
    
    def test_weekly_review_no_data(self, store):
        """Test weekly review with no data."""
        skill = WeeklyReviewSkill(store, llm_client=None)
        result = skill.execute(weeks_back=1)
        
        assert result["success"]
        assert "summary" in result
        assert result.get("llm_available") == False
    
    def test_weekly_review_with_data(self, store):
        """Test weekly review with some data."""
        # Add logs over the past week
        today = date.today()
        for i in range(5):
            day = today - timedelta(days=i)
            store.log_habit("exercise", logged_at=datetime.combine(day, datetime.min.time()))
        
        skill = WeeklyReviewSkill(store, llm_client=None)
        result = skill.execute(weeks_back=1)
        
        assert result["success"]
        assert result["stats"]["total_logs"] >= 5
        assert result["stats"]["unique_habits"] >= 1
        assert "exercise" in result["summary"].lower()
    
    def test_weekly_stats_computation(self, store):
        """Test that weekly stats are computed correctly."""
        # Add varied logs
        today = date.today()
        store.log_habit("exercise", logged_at=datetime.combine(today, datetime.min.time()))
        store.log_habit("water", logged_at=datetime.combine(today, datetime.min.time()))
        store.log_habit("exercise", logged_at=datetime.combine(today - timedelta(days=1), datetime.min.time()))
        
        skill = WeeklyReviewSkill(store, llm_client=None)
        stats = skill.compute_weekly_stats(weeks_back=1)
        
        assert stats["total_logs"] == 3
        assert stats["unique_habits"] == 2
        assert stats["days_active"] >= 1
