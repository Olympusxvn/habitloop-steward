"""Web UI for HabitLoop Steward using FastAPI.

Provides a minimal web interface for habit tracking and review.
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import date, datetime
from typing import Optional
import os

from .memory import MemoryStore
from .llm import NebiusClient
from .skills import DailyNudgeSkill, HabitStats
from .learning import WeeklyReviewSkill, ConstraintLearner


# Initialize FastAPI app
app = FastAPI(
    title="HabitLoop Steward",
    description="Personal AI habit tracking assistant",
    version="0.1.0"
)


def get_db_path() -> str:
    """Get database path from env or default."""
    return os.getenv("HABITLOOP_DB", "habitloop.db")


def get_llm_client() -> Optional[NebiusClient]:
    """Get LLM client if API key is available."""
    try:
        return NebiusClient()
    except ValueError:
        return None


# HTML Templates (inline for simplicity)
HTML_HEADER = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - HabitLoop Steward</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        nav {{
            margin: 20px 0;
            padding: 10px 0;
            border-bottom: 1px solid #ddd;
        }}
        nav a {{
            margin-right: 20px;
            text-decoration: none;
            color: #3498db;
            font-weight: 500;
        }}
        nav a:hover {{
            text-decoration: underline;
        }}
        .habit-log {{
            background: #ecf0f1;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }}
        .stat-box {{
            background: #e8f5e9;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .constraint-box {{
            background: #fff3cd;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #f39c12;
            border-radius: 4px;
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .privacy-panel {{
            background: #e3f2fd;
            border: 1px solid #2196f3;
            padding: 20px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        form {{
            margin: 20px 0;
        }}
        input, textarea, button {{
            padding: 10px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        input[type="text"], textarea {{
            width: 100%;
            max-width: 400px;
        }}
        button {{
            background: #3498db;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 500;
        }}
        button:hover {{
            background: #2980b9;
        }}
        .disclaimer {{
            background: #ffebee;
            border-left: 4px solid #f44336;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #777;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔄 HabitLoop Steward</h1>
        <nav>
            <a href="/">Today</a>
            <a href="/stats">Statistics</a>
            <a href="/constraints">Constraints</a>
            <a href="/weekly">Weekly Review</a>
            <a href="/privacy">Privacy</a>
        </nav>
"""

HTML_FOOTER = """
        <div class="footer">
            HabitLoop Steward v0.1.0 | MIT License<br>
            ⚠️ This is NOT medical advice. Consult healthcare professionals for health concerns.
        </div>
    </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    """Today's habits page."""
    store = MemoryStore(get_db_path())
    
    try:
        logs = store.get_logs_for_date(date.today())
        
        logs_html = ""
        if logs:
            for log in logs:
                time_str = log.logged_at.strftime('%H:%M')
                logs_html += f'<div class="habit-log">'
                logs_html += f'<strong>{time_str}</strong> - {log.habit_key}<br>'
                if log.value:
                    logs_html += f'Value: {log.value}<br>'
                if log.note:
                    logs_html += f'Note: {log.note}'
                logs_html += '</div>'
        else:
            logs_html = '<p>No habits logged today yet.</p>'
        
        html = HTML_HEADER.format(title="Today") + f"""
        <h2>📊 Today's Habits ({date.today().strftime('%Y-%m-%d')})</h2>
        {logs_html}
        
        <h2>➕ Log a Habit</h2>
        <form method="post" action="/log">
            <input type="text" name="habit_key" placeholder="Habit name (e.g., exercise)" required><br>
            <input type="text" name="value" placeholder="Value (optional)"><br>
            <textarea name="note" placeholder="Note (optional)" rows="3"></textarea><br>
            <button type="submit">Log Habit</button>
        </form>
        """ + HTML_FOOTER
        
        return html
    finally:
        store.close()


@app.post("/log")
async def log_habit(habit_key: str = Form(...), value: Optional[str] = Form(None), 
                   note: Optional[str] = Form(None)):
    """Log a habit."""
    store = MemoryStore(get_db_path())
    
    try:
        store.log_habit(habit_key, value=value if value else None, note=note if note else None)
        return RedirectResponse(url="/", status_code=303)
    finally:
        store.close()


@app.get("/stats", response_class=HTMLResponse)
async def stats():
    """Statistics page."""
    store = MemoryStore(get_db_path())
    
    try:
        cursor = store.conn.cursor()
        cursor.execute("SELECT DISTINCT habit_key FROM habit_log ORDER BY habit_key")
        habit_keys = [row[0] for row in cursor.fetchall()]
        
        stats_html = ""
        if habit_keys:
            for habit_key in habit_keys:
                stats_obj = HabitStats(habit_key, store)
                stats_data = stats_obj.compute()
                
                if stats_data["total_logs"] == 0:
                    continue
                
                stats_html += f'<div class="stat-box">'
                stats_html += f'<strong>{habit_key}</strong><br>'
                stats_html += f'Total logs: {stats_data["total_logs"]}<br>'
                stats_html += f'Current streak: {stats_data["current_streak"]} days<br>'
                stats_html += f'7-day adherence: {stats_data["adherence_7d"]}%<br>'
                stats_html += f'30-day adherence: {stats_data["adherence_30d"]}%'
                stats_html += '</div>'
        else:
            stats_html = '<p>No habits logged yet.</p>'
        
        html = HTML_HEADER.format(title="Statistics") + f"""
        <h2>📊 Habit Statistics</h2>
        {stats_html}
        """ + HTML_FOOTER
        
        return html
    finally:
        store.close()


