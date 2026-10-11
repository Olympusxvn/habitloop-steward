"""Serverless job management for HabitLoop Steward.

Supports both Nebius Serverless Jobs (when deployed) and local execution for testing.
Jobs can be nightly reviews, morning briefs, or other scheduled tasks.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
import json

from .memory import MemoryStore
from .llm import NebiusClient
from .skills import HabitStats, calculate_streak, calculate_adherence


class JobResult:
    """Result from job execution."""
    
    def __init__(self, job_type: str, success: bool, data: Dict[str, Any], 
                 message: Optional[str] = None):
        self.job_type = job_type
        self.success = success
        self.data = data
        self.message = message
        self.executed_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "job_type": self.job_type,
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "executed_at": self.executed_at.isoformat()
        }


class NightlyReviewJob:
    """Nightly review job: analyzes the day's habits and prepares insights.
    
    This job can run:
    - As a Nebius Serverless Job (scheduled cron)
    - Locally via CLI for testing
    
    DISCLAIMER: This is NOT medical advice. These are data observations only.
    """
    
    def __init__(self, store: MemoryStore, llm_client: Optional[NebiusClient] = None):
        self.store = store
        self.llm = llm_client
        
    def execute(self, target_date: Optional[date] = None) -> JobResult:
        """Execute nightly review for a specific date.
        
        Args:
            target_date: Date to review (defaults to today)
            
        Returns:
            JobResult with review data
        """
        if target_date is None:
            target_date = date.today()
        
        logs = self.store.get_logs_for_date(target_date)
        profile = self.store.get_profile()
        
        # Compute stats
        habits_logged = list(set([log.habit_key for log in logs]))
        total_logs = len(logs)
        
        habit_stats = {}
        for habit_key in habits_logged:
            stats = HabitStats(habit_key, self.store).compute()
            habit_stats[habit_key] = stats
        
        # Build summary
        summary_parts = [
            f"Nightly Review for {target_date.isoformat()}",
            f"",
            f"Habits logged: {len(habits_logged)}",
            f"Total log entries: {total_logs}",
            f""
        ]
        
        if habit_stats:
            summary_parts.append("Habit Details:")
            for habit_key, stats in habit_stats.items():
                summary_parts.append(f"  - {habit_key}:")
                summary_parts.append(f"    Streak: {stats['current_streak']} days")
                summary_parts.append(f"    7-day adherence: {stats['adherence_7d']}%")
        
        summary = "\n".join(summary_parts)
        
        # Optional LLM synthesis
        if self.llm:
            try:
                context = f"""Today's activity summary:
{summary}

User profile: {json.dumps(profile.to_dict() if profile else {}, default=str)}

Provide a brief, encouraging nightly reflection (2-3 sentences)."""
                
                reflection = self.llm.ask(context, max_tokens=150)
                summary += f"\n\n💭 Reflection:\n{reflection}"
                summary += "\n\n⚠️ This is NOT medical advice."
            except Exception:
                pass
        
        data = {
            "date": target_date.isoformat(),
            "habits_logged": habits_logged,
            "total_logs": total_logs,
            "habit_stats": habit_stats,
            "summary": summary
        }
        
        return JobResult(
            job_type="nightly_review",
            success=True,
            data=data,
            message="Nightly review completed"
        )


class MorningBriefJob:
    """Morning brief job: provides daily goals and reminders.
    
    DISCLAIMER: This is NOT medical advice. These are personalized reminders only.
    """
    
    def __init__(self, store: MemoryStore, llm_client: Optional[NebiusClient] = None):
        self.store = store
        self.llm = llm_client
        
    def execute(self) -> JobResult:
        """Execute morning brief."""
        profile = self.store.get_profile()
        yesterday = date.today() - timedelta(days=1)
        yesterday_logs = self.store.get_logs_for_date(yesterday)
        
        brief_parts = [
            f"Morning Brief for {date.today().isoformat()}",
            f""
        ]
        
        if profile and profile.goals:
            brief_parts.append("Your goals:")
            for goal_key, goal_value in profile.goals.items():
                brief_parts.append(f"  - {goal_key}: {goal_value}")
            brief_parts.append("")
        
        if yesterday_logs:
            brief_parts.append(f"Yesterday you logged {len(yesterday_logs)} habit(s):")
            habits = list(set([log.habit_key for log in yesterday_logs]))
            for habit in habits:
                brief_parts.append(f"  ✓ {habit}")
        else:
            brief_parts.append("No habits logged yesterday.")
        
        brief = "\n".join(brief_parts)
        
        # Optional LLM synthesis
        if self.llm:
            try:
                context = f"""Morning brief context:
{brief}

