"""Command-line interface for HabitLoop Steward."""

import typer
from typing import Optional
from datetime import datetime, date
from pathlib import Path
import json
import os

from .memory import MemoryStore
from .llm import NebiusClient

app = typer.Typer(
    name="habit",
    help="HabitLoop Steward - Personal AI habit tracking assistant"
)


def get_db_path() -> str:
    """Get database path from env or default."""
    return os.getenv("HABITLOOP_DB", "habitloop.db")


@app.command()
def log(
    habit_key: str,
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Habit value"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Optional note")
):
    """Log a habit entry."""
    store = MemoryStore(get_db_path())
    
    try:
        entry = store.log_habit(habit_key, value=value, note=note)
        typer.secho(f"✓ Logged {habit_key}", fg=typer.colors.GREEN)
        
        if value:
            typer.echo(f"  Value: {value}")
        if note:
            typer.echo(f"  Note: {note}")
        
        typer.echo(f"  Time: {entry.logged_at.strftime('%Y-%m-%d %H:%M:%S')}")
    finally:
        store.close()


@app.command()
def today():
    """Show today's habit logs."""
    store = MemoryStore(get_db_path())
    
    try:
        logs = store.get_logs_for_date(date.today())
        
        if not logs:
            typer.echo("No habits logged today yet.")
            return
        
        typer.secho(f"\n📊 Today's Habits ({date.today().strftime('%Y-%m-%d')})", 
                   fg=typer.colors.CYAN, bold=True)
        typer.echo()
        
        for entry in logs:
            time_str = entry.logged_at.strftime('%H:%M')
            typer.echo(f"  {time_str} - {entry.habit_key}")
            
            if entry.value:
                typer.echo(f"           Value: {entry.value}")
            if entry.note:
                typer.echo(f"           Note: {entry.note}")
            typer.echo()
    finally:
        store.close()


profile_app = typer.Typer(help="Manage user profile")
app.add_typer(profile_app, name="profile")


@profile_app.command("show")
def profile_show():
    """Show current profile."""
    store = MemoryStore(get_db_path())
    
    try:
        profile = store.get_profile()
        
        if not profile:
            typer.echo("No profile set. Use 'habit profile set' to create one.")
            return
        
        typer.secho("\n👤 Profile", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"  Timezone: {profile.timezone}")
        typer.echo(f"  Goals: {json.dumps(profile.goals, indent=2)}")
        typer.echo(f"  Quiet Hours: {json.dumps(profile.quiet_hours, indent=2)}")
        typer.echo(f"  Preferences: {json.dumps(profile.preferences, indent=2)}")
        typer.echo(f"  Updated: {profile.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    finally:
        store.close()


@profile_app.command("set")
def profile_set(
    timezone: str = typer.Option("UTC", "--timezone", "-tz", help="User timezone"),
    goals: Optional[str] = typer.Option(None, "--goals", "-g", help="Goals as JSON"),
    quiet_hours: Optional[str] = typer.Option(None, "--quiet-hours", "-q", help="Quiet hours as JSON"),
    preferences: Optional[str] = typer.Option(None, "--preferences", "-p", help="Preferences as JSON")
):
    """Set or update profile."""
    store = MemoryStore(get_db_path())
    
    try:
        goals_dict = json.loads(goals) if goals else {}
        quiet_dict = json.loads(quiet_hours) if quiet_hours else {}
        pref_dict = json.loads(preferences) if preferences else {}
        
        profile = store.upsert_profile(
            timezone=timezone,
            goals=goals_dict,
            quiet_hours=quiet_dict,
            preferences=pref_dict
        )
        
        typer.secho("✓ Profile updated", fg=typer.colors.GREEN)
    except json.JSONDecodeError as e:
        typer.secho(f"✗ Invalid JSON: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    finally:
        store.close()


@app.command()
def ask(question: str):
    """Ask the AI assistant a question."""
    try:
        client = NebiusClient()
    except ValueError as e:
        typer.secho(f"✗ {e}", fg=typer.colors.RED, err=True)
        typer.echo("\nSet NEBIUS_API_KEY environment variable or add it to .env file.")
        raise typer.Exit(1)
    
    store = MemoryStore(get_db_path())
    
    try:
        profile = store.get_profile()
        recent_logs = store.get_logs_for_date(date.today())
        
        context_parts = []
        
        if profile:
            context_parts.append(f"User timezone: {profile.timezone}")
            if profile.goals:
                context_parts.append(f"Goals: {json.dumps(profile.goals)}")
        
        if recent_logs:
            logs_summary = "\n".join([
                f"- {log.habit_key}" + (f" ({log.value})" if log.value else "")
                for log in recent_logs
            ])
            context_parts.append(f"Today's habits:\n{logs_summary}")
        
        context = "\n\n".join(context_parts) if context_parts else None
        
        typer.echo()
        with typer.progressbar(length=1, label="Thinking") as progress:
            response = client.ask(question, context=context)
            progress.update(1)
        
        typer.echo()
        typer.secho("🤖 Assistant:", fg=typer.colors.CYAN, bold=True)
        typer.echo(response)
        typer.echo()
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    finally:
        store.close()


@app.command("ping-model")
def ping_model():
    """Test connection to Nebius Token Factory."""
    try:
        client = NebiusClient()
    except ValueError as e:
        typer.secho(f"✗ {e}", fg=typer.colors.RED, err=True)
        typer.echo("\nSet NEBIUS_API_KEY environment variable or add it to .env file.")
        raise typer.Exit(1)
    
    typer.echo(f"Testing connection to {client.model}...")
    typer.echo()
    
    result = client.ping()
    
    if result["status"] == "success":
        typer.secho("✓ Connection successful!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Model: {result['model']}")
        typer.echo(f"  Response: {result['response']}")
        typer.echo(f"  Tokens used: {result['usage']['total_tokens']}")
    else:
        typer.secho(f"✗ Connection failed", fg=typer.colors.RED, bold=True, err=True)
        typer.echo(f"  Error: {result['error']}", err=True)
        raise typer.Exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
