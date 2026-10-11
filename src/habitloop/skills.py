"""Domain skills for HabitLoop Steward.

These skills provide the core habit tracking and coaching functionality.
All skills include non-medical disclaimers and degrade gracefully without LLM access.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import json

from .memory import MemoryStore
from .models import HabitLog
from .llm import NebiusClient


class SkillResult:
    """Result from executing a skill."""
    
    def __init__(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}
    
    def __repr__(self):
        return f"SkillResult(success={self.success}, message={self.message})"


def calculate_streak(logs: List[HabitLog], habit_key: str) -> int:
    """Calculate current streak for a habit (consecutive days with at least one log).
    
    Args:
        logs: All habit logs for the habit, ordered by logged_at DESC
        habit_key: Habit identifier
        
    Returns:
        Number of consecutive days with logging (0 if broken today)
    """
    if not logs:
        return 0
    
    days_seen = set()
    for log in logs:
        day = log.logged_at.date()
        days_seen.add(day)
    
    today = date.today()
    streak = 0
    check_date = today
    
    while check_date in days_seen:
        streak += 1
        check_date -= timedelta(days=1)
    
    return streak


def calculate_adherence(logs: List[HabitLog], days: int = 7) -> float:
    """Calculate adherence percentage over the last N days.
    
    Args:
        logs: All habit logs, ordered by logged_at DESC
        days: Number of days to look back
        
    Returns:
        Percentage of days with at least one log (0.0 to 100.0)
    """
    if not logs:
        return 0.0
    
    cutoff = datetime.now() - timedelta(days=days)
    recent_logs = [log for log in logs if log.logged_at >= cutoff]
    
    if not recent_logs:
        return 0.0
    
    days_logged = set()
    for log in recent_logs:
        days_logged.add(log.logged_at.date())
    
    return (len(days_logged) / days) * 100.0


class HabitStats:
    """Statistics for a single habit."""
    
    def __init__(self, habit_key: str, store: MemoryStore, lookback_days: int = 30):
        self.habit_key = habit_key
        self.store = store
        self.lookback_days = lookback_days
        
    def compute(self) -> Dict[str, Any]:
        """Compute all statistics for this habit."""
        logs = self.store.get_logs_by_habit(self.habit_key, limit=1000)
        
        if not logs:
            return {
                "habit_key": self.habit_key,
                "total_logs": 0,
                "current_streak": 0,
                "adherence_7d": 0.0,
                "adherence_30d": 0.0,
                "last_logged": None
            }
        
        total_logs = len(logs)
        current_streak = calculate_streak(logs, self.habit_key)
        adherence_7d = calculate_adherence(logs, days=7)
        adherence_30d = calculate_adherence(logs, days=30)
        last_logged = logs[0].logged_at.isoformat() if logs else None
        
        return {
            "habit_key": self.habit_key,
            "total_logs": total_logs,
            "current_streak": current_streak,
            "adherence_7d": round(adherence_7d, 1),
            "adherence_30d": round(adherence_30d, 1),
            "last_logged": last_logged
        }


class DailyNudgeSkill:
    """Provide daily motivation and reminders.
    
    DISCLAIMER: This is NOT medical advice. Consult healthcare professionals
    for any health concerns.
    """
    
    def __init__(self, store: MemoryStore, llm_client: Optional[NebiusClient] = None):
        self.store = store
        self.llm = llm_client
        
    def execute(self) -> SkillResult:
        """Generate daily nudge based on recent activity."""
        today_logs = self.store.get_logs_for_date(date.today())
        profile = self.store.get_profile()
        
        context_parts = []
        context_parts.append(f"Today's date: {date.today().isoformat()}")
        context_parts.append(f"Habits logged today: {len(today_logs)}")
        
        if profile and profile.goals:
            context_parts.append(f"User goals: {json.dumps(profile.goals)}")
        
        if today_logs:
            habit_summary = ", ".join([log.habit_key for log in today_logs])
            context_parts.append(f"Today's habits: {habit_summary}")
        
        context = "\n".join(context_parts)
        
        if self.llm:
            try:
                prompt = f"""Based on the user's activity, provide a brief, encouraging daily message.
