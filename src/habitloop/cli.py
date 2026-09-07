"""Command-line interface for HabitLoop Steward."""

import typer
from typing import Optional
from datetime import datetime, date
from pathlib import Path
import json
import os

from .memory import MemoryStore
from .llm import NebiusClient
from .skills import DailyNudgeSkill, PlanAdjustSkill, HabitStats
from .loop import (LoopRuntime, Proposal, VerificationResult, 
                   demo_bad_proposal, demo_quiet_hours_proposal, demo_good_proposal)
from .jobs import NightlyReviewJob, MorningBriefJob, NebiusJobScheduler
from .learning import ConstraintLearner, WeeklyReviewSkill

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


@app.command()
def nudge():
    """Get a daily motivation nudge."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        skill = DailyNudgeSkill(store, llm)
        result = skill.execute()
        
        typer.echo()
        typer.secho("💪 Daily Nudge", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo(result.message)
        typer.echo()
        
        if not result.data.get("llm_available", True):
            typer.secho("(Using offline mode - set NEBIUS_API_KEY for AI-powered nudges)", 
                       fg=typer.colors.YELLOW, dim=True)
    finally:
        store.close()


@app.command("plan-adjust")
def plan_adjust(
    habit_key: Optional[str] = typer.Argument(None, help="Specific habit to analyze")
):
    """Get plan adjustment suggestions based on adherence patterns."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        skill = PlanAdjustSkill(store, llm)
        result = skill.execute(habit_key=habit_key)
        
        typer.echo()
        typer.secho("📋 Plan Adjustment", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo(result.message)
        typer.echo()
    finally:
        store.close()


@app.command()
def stats(
    habit_key: Optional[str] = typer.Argument(None, help="Specific habit to show stats for")
):
    """Show habit statistics (streak, adherence, etc.)."""
    store = MemoryStore(get_db_path())
    
    try:
        if habit_key:
            habits = [habit_key]
        else:
            all_logs = store.get_logs_by_habit("dummy", limit=1)
            cursor = store.conn.cursor()
            cursor.execute("SELECT DISTINCT habit_key FROM habit_log ORDER BY habit_key")
            habits = [row[0] for row in cursor.fetchall()]
        
        if not habits:
            typer.echo("No habits logged yet.")
            return
        
        typer.echo()
        typer.secho("📊 Habit Statistics", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        
        for hkey in habits:
            stats_obj = HabitStats(hkey, store)
            stats_data = stats_obj.compute()
            
            if stats_data["total_logs"] == 0:
                continue
            
            typer.secho(f"  {hkey}", fg=typer.colors.GREEN, bold=True)
            typer.echo(f"    Total logs: {stats_data['total_logs']}")
            typer.echo(f"    Current streak: {stats_data['current_streak']} days")
            typer.echo(f"    Adherence (7d): {stats_data['adherence_7d']}%")
            typer.echo(f"    Adherence (30d): {stats_data['adherence_30d']}%")
            if stats_data['last_logged']:
                last = datetime.fromisoformat(stats_data['last_logged'])
                typer.echo(f"    Last logged: {last.strftime('%Y-%m-%d %H:%M')}")
            typer.echo()
    finally:
        store.close()


@app.command("run-loop")
def run_loop(
    proposal_json: str = typer.Argument(..., help="Proposal JSON string"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed history")
):
    """Run the propose→verify→correct loop on a proposal."""
    store = MemoryStore(get_db_path())
    
    try:
        proposal_data = json.loads(proposal_json)
        proposal = Proposal(
            proposal_type=proposal_data.get("proposal_type", "habit_log"),
            data=proposal_data.get("data", {}),
            metadata=proposal_data.get("metadata", {})
        )
        
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        runtime = LoopRuntime(store, llm)
        result = runtime.run_loop(proposal)
        
        typer.echo()
        typer.secho("🔄 Loop Runtime Result", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        
        status_color = {
            "success": typer.colors.GREEN,
            "success_with_warnings": typer.colors.YELLOW,
            "escalated": typer.colors.RED,
            "failed": typer.colors.RED
        }.get(result["status"], typer.colors.WHITE)
        
        typer.secho(f"Status: {result['status']}", fg=status_color, bold=True)
        typer.echo(f"Attempts: {result['attempts']}")
        typer.echo(f"Result: {result.get('result', 'N/A')}")
        
        if "warnings" in result:
            typer.echo()
            typer.secho("Warnings:", fg=typer.colors.YELLOW)
            for warning in result["warnings"]:
                typer.echo(f"  - {warning['message']}")
        
        if "issues" in result:
            typer.echo()
            typer.secho("Issues:", fg=typer.colors.RED)
            for issue in result["issues"]:
                typer.echo(f"  - [{issue['severity']}] {issue['message']}")
        
        if verbose and "history" in result:
            typer.echo()
            typer.secho("History:", fg=typer.colors.CYAN)
            typer.echo(json.dumps(result["history"], indent=2))
        
        typer.echo()
        
    except json.JSONDecodeError as e:
        typer.secho(f"✗ Invalid JSON: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    finally:
        store.close()


@app.command("verify-demo")
def verify_demo():
    """Run demo scenarios showing the verification gate in action."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        runtime = LoopRuntime(store, llm)
        
        typer.echo()
        typer.secho("🎬 Verification Demo", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo("Running three demo scenarios:")
        typer.echo()
        
        # Scenario 1: Bad proposal (RED)
        typer.secho("Scenario 1: Bad Proposal (missing required field)", fg=typer.colors.YELLOW, bold=True)
        bad_proposal = demo_bad_proposal()
        result1 = runtime.run_loop(bad_proposal)
        typer.echo(f"  Status: {result1['status']}")
        typer.echo(f"  Result: {result1.get('result', 'N/A')}")
        if "issues" in result1:
            for issue in result1["issues"]:
                typer.secho(f"  ❌ {issue['message']}", fg=typer.colors.RED)
        typer.echo()
        
        # Scenario 2: Quiet hours (YELLOW)
        typer.secho("Scenario 2: Quiet Hours Check", fg=typer.colors.YELLOW, bold=True)
        quiet_proposal = demo_quiet_hours_proposal()
        result2 = runtime.run_loop(quiet_proposal)
        typer.echo(f"  Status: {result2['status']}")
        typer.echo(f"  Result: {result2.get('result', 'N/A')}")
        if "warnings" in result2:
            for warning in result2["warnings"]:
                typer.secho(f"  ⚠️  {warning['message']}", fg=typer.colors.YELLOW)
        elif result2['status'] == 'success':
            typer.secho(f"  ✓ No quiet hours configured or outside quiet hours", fg=typer.colors.GREEN)
        typer.echo()
        
        # Scenario 3: Good proposal (GREEN)
        typer.secho("Scenario 3: Valid Proposal", fg=typer.colors.YELLOW, bold=True)
        good_proposal = demo_good_proposal()
        result3 = runtime.run_loop(good_proposal)
        typer.echo(f"  Status: {result3['status']}")
        typer.echo(f"  Result: {result3.get('result', 'N/A')}")
        if result3['status'] == 'success':
            typer.secho(f"  ✓ All checks passed", fg=typer.colors.GREEN)
        typer.echo()
        
        typer.secho("Demo complete! The loop runtime can:", fg=typer.colors.CYAN)
        typer.echo("  • Detect schema violations (RED gate)")
        typer.echo("  • Check quiet hours (YELLOW gate)")
        typer.echo("  • Validate against constraints")
        typer.echo("  • Escalate when auto-correction fails")
        typer.echo()
        
    finally:
        store.close()


job_app = typer.Typer(help="Serverless job commands")
app.add_typer(job_app, name="job")


@job_app.command("nightly")
def job_nightly(
    target_date: Optional[str] = typer.Option(None, "--date", "-d", help="Target date (YYYY-MM-DD)")
):
    """Run nightly review job locally."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        parsed_date = None
        if target_date:
            parsed_date = datetime.fromisoformat(target_date).date()
        
        job = NightlyReviewJob(store, llm)
        result = job.execute(target_date=parsed_date)
        
        typer.echo()
        typer.secho("🌙 Nightly Review", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo(result.data["summary"])
        typer.echo()
        
        if llm is None:
            typer.secho("(Using offline mode - set NEBIUS_API_KEY for AI-powered insights)", 
                       fg=typer.colors.YELLOW, dim=True)
        
    finally:
        store.close()


@job_app.command("morning")
def job_morning():
    """Run morning brief job locally."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        job = MorningBriefJob(store, llm)
        result = job.execute()
        
        typer.echo()
        typer.secho("☀️ Morning Brief", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo(result.data["brief"])
        typer.echo()
        
        if llm is None:
            typer.secho("(Using offline mode - set NEBIUS_API_KEY for AI-powered motivation)", 
                       fg=typer.colors.YELLOW, dim=True)
        
    finally:
        store.close()


@job_app.command("deploy-info")
def job_deploy_info():
    """Show instructions for deploying jobs to Nebius Serverless."""
    typer.echo(NebiusJobScheduler.get_deployment_instructions())


@app.command("learn-constraints")
def learn_constraints():
    """Run constraint learning cycle to detect patterns and create rules."""
    store = MemoryStore(get_db_path())
    
    try:
        learner = ConstraintLearner(store)
        result = learner.run_learning_cycle()
        
        typer.echo()
        typer.secho("🧠 Constraint Learning", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo(f"Patterns detected: {result['patterns_detected']}")
        typer.echo(f"New constraints created: {result['constraints_created']}")
        typer.echo()
        
        if result['new_constraints']:
            typer.secho("New constraints:", fg=typer.colors.GREEN)
            for constraint_text in result['new_constraints']:
                typer.echo(f"  ✓ {constraint_text}")
            typer.echo()
        else:
            typer.echo("No new constraints needed at this time.")
            typer.echo()
        
        if result['patterns_detected'] > 0 and result['constraints_created'] == 0:
            typer.secho("Note: Patterns detected but constraints already exist.", 
                       fg=typer.colors.YELLOW, dim=True)
            typer.echo()
    
    finally:
        store.close()


@app.command("constraints")
def show_constraints():
    """Show all active constraints."""
    store = MemoryStore(get_db_path())
    
    try:
        constraints = store.get_active_constraints()
        
        typer.echo()
        typer.secho("📋 Active Constraints", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        
        if not constraints:
            typer.echo("No active constraints yet.")
            typer.echo()
            return
        
        for constraint in constraints:
            source_icon = "🤖" if constraint.source == "learned" else "👤"
            typer.secho(f"{source_icon} #{constraint.id}", fg=typer.colors.YELLOW, bold=True)
            typer.echo(f"   {constraint.rule_text}")
            typer.echo(f"   Source: {constraint.source} | Created: {constraint.created_at.strftime('%Y-%m-%d')}")
            typer.echo()
    
    finally:
        store.close()


@app.command("weekly-review")
def weekly_review(
    weeks: int = typer.Option(1, "--weeks", "-w", help="Number of weeks to review")
):
    """Generate weekly review with statistics and insights."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = None
        try:
            llm = NebiusClient()
        except ValueError:
            pass
        
        skill = WeeklyReviewSkill(store, llm)
        result = skill.execute(weeks_back=weeks)
        
        typer.echo()
        typer.secho("📈 Weekly Review", fg=typer.colors.CYAN, bold=True)
        typer.echo()
        typer.echo(result["summary"])
        typer.echo()
        
        if not result.get("llm_available", False):
            typer.secho("(Using offline mode - set NEBIUS_API_KEY for AI-powered insights)", 
                       fg=typer.colors.YELLOW, dim=True)
    
    finally:
        store.close()


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload")
):
    """Start the web UI server."""
    import uvicorn
    
    typer.echo()
    typer.secho("🌐 Starting HabitLoop Steward Web UI", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"   Server: http://{host}:{port}")
    typer.echo()
    typer.secho("⚠️  This is NOT medical advice. For health concerns, consult professionals.", 
               fg=typer.colors.YELLOW)
    typer.echo()
    
    uvicorn.run(
        "habitloop.web:app",
        host=host,
        port=port,
        reload=reload
    )


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
