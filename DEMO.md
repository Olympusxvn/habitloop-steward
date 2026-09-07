# HabitLoop Steward Demo

3-minute demonstration of the HabitLoop Steward MVP for the Nebius x NVIDIA Global AI Hackathon (Personal AI Track).

## Overview

HabitLoop Steward is a privacy-first AI habit tracking assistant that uses:
- **Nebius Token Factory** for OpenAI-compatible API access
- **NVIDIA Nemotron** models for AI-powered insights
- **Local SQLite** storage for complete data privacy
- **Graph/loop runtime** with propose→verify→correct workflow

## Demo Script

### Prerequisites

```bash
# Install the package
pip install -e .

# Optional: Set API key for AI features
export NEBIUS_API_KEY=your_api_key_here
export NEMOTRON_MODEL=nvidia/nemotron-3-super-120b-a12b
```

### Part 1: Basic Habit Tracking (30 seconds)

```bash
# Log some habits
habit log exercise --value "30 min" --note "Morning run"
habit log water --value "500ml"
habit log meditation --value "10 min"

# View today's habits
habit today

# View statistics
habit stats
```

**Expected Output:**
- ✓ Habits logged successfully
- Today's summary shows all logged habits
- Stats show streak, adherence percentages

### Part 2: Graph/Loop Runtime Demo (60 seconds)

The loop runtime demonstrates the propose→verify→correct workflow with separate maker and verifier roles.

```bash
# Demo 1: Bad proposal (missing required field) → RED gate
habit verify-demo
```

**What happens:**
1. **Bad Proposal**: Missing `habit_key` (required field)
2. **Verifier**: Detects schema violation → **RED** gate
3. **Result**: Escalated (cannot auto-correct RED issues)

**Expected Output:**
```
Scenario 1: Bad Proposal (missing required field)
  Status: escalated
  Result: red
  ❌ Missing required field: habit_key
```

```bash
# Demo 2: Quiet hours check → YELLOW gate (if configured)
habit profile set --timezone "America/New_York" --quiet-hours '{"start": "22:00", "end": "07:00"}'
habit verify-demo
```

**Expected Output:**
```
Scenario 2: Quiet Hours Check
  Status: success_with_warnings / success
  ⚠️  Logging during quiet hours (if applicable)
  ✓ No quiet hours configured or outside quiet hours (otherwise)
```

```bash
# Demo 3: Valid proposal → GREEN gate
habit verify-demo
```

**Expected Output:**
```
Scenario 3: Valid Proposal
  Status: success
  Result: green
  ✓ All checks passed
```

### Part 3: Constraint Learning (45 seconds)

Demonstrates automatic constraint learning from low-adherence patterns.

```bash
# Create a low-adherence pattern (simulate missed days)
# In real usage, this would be ≥3 failures in 14 days with <30% adherence

# Run constraint learning
habit learn-constraints

# View learned constraints
habit constraints
```

**Expected Output:**
- Patterns detected: X
- New constraints created: Y
- Shows learned rules like "Review [habit]: adherence was low..."

### Part 4: Always-On Jobs (30 seconds)

Demonstrates local execution of serverless jobs (deployable to Nebius Serverless Jobs).

```bash
# Run nightly review locally
habit job nightly

# Run morning brief locally
habit job morning

# Show deployment instructions
habit job deploy-info
```

**Expected Output:**
- **Nightly Review**: Summary of day's habits with stats
- **Morning Brief**: Goals and yesterday's progress
- Deployment guide for Nebius Serverless Jobs

### Part 5: Weekly Review (30 seconds)

```bash
# Generate weekly review
habit weekly-review

# If NEBIUS_API_KEY is set, includes AI insights
# Otherwise, shows code-computed stats only
```

**Expected Output:**
- Total logs, unique habits, days active
- Top habits with streaks and adherence
- Active constraints
- Optional AI insights (if API key present)

### Part 6: Web UI (30 seconds)

```bash
# Start web server
habit web

# Or with custom host/port
habit web --host 0.0.0.0 --port 8080
```

Then visit `http://localhost:8000`:
- **Today**: View and log habits
- **Statistics**: Streaks and adherence
- **Constraints**: Learned rules
- **Weekly Review**: Full review with insights
- **Privacy**: Data control panel

## Architecture Highlights

### Technology Stack

