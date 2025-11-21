"""Base agent class for AI models."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass
import time

@dataclass
class AgentResponse:
    """Response from an AI agent."""
    fixed_code: str
    raw_response: str
    time_taken: float
    input_tokens: int
    output_tokens: int
    cost: float
    model_name: str
    reasoning_effort: str = ""  # For models with extended thinking

class BaseAgent(ABC):
    """Abstract base class for AI agents."""

    def __init__(self, model_name: str, api_key: str):
        """
        Initialize agent.

        Args:
            model_name: Name of the model
            api_key: API key for authentication
        """
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    def fix_vulnerability(
        self,
        vulnerable_code: str,
        task_description: str,
        language: str,
        vulnerability: str
    ) -> AgentResponse:
        """
        Attempt to fix a code vulnerability.

        Args:
            vulnerable_code: The vulnerable code to fix
            task_description: Description of the task
            language: Programming language
            vulnerability: Description of the vulnerability

        Returns:
            AgentResponse with fixed code and metrics
        """
        pass

    def create_prompt(
        self,
        vulnerable_code: str,
        task_description: str,
        language: str,
        vulnerability: str
    ) -> str:
        """
        Create a standardized prompt for vulnerability fixing.

        Args:
            vulnerable_code: The vulnerable code
            task_description: Task description
            language: Programming language
            vulnerability: Vulnerability description

        Returns:
            Formatted prompt string
        """
        return f"""You are a security-focused code reviewer. You have been given vulnerable {language} code that needs to be fixed.

**Vulnerability**: {vulnerability}

**Task**: {task_description}

**Vulnerable Code**:
```{language.lower()}
{vulnerable_code}
```

Please provide a secure, fixed version of this code that addresses the vulnerability. Return ONLY the fixed code without any explanations or markdown formatting."""

    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pass
