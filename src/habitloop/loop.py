"""Graph/loop runtime for HabitLoop Steward.

Implements the propose → verify → correct loop with separate maker and verifier roles.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, time
from enum import Enum
import json

from .memory import MemoryStore
from .llm import NebiusClient


class IntentType(Enum):
    """Type of user intent."""
    CHAT = "chat"
    SCHEDULED_JOB = "scheduled_job"
    VERIFICATION = "verification"


class VerificationResult(Enum):
    """Result of verification gate."""
    GREEN = "green"  # Passed all checks
    YELLOW = "yellow"  # Warnings but can proceed
    RED = "red"  # Must correct or escalate


class IntentSplitter:
    """Classify intent as chat interaction vs scheduled job."""
    
    @staticmethod
    def classify(input_text: str, context: Optional[Dict[str, Any]] = None) -> IntentType:
        """Classify user input into intent type.
        
        For now, uses simple keyword matching. With LLM, could be more sophisticated.
        """
        lower = input_text.lower()
        
        if any(word in lower for word in ["schedule", "remind", "nightly", "daily", "weekly"]):
            return IntentType.SCHEDULED_JOB
        
        if any(word in lower for word in ["verify", "check", "validate", "review"]):
            return IntentType.VERIFICATION
        
        return IntentType.CHAT


class Proposal:
    """A proposal from the maker that needs verification."""
    
    def __init__(self, proposal_type: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        self.proposal_type = proposal_type
        self.data = data
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "proposal_type": self.proposal_type,
            "data": self.data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class VerificationIssue:
    """An issue found during verification."""
    
    def __init__(self, severity: VerificationResult, category: str, message: str, 
                 field: Optional[str] = None):
        self.severity = severity
        self.category = category
        self.message = message
        self.field = field
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "field": self.field
        }


class Verifier:
    """Independent verifier that checks proposals against rules and constraints.
    
    The verifier does NOT have access to maker's reasoning, only the proposal itself.
    """
    
    def __init__(self, store: MemoryStore):
        self.store = store
        
    def verify_habit_log_proposal(self, proposal: Proposal) -> Tuple[VerificationResult, List[VerificationIssue]]:
        """Verify a habit log proposal.
        
        Checks:
        - Schema validation (required fields)
        - Quiet hours compliance
        - Constraint violations
        - Conflict with existing logs
        """
        issues = []
        data = proposal.data
        
        # Schema check
        if "habit_key" not in data or not data["habit_key"]:
            issues.append(VerificationIssue(
                VerificationResult.RED,
                "schema",
                "Missing required field: habit_key",
                field="habit_key"
            ))
        
        # Quiet hours check
        profile = self.store.get_profile()
        if profile and profile.quiet_hours:
            quiet_start = profile.quiet_hours.get("start")
            quiet_end = profile.quiet_hours.get("end")
            
            if quiet_start and quiet_end:
                now = datetime.now().time()
                start_time = time.fromisoformat(quiet_start)
                end_time = time.fromisoformat(quiet_end)
                
                # Simple check (doesn't handle wraparound midnight properly)
                if start_time <= now <= end_time:
                    issues.append(VerificationIssue(
                        VerificationResult.YELLOW,
                        "quiet_hours",
                        f"Logging during quiet hours ({quiet_start} - {quiet_end})",
                        field="logged_at"
                    ))
        
        # Active constraints check
        constraints = self.store.get_active_constraints()
        habit_key = data.get("habit_key", "")
        
        for constraint in constraints:
            # Simple keyword matching
            if habit_key.lower() in constraint.rule_text.lower():
                issues.append(VerificationIssue(
                    VerificationResult.YELLOW,
                    "constraint",
                    f"Active constraint may apply: {constraint.rule_text}",
                    field="habit_key"
                ))
        
        # Determine overall result
        if any(i.severity == VerificationResult.RED for i in issues):
            return VerificationResult.RED, issues
        elif any(i.severity == VerificationResult.YELLOW for i in issues):
            return VerificationResult.YELLOW, issues
        else:
            return VerificationResult.GREEN, issues
    
    def verify(self, proposal: Proposal) -> Tuple[VerificationResult, List[VerificationIssue]]:
        """Verify a proposal based on its type."""
        if proposal.proposal_type == "habit_log":
            return self.verify_habit_log_proposal(proposal)
        else:
            return VerificationResult.GREEN, []


class ProposalCorrector:
    """Attempts to auto-correct proposals that fail verification."""
    
    def __init__(self, store: MemoryStore, llm_client: Optional[NebiusClient] = None):
        self.store = store
        self.llm = llm_client
        
    def correct(self, proposal: Proposal, issues: List[VerificationIssue]) -> Optional[Proposal]:
        """Try to correct the proposal based on issues found.
        
        Returns corrected proposal or None if cannot auto-correct.
        """
        # Only auto-correct certain types of issues
        can_correct = True
        
        for issue in issues:
            if issue.severity == VerificationResult.RED:
                # RED issues require escalation
                can_correct = False
                break
        
        if not can_correct:
            return None
        
        # For now, simple corrections (could use LLM for more sophisticated fixes)
        corrected_data = proposal.data.copy()
        corrected_metadata = proposal.metadata.copy()
        corrected_metadata["corrections"] = [i.to_dict() for i in issues]
        
        return Proposal(proposal.proposal_type, corrected_data, corrected_metadata)


class LoopRuntime:
    """Main loop runtime: propose → verify → correct (≤3 attempts) → escalate."""
    
    MAX_CORRECTION_ATTEMPTS = 3
    
    def __init__(self, store: MemoryStore, llm_client: Optional[NebiusClient] = None):
        self.store = store
        self.llm = llm_client
        self.verifier = Verifier(store)
        self.corrector = ProposalCorrector(store, llm_client)
        
    def run_loop(self, initial_proposal: Proposal) -> Dict[str, Any]:
        """Run the full loop: propose → verify → correct → escalate.
        
        Returns:
            Dict with status, final_result, attempts, issues, etc.
        """
        proposal = initial_proposal
        attempts = 0
        history = []
        
        while attempts < self.MAX_CORRECTION_ATTEMPTS:
            attempts += 1
            
            # Verify
            result, issues = self.verifier.verify(proposal)
            
            history.append({
                "attempt": attempts,
                "proposal": proposal.to_dict(),
                "verification_result": result.value,
                "issues": [i.to_dict() for i in issues]
            })
            
            if result == VerificationResult.GREEN:
                return {
                    "status": "success",
                    "result": result.value,
                    "attempts": attempts,
                    "history": history,
                    "final_proposal": proposal.to_dict()
                }
            
            if result == VerificationResult.YELLOW and attempts == 1:
                # YELLOW on first attempt: proceed with warning
                return {
                    "status": "success_with_warnings",
                    "result": result.value,
                    "attempts": attempts,
                    "history": history,
                    "final_proposal": proposal.to_dict(),
                    "warnings": [i.to_dict() for i in issues]
                }
            
            # Try to correct
            corrected = self.corrector.correct(proposal, issues)
            
            if corrected is None:
                # Cannot auto-correct, escalate
                return {
                    "status": "escalated",
                    "result": result.value,
                    "attempts": attempts,
                    "history": history,
                    "escalation_reason": "Cannot auto-correct RED issues",
                    "issues": [i.to_dict() for i in issues]
                }
            
            proposal = corrected
        
        # Exceeded max attempts
        return {
            "status": "failed",
            "result": "max_attempts_exceeded",
            "attempts": attempts,
            "history": history,
            "final_issues": [i.to_dict() for i in issues]
        }


def demo_bad_proposal() -> Dict[str, Any]:
    """Create an intentionally bad proposal for demo purposes."""
    return Proposal(
        proposal_type="habit_log",
        data={
            # Missing habit_key - should trigger RED
            "value": "test",
            "note": "This proposal is intentionally bad for demo"
        },
        metadata={"demo": True, "expected_result": "RED"}
    )


def demo_quiet_hours_proposal() -> Dict[str, Any]:
    """Create a proposal that violates quiet hours (if set)."""
    return Proposal(
        proposal_type="habit_log",
        data={
            "habit_key": "late_night_snack",
            "value": "1 cookie",
            "note": "This might be during quiet hours"
        },
        metadata={"demo": True, "expected_result": "YELLOW"}
    )


def demo_good_proposal() -> Dict[str, Any]:
    """Create a valid proposal for demo."""
    return Proposal(
        proposal_type="habit_log",
        data={
            "habit_key": "exercise",
            "value": "30 min",
            "note": "Morning workout"
        },
        metadata={"demo": True, "expected_result": "GREEN"}
    )
