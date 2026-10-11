"""Tests for loop runtime."""

import pytest
from datetime import datetime
import tempfile
import os
from pathlib import Path

from habitloop.memory import MemoryStore
from habitloop.loop import (
    LoopRuntime, Proposal, Verifier, VerificationResult,
    IntentSplitter, IntentType
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


class TestIntentSplitter:
    """Tests for intent classification."""
    
    def test_chat_intent(self):
        """Test chat intent classification."""
        result = IntentSplitter.classify("How am I doing?")
        assert result == IntentType.CHAT
    
    def test_scheduled_job_intent(self):
        """Test scheduled job intent."""
        result = IntentSplitter.classify("Schedule a nightly review")
        assert result == IntentType.SCHEDULED_JOB
    
    def test_verification_intent(self):
        """Test verification intent."""
        result = IntentSplitter.classify("Verify this proposal")
        assert result == IntentType.VERIFICATION


class TestProposal:
    """Tests for Proposal class."""
    
    def test_proposal_creation(self):
        """Test creating a proposal."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"habit_key": "exercise", "value": "30 min"},
            metadata={"source": "test"}
        )
        
        assert proposal.proposal_type == "habit_log"
        assert proposal.data["habit_key"] == "exercise"
        assert proposal.metadata["source"] == "test"
    
    def test_proposal_serialization(self):
        """Test proposal serialization."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"habit_key": "exercise"}
        )
        
        d = proposal.to_dict()
        assert d["proposal_type"] == "habit_log"
        assert d["data"]["habit_key"] == "exercise"
        assert "created_at" in d


class TestVerifier:
    """Tests for verification logic."""
    
    def test_verify_valid_proposal(self, store):
        """Test verification of valid proposal."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"habit_key": "exercise", "value": "30 min"}
        )
        
        verifier = Verifier(store)
        result, issues = verifier.verify(proposal)
        
        assert result in [VerificationResult.GREEN, VerificationResult.YELLOW]
    
    def test_verify_missing_habit_key(self, store):
        """Test verification fails for missing habit_key."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"value": "30 min"}  # Missing habit_key
        )
        
        verifier = Verifier(store)
        result, issues = verifier.verify(proposal)
        
        assert result == VerificationResult.RED
        assert len(issues) > 0
        assert issues[0].category == "schema"
    
    def test_verify_with_constraints(self, store):
        """Test verification checks constraints."""
        # Add a constraint
        store.add_constraint("exercise should be limited", source="user")
        
        proposal = Proposal(
            proposal_type="habit_log",
            data={"habit_key": "exercise", "value": "30 min"}
        )
        
        verifier = Verifier(store)
        result, issues = verifier.verify(proposal)
        
        # Should get YELLOW warning about constraint
        if result == VerificationResult.YELLOW:
            assert any(issue.category == "constraint" for issue in issues)


class TestLoopRuntime:
    """Tests for the full loop runtime."""
    
    def test_loop_with_valid_proposal(self, store):
        """Test loop with valid proposal."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"habit_key": "exercise", "value": "30 min"}
        )
        
        runtime = LoopRuntime(store, llm_client=None)
        result = runtime.run_loop(proposal)
        
        assert result["status"] in ["success", "success_with_warnings"]
        assert result["attempts"] >= 1
    
    def test_loop_with_invalid_proposal(self, store):
        """Test loop with invalid proposal (missing required field)."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"value": "30 min"}  # Missing habit_key
        )
        
        runtime = LoopRuntime(store, llm_client=None)
        result = runtime.run_loop(proposal)
        
        assert result["status"] == "escalated"
        assert "issues" in result
    
    def test_loop_history_tracking(self, store):
        """Test that loop tracks history of attempts."""
        proposal = Proposal(
            proposal_type="habit_log",
            data={"habit_key": "exercise"}
        )
        
        runtime = LoopRuntime(store, llm_client=None)
        result = runtime.run_loop(proposal)
        
        assert "history" in result
        assert len(result["history"]) >= 1
        assert result["history"][0]["attempt"] == 1
