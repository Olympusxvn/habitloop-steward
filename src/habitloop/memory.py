"""SQLite memory storage for HabitLoop Steward."""

import sqlite3
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import json

from .models import Profile, HabitLog, Constraint


class MemoryStore:
    """SQLite-backed memory store for habit tracking."""

    def __init__(self, db_path: str = "habitloop.db"):
        """Initialize memory store with SQLite database."""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY,
                timezone TEXT NOT NULL,
                goals TEXT NOT NULL,
                quiet_hours TEXT NOT NULL,
                preferences TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_key TEXT NOT NULL,
                value TEXT,
                note TEXT,
                logged_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS constraints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_text TEXT NOT NULL,
                source TEXT NOT NULL,
                active INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_habit_log_key_date 
            ON habit_log(habit_key, logged_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_constraints_active 
            ON constraints(active)
        """)
        
        self.conn.commit()

    def get_profile(self) -> Optional[Profile]:
        """Get user profile (single row)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM profile WHERE id = 1")
        row = cursor.fetchone()
        return Profile.from_row(row) if row else None

    def upsert_profile(
        self,
        timezone: str = "UTC",
        goals: Optional[Dict[str, Any]] = None,
        quiet_hours: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Profile:
        """Create or update user profile."""
        cursor = self.conn.cursor()
        
        goals = goals or {}
        quiet_hours = quiet_hours or {}
        preferences = preferences or {}
        updated_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO profile (id, timezone, goals, quiet_hours, preferences, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                timezone = excluded.timezone,
                goals = excluded.goals,
                quiet_hours = excluded.quiet_hours,
                preferences = excluded.preferences,
                updated_at = excluded.updated_at
        """, (
            timezone,
            json.dumps(goals),
            json.dumps(quiet_hours),
            json.dumps(preferences),
            updated_at
        ))
        
        self.conn.commit()
        return self.get_profile()

    def log_habit(
        self,
        habit_key: str,
        value: Optional[str] = None,
        note: Optional[str] = None,
        logged_at: Optional[datetime] = None,
        source: str = "cli"
    ) -> HabitLog:
        """Log a habit entry."""
        cursor = self.conn.cursor()
        
        if logged_at is None:
            logged_at = datetime.utcnow()
        
        cursor.execute("""
            INSERT INTO habit_log (habit_key, value, note, logged_at, source)
            VALUES (?, ?, ?, ?, ?)
        """, (habit_key, value, note, logged_at.isoformat(), source))
        
        self.conn.commit()
        
        log_id = cursor.lastrowid
        return HabitLog(
            id=log_id,
            habit_key=habit_key,
            value=value,
            note=note,
            logged_at=logged_at,
            source=source
        )

    def get_logs_for_date(self, target_date: date) -> List[HabitLog]:
        """Get all habit logs for a specific date."""
        cursor = self.conn.cursor()
        
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        
        cursor.execute("""
            SELECT * FROM habit_log
            WHERE logged_at >= ? AND logged_at <= ?
            ORDER BY logged_at DESC
        """, (start, end))
        
        return [HabitLog.from_row(row) for row in cursor.fetchall()]

    def get_logs_by_habit(self, habit_key: str, limit: int = 10) -> List[HabitLog]:
        """Get recent logs for a specific habit."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM habit_log
            WHERE habit_key = ?
            ORDER BY logged_at DESC
            LIMIT ?
        """, (habit_key, limit))
        
        return [HabitLog.from_row(row) for row in cursor.fetchall()]

    def add_constraint(
        self,
        rule_text: str,
        source: str = "user",
        active: bool = True
    ) -> Constraint:
        """Add a new constraint."""
        cursor = self.conn.cursor()
        created_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO constraints (rule_text, source, active, created_at)
            VALUES (?, ?, ?, ?)
        """, (rule_text, source, int(active), created_at))
        
        self.conn.commit()
        
        constraint_id = cursor.lastrowid
        return Constraint(
            id=constraint_id,
            rule_text=rule_text,
            source=source,
            active=active,
            created_at=datetime.fromisoformat(created_at)
        )

    def get_active_constraints(self) -> List[Constraint]:
        """Get all active constraints."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM constraints
            WHERE active = 1
            ORDER BY created_at DESC
        """)
        
        return [Constraint.from_row(row) for row in cursor.fetchall()]

    def deactivate_constraint(self, constraint_id: int):
        """Deactivate a constraint."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE constraints
            SET active = 0
            WHERE id = ?
        """, (constraint_id,))
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