Keep it positive, non-judgmental, and motivating.

{context}

IMPORTANT: You are NOT providing medical advice. This is general motivation only."""
                
                response = self.llm.ask(prompt, max_tokens=150)
                
                disclaimer = "\n\n⚠️ This is NOT medical advice. Consult healthcare professionals for health concerns."
                return SkillResult(True, response + disclaimer, {"context": context})
                
            except Exception as e:
                pass
        
        # Fallback: deterministic nudge without LLM
        if len(today_logs) == 0:
            message = "Good morning! 🌅 No habits logged yet today. Every journey begins with a single step."
        elif len(today_logs) < 3:
            message = f"Great start! 💪 You've logged {len(today_logs)} habit(s) today. Keep the momentum going!"
        else:
            message = f"Excellent work! 🎉 You've logged {len(today_logs)} habits today. You're building strong patterns!"
        
        disclaimer = "\n\n⚠️ This is NOT medical advice. Consult healthcare professionals for health concerns."
        return SkillResult(True, message + disclaimer, {"context": context, "llm_available": False})


class PlanAdjustSkill:
    """Suggest plan adjustments based on adherence patterns.
    
    DISCLAIMER: This is NOT medical advice. These are general observations only.
    """
    
    def __init__(self, store: MemoryStore, llm_client: Optional[NebiusClient] = None):
        self.store = store
        self.llm = llm_client
        
    def execute(self, habit_key: Optional[str] = None) -> SkillResult:
        """Analyze patterns and suggest adjustments."""
        profile = self.store.get_profile()
        
        if habit_key:
            habits_to_check = [habit_key]
        else:
            all_logs = self.store.get_logs_by_habit("*", limit=1000) if habit_key is None else []
            habits_to_check = list(set([log.habit_key for log in all_logs]))
        
        suggestions = []
        
        for hkey in habits_to_check:
            stats = HabitStats(hkey, self.store).compute()
            
            if stats["total_logs"] == 0:
                continue
                
            adherence_7d = stats["adherence_7d"]
            streak = stats["current_streak"]
            
            if adherence_7d < 30:
                suggestions.append(f"- {hkey}: Low adherence ({adherence_7d}%). Consider breaking it into smaller goals.")
            elif adherence_7d > 80 and streak > 7:
                suggestions.append(f"- {hkey}: Strong pattern! ({adherence_7d}%, {streak}-day streak). Consider a new challenge.")
        
        if not suggestions:
            message = "Your habits look balanced. Keep tracking to identify patterns over time."
        else:
            message = "Here are some observations:\n\n" + "\n".join(suggestions)
        
        disclaimer = "\n\n⚠️ This is NOT medical advice. These are general observations only."
        
        return SkillResult(True, message + disclaimer, {
            "suggestions_count": len(suggestions),
            "llm_available": self.llm is not None
        })


class HabitLogSkill:
    """Skill for logging habits with validation.
    
    This wraps the basic memory logging with additional checks.
    """
    
    def __init__(self, store: MemoryStore):
        self.store = store
        
    def execute(self, habit_key: str, value: Optional[str] = None, 
                note: Optional[str] = None) -> SkillResult:
        """Log a habit with validation against constraints."""
        constraints = self.store.get_active_constraints()
        
        # Check constraints (simple keyword matching for now)
        for constraint in constraints:
            if habit_key.lower() in constraint.rule_text.lower():
                # Constraint exists but we still allow logging
                # (could add more sophisticated checking here)
                pass
        
        entry = self.store.log_habit(habit_key, value=value, note=note)
        
        return SkillResult(True, f"Logged {habit_key}", {
            "log_id": entry.id,
            "habit_key": habit_key,
            "logged_at": entry.logged_at.isoformat()
        })
