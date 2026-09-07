#!/bin/bash
# HabitLoop Steward Demo Script
# 3-minute automated demonstration

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║            HabitLoop Steward Demo                            ║"
echo "║  Personal AI Track - Nebius x NVIDIA Hackathon               ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check offline mode
OFFLINE_MODE=false
if [ "$1" == "--offline" ]; then
    OFFLINE_MODE=true
    echo -e "${YELLOW}Running in OFFLINE mode (no API key required)${NC}"
    unset NEBIUS_API_KEY
    echo ""
fi

# Function to pause between steps
pause() {
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read
}

# Part 1: Basic Habit Tracking
echo -e "${GREEN}═══ Part 1: Basic Habit Tracking ═══${NC}"
echo ""

echo "Logging some habits..."
python3 -m habitloop.cli log exercise --value "30 min" --note "Morning run"
python3 -m habitloop.cli log water --value "500ml"
python3 -m habitloop.cli log meditation --value "10 min"
echo ""

pause

echo "Viewing today's habits..."
python3 -m habitloop.cli today
echo ""

pause

echo "Checking statistics..."
python3 -m habitloop.cli stats
echo ""

pause

# Part 2: Graph/Loop Runtime
echo -e "${GREEN}═══ Part 2: Graph/Loop Runtime Demo ═══${NC}"
echo ""
echo "Demonstrating propose→verify→correct workflow..."
echo ""

python3 -m habitloop.cli verify-demo

pause

# Part 3: Constraint Learning
echo -e "${GREEN}═══ Part 3: Constraint Learning ═══${NC}"
echo ""

echo "Running constraint learning cycle..."
python3 -m habitloop.cli learn-constraints
echo ""

pause

echo "Viewing active constraints..."
python3 -m habitloop.cli constraints
echo ""

pause

# Part 4: Always-On Jobs
echo -e "${GREEN}═══ Part 4: Always-On Jobs (Local) ═══${NC}"
echo ""

echo "Running nightly review..."
python3 -m habitloop.cli job nightly
echo ""

pause

echo "Running morning brief..."
python3 -m habitloop.cli job morning
echo ""

pause

# Part 5: Weekly Review
echo -e "${GREEN}═══ Part 5: Weekly Review ═══${NC}"
echo ""

echo "Generating weekly review..."
python3 -m habitloop.cli weekly-review
echo ""

pause

# Part 6: API Features (if not offline)
if [ "$OFFLINE_MODE" = false ] && [ ! -z "$NEBIUS_API_KEY" ]; then
    echo -e "${GREEN}═══ Part 6: AI-Powered Features ═══${NC}"
    echo ""
    
    echo "Testing API connection..."
    python3 -m habitloop.cli ping-model
    echo ""
    
    pause
    
    echo "Getting AI-powered nudge..."
    python3 -m habitloop.cli nudge
    echo ""
else
    echo -e "${YELLOW}Skipping AI-powered features (offline mode or no API key)${NC}"
    echo ""
fi

# Summary
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║                   Demo Complete! ✅                           ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

echo "Key Features Demonstrated:"
echo "  ✓ Basic habit tracking with statistics"
echo "  ✓ Graph/loop runtime with verification gates"
echo "  ✓ Automatic constraint learning"
echo "  ✓ Always-on job execution (local)"
echo "  ✓ Weekly review with insights"
if [ "$OFFLINE_MODE" = false ] && [ ! -z "$NEBIUS_API_KEY" ]; then
    echo "  ✓ AI-powered features via Nebius + Nemotron"
fi
echo ""

echo "Next Steps:"
echo "  • Start web UI: python3 -m habitloop.cli web"
echo "  • View full demo guide: cat DEMO.md"
echo "  • Deploy to Nebius: python3 -m habitloop.cli job deploy-info"
echo ""

echo -e "${YELLOW}⚠️  Reminder: This is NOT medical advice.${NC}"
echo ""