```
┌─────────────────────────────────────────┐
│         User Interfaces                 │
│  ┌──────────┐      ┌─────────────┐    │
│  │ CLI      │      │  Web UI     │    │
│  │ (typer)  │      │ (FastAPI)   │    │
│  └──────────┘      └─────────────┘    │
└─────────────────────────────────────────┘
           │                  │
┌──────────▼──────────────────▼───────────┐
│         Core Components                  │
│  ┌──────────────────────────────────┐  │
│  │  Domain Skills                    │  │
│  │  • Daily nudge                    │  │
│  │  • Plan adjust                    │  │
│  │  • Habit stats (code nodes)       │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  Graph/Loop Runtime               │  │
│  │  • Intent splitter                │  │
│  │  │  • Propose → Verify → Correct  │  │
│  │  • Separate verifier (no maker    │  │
│  │    reasoning access)              │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  Learning Edge                    │  │
│  │  • Constraint learning            │  │
│  │  • Pattern detection              │  │
│  │  • Weekly review                  │  │
│  └──────────────────────────────────┘  │
└──────────────────────────────────────────┘
           │                  │
     ┌─────▼─────┐      ┌────▼─────────┐
     │  SQLite   │      │ Nebius Token │
     │  (local)  │      │   Factory    │
     │           │      │  + Nemotron  │
     └───────────┘      └──────────────┘
```

### Key Features

1. **Privacy-First**
   - All habit data stored locally (SQLite)
   - Only AI queries sent to Nebius (optional)
   - User-controlled data deletion

2. **Graph/Loop Runtime**
   - Propose → Verify → Correct (≤3 attempts)
   - Separate verifier role (no maker context)
   - RED/YELLOW/GREEN gates
   - Auto-correction or escalation

3. **Learning Edge**
   - Automatic constraint learning from patterns
   - ≥3 failures + <30% adherence triggers learning
   - No duplicate constraint creation

4. **Always-On Capability**
   - Nebius Serverless Jobs skeleton
   - Local fallback for testing
   - Nightly review + morning brief

5. **Non-Medical Guardrails**
   - Explicit disclaimers in all outputs
   - LLM system prompt boundaries
   - Focus on data observation, not diagnosis

## Testing Without API Key

All features work offline without `NEBIUS_API_KEY`:

```bash
# All these work offline
habit log exercise --value "30 min"
habit today
habit stats
habit verify-demo
habit learn-constraints
habit constraints
habit job nightly
habit weekly-review
habit web

# These gracefully degrade without API key
habit ask "How am I doing?"          # Error message
habit ping-model                     # Error message
habit nudge                          # Deterministic fallback
```

## Offline Test Run

```bash
# Full offline demo
./scripts/demo.sh --offline
```

## With API Key

When `NEBIUS_API_KEY` is set:

```bash
# Test connection
habit ping-model

# AI-powered features
habit ask "What patterns do you see in my habits?"
habit nudge                          # LLM-generated encouragement
habit weekly-review                  # Includes AI insights
habit job nightly                    # Includes AI reflection
```

## Success Criteria

All requirements met:

- ✅ **Day 1-2**: Foundation (SQLite, Nebius client, CLI)
- ✅ **Day 3-4**: Domain skills (nudge, plan, stats with code nodes)
- ✅ **Day 5-6**: Graph/loop runtime (propose→verify→correct, separate verifier)
- ✅ **Day 7**: Serverless jobs (skeleton + local fallback)
- ✅ **Day 8-9**: Learning edge (constraint learning, weekly review)
- ✅ **Day 10-11**: Web UI (FastAPI, privacy panel)
- ✅ **Day 12**: Demo script (this file)

## For Judges

### Innovation
- Graph/loop runtime with separate maker/verifier roles
- Automatic constraint learning from user patterns
- Privacy-first architecture with local storage

### Technical Excellence
- Clean separation of concerns
- Graceful degradation without API key
- Comprehensive test coverage (offline)

### Personal AI Track Fit
- Always-on steward capability (serverless jobs)
- Learns from user patterns (constraint learning)
- Private and user-controlled (local SQLite)

### Nebius + NVIDIA Integration
- Nebius Token Factory for OpenAI-compatible access
- NVIDIA Nemotron models for AI insights
- Documented deployment to Nebius Serverless Jobs

## Next Steps (Days 13-14)

Human implementer will complete:
1. ✅ Make repository public
2. ✅ Record ≤3 min demo video
3. ✅ Final README polish
4. ✅ Submit to Devpost
5. ✅ Submit hackathon feedback form

## License

MIT License - See LICENSE file

## Disclaimer

⚠️ **This is NOT medical advice.** HabitLoop Steward does not diagnose conditions, prescribe treatments, or replace consultation with qualified healthcare professionals. For any health concerns, always consult qualified healthcare professionals.
