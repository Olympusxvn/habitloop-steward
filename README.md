# HabitLoop Steward

Personal AI habit tracking assistant with always-on private steward capabilities. Built for the Nebius x NVIDIA Global AI Hackathon (Personal AI Track).

## ⚠️ Important Disclaimer

**This application is NOT medical advice.** HabitLoop Steward is a personal tracking tool that helps you log and understand your habits. It does NOT:

- Diagnose medical conditions
- Provide medical advice or treatment recommendations
- Replace consultation with qualified healthcare professionals

For any health concerns, always consult qualified healthcare professionals.

## Features

### Core Capabilities
- 📝 Simple habit logging via CLI and web UI
- 💾 Local SQLite storage (your data stays private)
- 🤖 AI assistant powered by NVIDIA Nemotron via Nebius Token Factory
- 📊 Statistics with streaks and adherence tracking
- 👤 Customizable profile with goals, timezone, and preferences

### Advanced Features
- 🔄 **Graph/Loop Runtime**: Propose→Verify→Correct workflow with separate verifier
- 🧠 **Constraint Learning**: Automatically learns rules from low-adherence patterns
- 📈 **Weekly Reviews**: Code-computed stats + optional AI insights
- 🌙 **Serverless Jobs**: Nightly review & morning brief (deployable to Nebius)
- 🌐 **Web UI**: FastAPI-based interface with privacy panel
- 🔒 **Privacy-First**: All data local, explicit control, no telemetry

## Architecture

```
┌─────────────────────────────────────────┐
│         User Interfaces                 │
│  ┌──────────┐      ┌─────────────┐    │
│  │   CLI    │      │   Web UI    │    │
│  │ (typer)  │      │ (FastAPI)   │    │
│  └──────────┘      └─────────────┘    │
└─────────────────────────────────────────┘
           │                  │
┌──────────▼──────────────────▼───────────┐
│         Core Components                  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  Domain Skills                    │  │
│  │  • Daily nudge (motivational)     │  │
│  │  • Plan adjust (recommendations)  │  │
│  │  • Stats calculation (code nodes) │  │
│  │    - Streaks                      │  │
│  │    - Adherence %                  │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  Graph/Loop Runtime               │  │
│  │  • Intent splitter (chat/job)     │  │
│  │  • Propose → Verify → Correct     │  │
│  │  • Separate verifier role         │  │
│  │  • RED/YELLOW/GREEN gates         │  │
│  │  • Auto-correct or escalate       │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  Learning Edge                    │  │
│  │  • Constraint learning            │  │
│  │  • Pattern detection (≥3 fails)   │  │
│  │  • Weekly review synthesis        │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  Jobs (Serverless)                │  │
│  │  • Nightly review                 │  │
│  │  • Morning brief                  │  │
│  │  • Local fallback + Nebius deploy │  │
│  └──────────────────────────────────┘  │
└──────────────────────────────────────────┘
           │                  │
     ┌─────▼─────┐      ┌────▼─────────┐
     │  SQLite   │      │ Nebius Token │
     │  (local)  │      │   Factory    │
     │           │      │  + Nemotron  │
     └───────────┘      └──────────────┘
```

### Module Structure

```
src/habitloop/
├── __init__.py       # Package initialization
├── models.py         # Data models (Profile, HabitLog, Constraint)
├── memory.py         # SQLite storage layer with CRUD
├── llm.py            # Nebius Token Factory client
├── skills.py         # Domain skills (nudge, plan, stats)
├── loop.py           # Graph/loop runtime + verifier
├── learning.py       # Constraint learning + weekly review
├── jobs.py           # Serverless job handlers
├── cli.py            # Command-line interface
└── web.py            # FastAPI web UI

tests/
├── test_memory.py    # SQLite CRUD tests
├── test_skills.py    # Skills tests (offline)
├── test_loop.py      # Loop runtime tests
└── test_learning.py  # Learning tests
```

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- A Nebius Token Factory API key (optional, for AI features)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Olympusxvn/habitloop-steward
cd habitloop-steward
```

2. Install the package:
```bash
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

