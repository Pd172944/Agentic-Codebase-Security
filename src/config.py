"""Configuration module for API keys and settings."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Model configurations
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# Evaluation settings
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", "100"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))

# Dataset configuration
DATASET_NAME = "CyberNative/Code_Vulnerability_Security_DPO"

# Results directory
RESULTS_DIR = "results"
LOGS_DIR = "logs"

# Cost per 1M tokens (approximate, update as needed)
COST_PER_1M_TOKENS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "gemini-2.0-flash-exp": {"input": 0.075, "output": 0.30},
}

def validate_config():
    """Validate that at least one API key is present."""
    available_keys = []

    if OPENAI_API_KEY:
        available_keys.append("OPENAI_API_KEY")
    if ANTHROPIC_API_KEY:
        available_keys.append("ANTHROPIC_API_KEY")
    if GOOGLE_API_KEY:
        available_keys.append("GOOGLE_API_KEY")

    if not available_keys:
        raise ValueError(
            "No API keys found. Please set at least one API key in your .env file: "
            "OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY"
        )

    return True

def get_available_agents():
    """Return list of agents that have API keys configured."""
    available = []
    if OPENAI_API_KEY:
        available.append("GPT-4o")
    if ANTHROPIC_API_KEY:
        available.append("Claude-Sonnet-4")
    if GOOGLE_API_KEY:
        available.append("Gemini-2.0-Flash")
    return available
