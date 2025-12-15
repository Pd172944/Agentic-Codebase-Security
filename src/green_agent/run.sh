#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
# Default to port 8001 for the green agent
#export AGENT_PORT=${AGENT_PORT:-8001}
#export HOST=${HOST:-0.0.0.0}

# REPLACE 'green_agent_server.py' with the actual name of your python script if different!
python green_agent_server.py
