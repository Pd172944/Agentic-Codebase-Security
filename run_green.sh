#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
export AGENT_PORT=${AGENT_PORT:-8001}
export HOST=${HOST:-0.0.0.0}

python src/green_agent/server.py

