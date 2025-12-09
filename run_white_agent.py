#!/usr/bin/env python3
import uvicorn
import os
import argparse
import sys
from dotenv import load_dotenv

# Add current directory to path so we can import src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.a2a_agent_wrapper import (
    create_gpt_a2a_agent,
    create_claude_a2a_agent,
    create_gemini_a2a_agent
)

def main():
    # Load environment variables (API keys)
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run White Agent A2A Server")
    parser.add_argument("--agent", choices=["gpt", "claude", "gemini"], default="gpt", help="Agent model to run")
    parser.add_argument("--port", type=int, default=8002, help="Port to run on (default: 8002)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to run on")
    
    args = parser.parse_args()
    
    print(f"Initializing {args.agent} agent...")
    
    # Select and create the agent wrapper based on argument
    if args.agent == "gpt":
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY not found in environment")
            return
        agent_wrapper = create_gpt_a2a_agent()
    elif args.agent == "claude":
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("Error: ANTHROPIC_API_KEY not found in environment")
            return
        agent_wrapper = create_claude_a2a_agent()
    elif args.agent == "gemini":
        if not os.getenv("GOOGLE_API_KEY"):
            print("Error: GOOGLE_API_KEY not found in environment")
            return
        agent_wrapper = create_gemini_a2a_agent()
        
    print(f"Starting {args.agent} agent server on http://{args.host}:{args.port}")
    
    # Get the ASGI app from the wrapper and run it
    app = agent_wrapper.to_a2a_server()
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()


