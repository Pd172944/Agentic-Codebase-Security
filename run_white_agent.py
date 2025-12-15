#!/usr/bin/env python3
import uvicorn
import os
import argparse
import sys
from urllib.parse import urlparse
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

    # --- NEW LOGIC: DETECT CLOUDFLARE ---
    cloud_host_env = os.getenv("CLOUDRUN_HOST")
    
    if cloud_host_env:
        # If the env var is set (e.g., https://xyz.trycloudflare.com)
        # We must parse it to separate protocol (https) from host (xyz...)
        if "://" not in cloud_host_env:
            cloud_host_env = f"https://{cloud_host_env}"
            
        parsed = urlparse(cloud_host_env)
        public_host = parsed.hostname
        public_protocol = parsed.scheme
        public_port = 443  # Cloudflare tunnels always use 443 for HTTPS
        
        print(f"🌍 Configuring Agent Card for External Access: {public_protocol}://{public_host}:{public_port}")
        
        # Pass these to the wrapper so the JSON card is correct
        app = agent_wrapper.to_a2a_server(
            host=public_host, 
            port=public_port, 
            protocol=public_protocol
        )
    else:
        # Fallback to local defaults if no tunnel is detected
        print(f"🏠 Configuring Agent Card for Local Access: http://localhost:{args.port}")
        app = agent_wrapper.to_a2a_server(
            host="localhost",
            port=args.port,
            protocol="http"
        )
    # ------------------------------------

    print(f"Starting {args.agent} agent server locally on http://{args.host}:{args.port}")
    
    # We still run uvicorn on the local port, because the tunnel forwards traffic HERE.
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()