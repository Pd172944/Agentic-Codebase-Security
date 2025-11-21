"""Startup script for the web application."""

import sys
import os
from pathlib import Path

# Add webapp to path
sys.path.insert(0, str(Path(__file__).parent / "webapp"))
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_env_file():
    """Check if .env file exists and has required keys."""
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("WARNING: .env file not found!")
        print("The app will run in DEMO MODE only.")
        print("\nTo enable real evaluations:")
        print("1. Copy .env.example to .env")
        print("2. Add your API keys to .env")
        return False

    # Check for API keys
    from dotenv import load_dotenv
    load_dotenv()

    missing = []
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        if not os.getenv(key):
            missing.append(key)

    if missing:
        print(f"WARNING: Missing API keys: {', '.join(missing)}")
        print("The app will run in DEMO MODE only.")
        return False

    return True

def main():
    """Run the web application."""
    print("=" * 80)
    print("AI Agent Vulnerability Evaluation - Web Application")
    print("=" * 80)
    print()

    has_api_keys = check_env_file()

    if has_api_keys:
        print("Status: Real evaluation mode enabled")
    else:
        print("Status: Demo mode only (no API keys)")

    print()
    print("Starting server...")
    print("Open http://localhost:8000 in your browser")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)

    # Import and run the app
    import uvicorn
    from webapp.app import app

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