Provide a brief, motivating morning message (2-3 sentences)."""
                
                motivation = self.llm.ask(context, max_tokens=150)
                brief += f"\n\n💪 Motivation:\n{motivation}"
                brief += "\n\n⚠️ This is NOT medical advice."
            except Exception:
                pass
        
        data = {
            "date": date.today().isoformat(),
            "brief": brief
        }
        
        return JobResult(
            job_type="morning_brief",
            success=True,
            data=data,
            message="Morning brief completed"
        )


class NebiusJobScheduler:
    """Skeleton for Nebius Serverless Jobs integration.
    
    This class provides the configuration and deployment structure.
    Actual deployment requires Nebius credentials and setup.
    """
    
    @staticmethod
    def generate_job_config(job_type: str, schedule: str = "0 0 * * *") -> Dict[str, Any]:
        """Generate Nebius Serverless Job configuration.
        
        Args:
            job_type: Type of job (nightly_review, morning_brief)
            schedule: Cron schedule (default: daily at midnight)
            
        Returns:
            Job configuration dict
            
        Note:
            This is a skeleton. Actual deployment requires:
            - Nebius account with Serverless Jobs enabled
            - Valid NEBIUS_API_KEY
            - Job deployment via Nebius CLI or API
        """
        config = {
            "job_type": job_type,
            "schedule": schedule,
            "runtime": "python3.11",
            "handler": f"habitloop.jobs.{job_type}_handler",
            "environment": {
                "NEBIUS_API_KEY": "${NEBIUS_API_KEY}",
                "NEMOTRON_MODEL": "${NEMOTRON_MODEL}",
                "HABITLOOP_DB": "${HABITLOOP_DB}"
            },
            "deployment_notes": [
                "1. Ensure Nebius account has Serverless Jobs enabled",
                "2. Set environment variables in Nebius console",
                "3. Deploy via: nebius jobs create --config job_config.json",
                "4. Monitor via: nebius jobs logs <job-id>"
            ]
        }
        
        return config
    
    @staticmethod
    def get_deployment_instructions() -> str:
        """Get instructions for deploying to Nebius Serverless Jobs."""
        return """
# Nebius Serverless Jobs Deployment

## Prerequisites
1. Nebius account with Serverless Jobs enabled
2. Nebius CLI installed: `pip install nebius-cli`
3. Authenticated: `nebius auth login`
4. NEBIUS_API_KEY configured in Nebius console

## Deploy Nightly Review Job

```bash
# Generate job configuration
python3 -m habitloop.jobs generate-config nightly_review > nightly_job.json

# Deploy job
nebius jobs create --config nightly_job.json --name habitloop-nightly

# Monitor job
nebius jobs list
nebius jobs logs habitloop-nightly
```

## Deploy Morning Brief Job

```bash
# Generate job configuration
python3 -m habitloop.jobs generate-config morning_brief --schedule "0 6 * * *" > morning_job.json

# Deploy job
nebius jobs create --config morning_job.json --name habitloop-morning

# Monitor job
nebius jobs logs habitloop-morning
```

## Environment Variables

Set these in the Nebius console under Serverless Jobs > Environment:

- NEBIUS_API_KEY: Your Nebius Token Factory API key
- NEMOTRON_MODEL: Model to use (default: nvidia/nemotron-3-super-120b-a12b)
- HABITLOOP_DB: Database connection string (for remote storage)

## Local Testing

Before deploying, test jobs locally:

```bash
# Test nightly review
python3 -m habitloop.cli job nightly

# Test morning brief
python3 -m habitloop.cli job morning
```

## Cost Considerations

- Nightly review: ~0.001 Nebius credits per run
- Morning brief: ~0.001 Nebius credits per run
- Monthly (daily jobs): ~0.06 Nebius credits

## Notes

- Jobs run in UTC timezone by default
- Adjust schedule for your timezone
- Database must be accessible from Nebius cloud (use cloud storage or S3-compatible DB)
"""


def nightly_review_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handler for Nebius Serverless Job: nightly review.
    
    This is the entry point when deployed to Nebius.
    """
    store = MemoryStore()
    
    llm = None
    try:
        llm = NebiusClient()
    except ValueError:
        pass
    
    job = NightlyReviewJob(store, llm)
    result = job.execute()
    
    store.close()
    
    return result.to_dict()


def morning_brief_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handler for Nebius Serverless Job: morning brief.
    
    This is the entry point when deployed to Nebius.
    """
    store = MemoryStore()
    
    llm = None
    try:
        llm = NebiusClient()
    except ValueError:
        pass
    
    job = MorningBriefJob(store, llm)
    result = job.execute()
    
    store.close()
    
    return result.to_dict()
