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
    """Validate that all required API keys are present."""
    missing_keys = []

    if not OPENAI_API_KEY:
        missing_keys.append("OPENAI_API_KEY")
    if not ANTHROPIC_API_KEY:
        missing_keys.append("ANTHROPIC_API_KEY")
    if not GOOGLE_API_KEY:
        missing_keys.append("GOOGLE_API_KEY")

    if missing_keys:
        raise ValueError(
            f"Missing required API keys: {', '.join(missing_keys)}. "
            "Please set them in your .env file."
        )

    return True
