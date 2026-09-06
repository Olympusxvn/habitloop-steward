"""Data models for HabitLoop Steward."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class Profile:
    """User profile with timezone, goals, quiet hours, and preferences."""
    id: int
    timezone: str
    goals: Dict[str, Any]
    quiet_hours: Dict[str, Any]
    preferences: Dict[str, Any]
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Profile":
        """Create Profile from database row."""
        return cls(
            id=row[0],
            timezone=row[1],
            goals=json.loads(row[2]),
            quiet_hours=json.loads(row[3]),
            preferences=json.loads(row[4]),
            updated_at=datetime.fromisoformat(row[5])
        )


@dataclass
class HabitLog:
    """A single habit log entry."""
    id: Optional[int]
    habit_key: str
    value: Optional[str]
    note: Optional[str]
    logged_at: datetime
    source: str

    @classmethod
    def from_row(cls, row: tuple) -> "HabitLog":
        """Create HabitLog from database row."""
        return cls(
            id=row[0],
            habit_key=row[1],
            value=row[2],
            note=row[3],
            logged_at=datetime.fromisoformat(row[4]),
            source=row[5]
        )


@dataclass
class Constraint:
    """A constraint or rule for habit tracking."""
    id: Optional[int]
    rule_text: str
    source: str
    active: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Constraint":
        """Create Constraint from database row."""
        return cls(
            id=row[0],
            rule_text=row[1],
            source=row[2],
            active=bool(row[3]),
            created_at=datetime.fromisoformat(row[4])
        )