3. (Optional) Configure API key for AI features:
```bash
cp .env.example .env
# Edit .env and add: NEBIUS_API_KEY=your_api_key_here
```

## Getting Your Nebius API Key

HabitLoop Steward uses the Nebius Token Factory for OpenAI-compatible access to NVIDIA Nemotron models.

1. Visit [Nebius Token Factory](https://tokenfactory.nebius.com/)
2. Sign up or log in
3. Generate an API key
4. Add the key to your `.env` file

## Usage

### CLI Commands

All commands work **without an API key** (graceful offline mode).

#### Basic Tracking
```bash
# Log habits
habit log exercise --value "30 min" --note "Morning run"
habit log water --value "500ml"

# View today's habits
habit today

# Show statistics (streaks, adherence)
habit stats
habit stats exercise  # For specific habit
```

#### AI Features (optional API key)
```bash
# Test connection
habit ping-model

# Get daily motivation
habit nudge

# Ask questions
habit ask "How am I doing with my exercise goals?"

# Plan adjustments
habit plan-adjust
habit plan-adjust exercise  # For specific habit
```

#### Profile Management
```bash
# Set profile
habit profile set --timezone "America/New_York" \
                 --goals '{"exercise": "5 days/week"}' \
                 --quiet-hours '{"start": "22:00", "end": "07:00"}'

# View profile
habit profile show
```

#### Graph/Loop Runtime
```bash
# Demo the verification workflow
habit verify-demo

# Run loop on custom proposal
habit run-loop '{"proposal_type": "habit_log", "data": {"habit_key": "exercise"}}'
```

#### Constraint Learning
```bash
# Run learning cycle (detects patterns, creates constraints)
habit learn-constraints

# View learned constraints
habit constraints
```

#### Weekly Review
```bash
# Generate weekly review
habit weekly-review

# Review multiple weeks
habit weekly-review --weeks 2
```

#### Serverless Jobs (Local)
```bash
# Run nightly review
habit job nightly

# Run morning brief
habit job morning

# Show deployment instructions
habit job deploy-info
```

#### Web UI
```bash
# Start web server
habit web

# Custom host/port
habit web --host 0.0.0.0 --port 8080

# Then visit: http://localhost:8000
```

### Web UI Features

The web interface provides:
- **Today**: View and log habits
- **Statistics**: Streaks, adherence, total logs
- **Constraints**: View learned rules, trigger learning
- **Weekly Review**: Full review with optional AI insights
- **Privacy**: Data control panel, deletion instructions

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEBIUS_API_KEY` | Nebius Token Factory API key | No (offline mode) | None |
| `NEMOTRON_MODEL` | Model to use | No | `nvidia/nemotron-3-super-120b-a12b` |
| `HABITLOOP_DB` | Database path | No | `habitloop.db` |

## Testing

Run the full test suite (all tests work offline):

```bash
pytest -v

# With coverage
pytest --cov=habitloop --cov-report=html
```

Expected results:
- Memory tests: 14 passing
- Skills tests: ~15 passing
- Loop tests: ~10 passing
- Learning tests: ~8 passing

## Demo

See [DEMO.md](DEMO.md) for a complete 3-minute demonstration.

Quick demo:
```bash
./scripts/demo.sh

# Offline mode (no API key)
./scripts/demo.sh --offline
```

## Deploying to Nebius Serverless

For always-on jobs (nightly review, morning brief):

```bash
# View deployment instructions
habit job deploy-info

# Generate job config
python3 -c "from habitloop.jobs import NebiusJobScheduler; \
            import json; \
            print(json.dumps(NebiusJobScheduler.generate_job_config('nightly_review'), indent=2))"
```

See [deployment documentation](DEMO.md#deploying-to-nebius-serverless) for full details.

## Privacy & Data

- **Local Storage**: All habit data stored in SQLite (`habitloop.db`)
- **No Telemetry**: Zero analytics or tracking
- **LLM Queries Only**: Only AI requests sent to Nebius (optional)
- **User Control**: Delete database anytime, export with SQLite tools
- **Privacy Panel**: View data location and control options in web UI

## Hackathon Context

**Track:** Personal AI Track  
**Event:** Nebius x NVIDIA Global AI Hackathon  
**Technologies:**
- Nebius Token Factory (OpenAI-compatible API)
- NVIDIA Nemotron models
- SQLite (local storage)
- FastAPI (web UI)
- Python 3.9+

### Implementation Timeline

- **Days 1-2**: Foundation (SQLite, Nebius client, CLI)
- **Days 3-4**: Domain skills (nudge, plan adjust, stats with code nodes)
- **Days 5-6**: Graph/loop runtime (propose→verify→correct, separate verifier)
- **Day 7**: Serverless jobs skeleton + local fallback
- **Days 8-9**: Learning edge (constraint learning, weekly review)
- **Days 10-11**: Minimal web UI with privacy panel
- **Day 12**: Demo script and documentation
- **Days 13-14**: Video, README polish, Devpost submission

## Days 13-14 Checklist (Human Implementer)

Before hackathon submission:

### Day 13: Preparation
- [ ] **Make repository public** (if currently private)
  - Remove any sensitive data or credentials
  - Verify LICENSE file is present (MIT)
  - Check .gitignore excludes .env and .db files

- [ ] **Record demo video** (≤3 minutes)
  - Show: habit logging, stats, verify-demo, constraint learning, weekly review, web UI
  - Highlight: graph/loop runtime, privacy-first, Nebius+Nemotron integration
  - Include: architecture diagram, code walkthrough (optional)
  - Format: MP4, 1080p recommended
  - Tools: OBS Studio, Loom, or built-in screen recorder

- [ ] **Final README polish**
  - Add demo video link
  - Update any placeholder URLs
  - Verify all commands work as documented
  - Add screenshots (optional but recommended)

### Day 14: Submission
- [ ] **Devpost submission**
  - Project title: "HabitLoop Steward - Privacy-First AI Habit Tracking"
  - Tagline: "Always-on personal AI steward with graph/loop runtime and constraint learning"
  - Description: Paste from README (architecture + features)
  - Demo video: Upload or link
  - GitHub repo: https://github.com/Olympusxvn/habitloop-steward
  - Technologies: Nebius Token Factory, NVIDIA Nemotron, FastAPI, SQLite, Python
  - Built for: Personal AI Track

- [ ] **Required Devpost fields**
  - Inspiration: "Need for privacy-first habit tracking with AI insights"
  - What it does: "Tracks habits locally, learns patterns, provides AI coaching"
  - How we built it: "Python + Nebius + Nemotron + graph/loop runtime"
  - Challenges: "Offline degradation, separate verifier role, constraint learning"
  - Accomplishments: "Full MVP with serverless jobs, learning edge, privacy controls"
  - What we learned: "Graph/loop patterns, Nebius integration, privacy-first design"
  - What's next: "Mobile app, more sophisticated learning, community deployment"

- [ ] **Submit hackathon feedback form** (if provided by organizers)

- [ ] **Optional: Social sharing**
  - Tweet demo video with #NebiusHackathon #NVIDIA
  - LinkedIn post about building experience
  - Dev.to article (optional)

### Pre-Submission Checklist

- [ ] Repository is public
- [ ] LICENSE file present (MIT)
- [ ] README is complete
- [ ] .gitignore excludes sensitive files
- [ ] Demo video recorded (≤3 min)
- [ ] All tests pass: `pytest -v`
- [ ] Offline mode works: `./scripts/demo.sh --offline`
- [ ] Web UI starts: `python3 -m habitloop.cli web`
- [ ] DEMO.md is accurate
- [ ] No TODOs or placeholder text in code

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

This project was developed for a hackathon. After the event, contributions will be welcome!

## Support

For issues or questions:
- GitHub Issues: https://github.com/Olympusxvn/habitloop-steward/issues
- Demo: See [DEMO.md](DEMO.md)
- Architecture: See section above

---

**Remember:** This tool is for personal tracking only. Always consult healthcare professionals for medical advice.