@app.get("/constraints", response_class=HTMLResponse)
async def constraints():
    """Constraints page."""
    store = MemoryStore(get_db_path())
    
    try:
        constraints_list = store.get_active_constraints()
        
        constraints_html = ""
        if constraints_list:
            for constraint in constraints_list:
                source_icon = "🤖" if constraint.source == "learned" else "👤"
                constraints_html += f'<div class="constraint-box">'
                constraints_html += f'{source_icon} <strong>#{constraint.id}</strong><br>'
                constraints_html += f'{constraint.rule_text}<br>'
                constraints_html += f'<small>Source: {constraint.source} | Created: {constraint.created_at.strftime("%Y-%m-%d")}</small>'
                constraints_html += '</div>'
        else:
            constraints_html = '<p>No active constraints yet.</p>'
        
        html = HTML_HEADER.format(title="Constraints") + f"""
        <h2>📋 Active Constraints</h2>
        <p>Constraints are rules learned from your patterns or set manually.</p>
        {constraints_html}
        
        <h2>🧠 Run Constraint Learning</h2>
        <p>Analyze patterns and automatically create constraints from repeated low-adherence habits.</p>
        <form method="post" action="/learn">
            <button type="submit">Run Learning Cycle</button>
        </form>
        """ + HTML_FOOTER
        
        return html
    finally:
        store.close()


@app.post("/learn")
async def learn():
    """Run constraint learning."""
    store = MemoryStore(get_db_path())
    
    try:
        learner = ConstraintLearner(store)
        learner.run_learning_cycle()
        return RedirectResponse(url="/constraints", status_code=303)
    finally:
        store.close()


@app.get("/weekly", response_class=HTMLResponse)
async def weekly():
    """Weekly review page."""
    store = MemoryStore(get_db_path())
    
    try:
        llm = get_llm_client()
        skill = WeeklyReviewSkill(store, llm)
        result = skill.execute(weeks_back=1)
        
        summary_html = result["summary"].replace("\n", "<br>")
        
        llm_status = ""
        if not result.get("llm_available", False):
            llm_status = '<div class="warning">Using offline mode. Set NEBIUS_API_KEY for AI-powered insights.</div>'
        
        html = HTML_HEADER.format(title="Weekly Review") + f"""
        <h2>📈 Weekly Review</h2>
        {llm_status}
        <div style="white-space: pre-wrap; line-height: 1.6;">{summary_html}</div>
        """ + HTML_FOOTER
        
        return html
    finally:
        store.close()


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    """Privacy panel page."""
    db_path = get_db_path()
    db_exists = os.path.exists(db_path)
    db_size = os.path.getsize(db_path) if db_exists else 0
    
    llm_status = "✓ Configured" if get_llm_client() else "✗ Not configured (offline mode)"
    
    html = HTML_HEADER.format(title="Privacy") + f"""
    <h2>🔒 Privacy & Data Control</h2>
    
    <div class="privacy-panel">
        <h3>Your Data</h3>
        <p><strong>Local Storage:</strong> All habit data is stored locally on your machine.</p>
        <p><strong>Database Location:</strong> <code>{db_path}</code></p>
        <p><strong>Database Size:</strong> {db_size / 1024:.2f} KB</p>
        <p><strong>LLM Status:</strong> {llm_status}</p>
    </div>
    
    <div class="privacy-panel">
        <h3>What Stays Local</h3>
        <ul>
            <li>All habit logs and timestamps</li>
            <li>Your profile (timezone, goals, preferences)</li>
            <li>Learned constraints and rules</li>
            <li>Statistics and analytics</li>
        </ul>
    </div>
    
    <div class="privacy-panel">
        <h3>What Goes to Nebius (if API key set)</h3>
        <ul>
            <li>AI queries (ask, nudge, weekly insights)</li>
            <li>Contextual data needed for responses</li>
            <li>No habit logs are sent without your explicit request</li>
        </ul>
    </div>
    
    <div class="disclaimer">
        <h3>⚠️ Medical Disclaimer</h3>
        <p>This application is NOT medical advice. It does not diagnose conditions, 
        prescribe treatments, or replace consultation with qualified healthcare professionals.</p>
        <p>For any health concerns, always consult qualified healthcare professionals.</p>
    </div>
    
    <div class="privacy-panel">
        <h3>Your Control</h3>
        <p><strong>Delete All Data:</strong> Remove the database file at <code>{db_path}</code></p>
        <p><strong>Export Data:</strong> Use SQLite tools to export: <code>sqlite3 {db_path} .dump</code></p>
        <p><strong>Disable LLM:</strong> Remove or unset <code>NEBIUS_API_KEY</code> environment variable</p>
    </div>
    """ + HTML_FOOTER
    
    return html


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": os.path.exists(get_db_path()),
        "llm_configured": get_llm_client() is not None
    }
