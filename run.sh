#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
#export AGENT_PORT=${AGENT_PORT:-8001}
#export HOST=${HOST:-0.0.0.0}

# Use the python from the venv if available
if [ -d "venv" ]; then
    # Run as a module to fix relative imports
    ./venv/bin/python -m src.green_agent.server
else
    python3 -m src.green_agent.server
fi