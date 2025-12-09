#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
# Default to port 8002 for the agent itself
export AGENT_PORT=${AGENT_PORT:-8002}
export HOST=${HOST:-0.0.0.0}

python run_white_agent.py --port $AGENT_PORT
