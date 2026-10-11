"""Learning module for HabitLoop Steward.

Implements constraint learning from repeated failures and pattern recognition.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from collections import Counter

from .memory import MemoryStore
from .models import Constraint


class FailurePattern:
    """Represents a pattern of failures for learning."""
    
    def __init__(self, habit_key: str, failure_count: int, 
                 time_window_days: int, contexts: List[Dict[str, Any]]):
        self.habit_key = habit_key
        self.failure_count = failure_count
        self.time_window_days = time_window_days
        self.contexts = contexts
        self.detected_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "habit_key": self.habit_key,
            "failure_count": self.failure_count,
            "time_window_days": self.time_window_days,
            "contexts": self.contexts,
            "detected_at": self.detected_at.isoformat()
        }


class ConstraintLearner:
    """Learns constraints from repeated failures.
    
    After ≥3 related failures in a time window, proposes a new constraint.
    """
    
    FAILURE_THRESHOLD = 3
    TIME_WINDOW_DAYS = 14
    
    def __init__(self, store: MemoryStore):
        self.store = store
        
    def detect_failure_patterns(self) -> List[FailurePattern]:
        """Detect patterns of repeated failures.
        
        For now, we detect patterns based on:
        - Low adherence (< 30%) over the time window
        - Multiple gaps in logging
        """
        patterns = []
        
        # Get all habit keys
        cursor = self.store.conn.cursor()
        cursor.execute("SELECT DISTINCT habit_key FROM habit_log ORDER BY habit_key")
        habit_keys = [row[0] for row in cursor.fetchall()]
        
        cutoff = datetime.now() - timedelta(days=self.TIME_WINDOW_DAYS)
        
        for habit_key in habit_keys:
            # Get logs in time window
            cursor.execute("""
                SELECT * FROM habit_log
                WHERE habit_key = ? AND logged_at >= ?
                ORDER BY logged_at DESC
            """, (habit_key, cutoff.isoformat()))
            
            logs = cursor.fetchall()
            
            if not logs:
                continue
            
            # Count days with logs
            days_logged = set()
            for log in logs:
                logged_at = datetime.fromisoformat(log[4])  # logged_at is column 4
                days_logged.add(logged_at.date())
            
            adherence = (len(days_logged) / self.TIME_WINDOW_DAYS) * 100.0
            
            # If adherence is low, this is a "failure pattern"
            if adherence < 30 and len(logs) >= self.FAILURE_THRESHOLD:
                contexts = []
                for log in logs[:5]:  # Sample last 5
                    contexts.append({
                        "logged_at": log[4],
                        "value": log[2],
                        "note": log[3]
                    })
                
                pattern = FailurePattern(
                    habit_key=habit_key,
                    failure_count=len(logs),
                    time_window_days=self.TIME_WINDOW_DAYS,
                    contexts=contexts
                )
                patterns.append(pattern)
        
        return patterns
    
    def learn_constraint_from_pattern(self, pattern: FailurePattern) -> Optional[Constraint]:
        """Create a constraint from a detected failure pattern.
        
        Args:
            pattern: Detected failure pattern
            
        Returns:
            New constraint or None if already exists
        """
        # Check if we already have a similar constraint
        existing = self.store.get_active_constraints()
        
        for constraint in existing:
            if pattern.habit_key.lower() in constraint.rule_text.lower():
                return None  # Already have a constraint for this
        
        # Create new constraint
        rule_text = f"Review {pattern.habit_key}: adherence was low ({pattern.failure_count} logs in {pattern.time_window_days} days). Consider adjusting frequency or difficulty."
        
        constraint = self.store.add_constraint(
            rule_text=rule_text,
            source="learned",
            active=True
        )
        
        return constraint
    
    def run_learning_cycle(self) -> Dict[str, Any]:
        """Run a full learning cycle: detect patterns → create constraints.
        
        Returns:
            Summary of learning cycle results
        """
        patterns = self.detect_failure_patterns()
        
        new_constraints = []
        for pattern in patterns:
            constraint = self.learn_constraint_from_pattern(pattern)
            if constraint:
                new_constraints.append(constraint)
        
        return {
            "patterns_detected": len(patterns),
            "constraints_created": len(new_constraints),
            "patterns": [p.to_dict() for p in patterns],
            "new_constraints": [c.rule_text for c in new_constraints]
        }


class WeeklyReviewSkill:
    """Generate weekly review with code-node stats and optional LLM synthesis.
    
    DISCLAIMER: This is NOT medical advice. These are data observations only.
    """
    
    def __init__(self, store: MemoryStore, llm_client: Optional['NebiusClient'] = None):
        self.store = store
        self.llm = llm_client
        
    def compute_weekly_stats(self, weeks_back: int = 1) -> Dict[str, Any]:
        """Compute statistics for the last N weeks.
        
        Args:
            weeks_back: Number of weeks to look back
            
        Returns:
            Dict with weekly statistics
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=7 * weeks_back)
        
        # Get all logs in time window
        cursor = self.store.conn.cursor()
        cursor.execute("""
            SELECT * FROM habit_log
            WHERE logged_at >= ? AND logged_at <= ?
            ORDER BY logged_at DESC
        """, (
            datetime.combine(start_date, datetime.min.time()).isoformat(),
            datetime.combine(end_date, datetime.max.time()).isoformat()
        ))
        
        logs = cursor.fetchall()
        
        # Count by habit
        habit_counter = Counter()
        days_active = set()
        
        for log in logs:
            habit_key = log[1]
            logged_at = datetime.fromisoformat(log[4])
            
            habit_counter[habit_key] += 1
            days_active.add(logged_at.date())
        
        # Get streaks and adherence for each habit
        habit_details = {}
        for habit_key in habit_counter.keys():
            from .skills import HabitStats
            stats = HabitStats(habit_key, self.store).compute()
            habit_details[habit_key] = {
                "count": habit_counter[habit_key],
                "streak": stats["current_streak"],
                "adherence_7d": stats["adherence_7d"]
            }
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days + 1
            },
            "total_logs": len(logs),
            "unique_habits": len(habit_counter),
            "days_active": len(days_active),
            "habits": habit_details,
            "most_logged": habit_counter.most_common(3)
        }
    
    def execute(self, weeks_back: int = 1) -> Dict[str, Any]:
        """Execute weekly review.
        
        Args:
            weeks_back: Number of weeks to review
            
        Returns:
            Review results with summary
        """
        stats = self.compute_weekly_stats(weeks_back)
        profile = self.store.get_profile()
        constraints = self.store.get_active_constraints()
        
        # Build text summary
        summary_parts = [
            f"Weekly Review ({stats['period']['start']} to {stats['period']['end']})",
            f"",
            f"Total logs: {stats['total_logs']}",
            f"Unique habits tracked: {stats['unique_habits']}",
            f"Days active: {stats['days_active']} / {stats['period']['days']}",
            f""
        ]
        
        if stats['most_logged']:
            summary_parts.append("Top habits:")
            for habit_key, count in stats['most_logged']:
                detail = stats['habits'].get(habit_key, {})
                streak = detail.get('streak', 0)
                adherence = detail.get('adherence_7d', 0)
                summary_parts.append(f"  - {habit_key}: {count} logs, {streak}-day streak, {adherence}% adherence")
            summary_parts.append("")
        
        if constraints:
            summary_parts.append(f"Active constraints: {len(constraints)}")
            for constraint in constraints[:3]:  # Show first 3
                summary_parts.append(f"  - {constraint.rule_text}")
            summary_parts.append("")
        
        summary = "\n".join(summary_parts)
        
        # Optional LLM synthesis
        llm_insights = None
        if self.llm:
            try:
                context = f"""Weekly review data:
{summary}

User profile: {json.dumps(profile.__dict__ if profile else {}, default=str)}

Provide 2-3 sentences of encouraging insights and suggestions."""
                
                from .llm import NebiusClient
                insights = self.llm.ask(context, max_tokens=200)
                llm_insights = insights
                summary += f"\n\n💡 Insights:\n{insights}"
                summary += "\n\n⚠️ This is NOT medical advice. These are general observations only."
            except Exception:
                pass
        
        return {
            "success": True,
            "stats": stats,
            "summary": summary,
            "llm_insights": llm_insights,
            "llm_available": self.llm is not None
        }
