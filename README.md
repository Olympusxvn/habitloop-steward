# HabitLoop Steward

Personal AI habit tracking assistant with always-on private steward capabilities. Built for the Nebius x NVIDIA Global AI Hackathon (Personal AI Track).

## ⚠️ Important Disclaimer

**This application is NOT medical advice.** HabitLoop Steward is a personal tracking tool that helps you log and understand your habits. It does NOT:

- Diagnose medical conditions
- Provide medical advice or treatment recommendations
- Replace consultation with qualified healthcare professionals

For any health concerns, always consult qualified healthcare professionals.

## Features

- 📝 Simple habit logging via CLI
- 💾 Local SQLite storage (your data stays private)
- 🤖 AI assistant powered by NVIDIA Nemotron via Nebius Token Factory
- 📊 Daily habit summaries
- 👤 Customizable profile with goals, timezone, and preferences
- 🔒 Privacy-first design (no data leaves your machine except LLM queries)

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- A Nebius Token Factory API key (for AI features)

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd habitloop-steward
```

2. Install the package in development mode:
```bash
pip install -e .
```

For development with testing dependencies:
```bash
pip install -e ".[dev]"
```

3. Copy the example environment file:
```bash
cp .env.example .env
```

4. Edit `.env` and add your Nebius API key:
```bash
NEBIUS_API_KEY=your_actual_api_key_here
```

## Getting Your Nebius API Key

HabitLoop Steward uses the Nebius Token Factory for OpenAI-compatible access to NVIDIA Nemotron models.

1. Visit [Nebius Token Factory](https://tokenfactory.nebius.com/)
2. Sign up or log in
3. Generate an API key
4. Add the key to your `.env` file

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEBIUS_API_KEY` | Your Nebius Token Factory API key | Yes (for AI features) | None |
| `NEMOTRON_MODEL` | Model identifier to use | No | `nvidia/nemotron-3-super-120b-a12b` |
| `HABITLOOP_DB` | Path to SQLite database file | No | `habitloop.db` |

### Available Models

The default model is `nvidia/nemotron-3-super-120b-a12b`. You can configure other models available through Nebius Token Factory by setting the `NEMOTRON_MODEL` environment variable.

## Usage

### Basic Commands

#### Log a Habit
```bash
# Simple log
habit log exercise

# With value
habit log water --value "500ml"

# With note
habit log meditation --note "10 minutes morning session"

# With both
habit log running --value "5km" --note "felt great!"
```

#### View Today's Habits
```bash
habit today
```

#### Manage Profile
```bash
# Show current profile
habit profile show

# Set/update profile
habit profile set --timezone "America/New_York"

# Set goals (as JSON)
habit profile set --goals '{"exercise": "5 days/week", "reading": "30 min/day"}'

# Set quiet hours
habit profile set --quiet-hours '{"start": "22:00", "end": "07:00"}'

# Set preferences
habit profile set --preferences '{"notifications": true, "weekly_summary": true}'
```

#### AI Assistant (requires API key)

Test connection:
```bash
habit ping-model
```

Ask a question:
```bash
habit ask "How am I doing with my habits this week?"
habit ask "What patterns do you see in my exercise routine?"
habit ask "Give me some motivation to keep going!"
```

The AI assistant automatically includes:
- Your profile information (timezone, goals)
- Today's logged habits
- Context-aware responses
- Non-medical guidance only

## Architecture

```
src/habitloop/
├── __init__.py       # Package initialization
├── models.py         # Data models (Profile, HabitLog, Constraint)
├── memory.py         # SQLite storage layer
├── llm.py           # Nebius Token Factory client
└── cli.py           # Command-line interface
```

### Database Schema

**profile** - User profile (single row)
- `id` (INTEGER PRIMARY KEY)
- `timezone` (TEXT)
- `goals` (TEXT/JSON)
- `quiet_hours` (TEXT/JSON)
- `preferences` (TEXT/JSON)
- `updated_at` (TEXT/ISO8601)

**habit_log** - Habit entries
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `habit_key` (TEXT) - habit identifier
- `value` (TEXT, optional) - measurement/value
- `note` (TEXT, optional) - user note
- `logged_at` (TEXT/ISO8601)
- `source` (TEXT) - 'cli', 'app', etc.

**constraints** - Rules and constraints
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `rule_text` (TEXT) - constraint description
- `source` (TEXT) - where the constraint came from
- `active` (INTEGER) - 0 or 1
- `created_at` (TEXT/ISO8601)

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=habitloop --cov-report=html
```

The tests cover all SQLite CRUD operations and work without an API key.

## Development

The project uses:
- **typer** for the CLI interface
- **openai** library for OpenAI-compatible API access
- **python-dotenv** for environment variable management
- **pytest** for testing

## Privacy & Data

- All habit data is stored locally in SQLite (`habitloop.db`)
- Profile and logs never leave your machine
- Only AI queries are sent to Nebius Token Factory
- No telemetry or analytics
- You can delete `habitloop.db` at any time to reset

## Hackathon Context

**Track:** Personal AI Track  
**Event:** Nebius x NVIDIA Global AI Hackathon  
**Focus:** Always-on private habit steward with graph/loop runtime (future phases)

### Roadmap

**Day 1-2 (Current):** ✅ Foundation
- SQLite memory storage
- Nebius Token Factory integration
- Basic CLI commands
- Non-medical guardrails

**Day 3-4:** Enhanced Intelligence
- Context-aware suggestions
- Pattern recognition
- Multi-day habit tracking
- Streak calculations

**Day 5-6:** Graph Runtime
- Habit relationship modeling
- Dependency tracking
- Goal progress visualization

**Day 7:** Always-On Steward
- Background monitoring
- Proactive reminders
- Adaptive scheduling

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

This project is being developed for a hackathon. After the event, contributions will be welcome!

## Support

For issues or questions during development, please open a GitHub issue.

---

**Remember:** This tool is for personal tracking only. Always consult healthcare professionals for medical advice.
