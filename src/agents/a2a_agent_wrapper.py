"""A2A protocol wrapper for evaluation agents."""

from pydantic_ai import Agent
from typing import Dict
import json

class A2AVulnerabilityFixerAgent:
    """A2A-compliant agent wrapper for vulnerability fixing."""

    def __init__(self, model_name: str, agent_display_name: str):
        """
        Initialize A2A agent wrapper.

        Args:
            model_name: Model identifier (e.g., "openai:gpt-4o")
            agent_display_name: Display name for the agent
        """
        self.model_name = model_name
        self.agent_display_name = agent_display_name

        # Create Pydantic AI agent with security-focused instructions
        self.agent = Agent(
            model_name,
            system_prompt="""You are a security expert specializing in fixing code vulnerabilities.

When given vulnerable code and a task description, you must:
1. Analyze the security vulnerability
2. Provide a fixed version of the code that addresses the vulnerability
3. Return ONLY the fixed code without explanations or markdown

Be precise and focus on security best practices."""
        )

    def create_task_prompt(
        self,
        vulnerable_code: str,
        task_description: str,
        vulnerability: str
    ) -> str:
        """
        Create prompt for vulnerability fixing task.

        Args:
            vulnerable_code: The vulnerable code
            task_description: Task description
            vulnerability: Vulnerability description

        Returns:
            Formatted prompt
        """
        return f"""**Vulnerability**: {vulnerability}

**Task**: {task_description}

**Vulnerable Code**:
```python
{vulnerable_code}
```

Provide a secure, fixed version of this code. Return ONLY the fixed Python code."""

    async def fix_vulnerability(
        self,
        vulnerable_code: str,
        task_description: str,
        vulnerability: str
    ) -> str:
        """
        Fix vulnerability using A2A agent.

        Args:
            vulnerable_code: The vulnerable code
            task_description: Task description
            vulnerability: Vulnerability description

        Returns:
            Fixed code
        """
        prompt = self.create_task_prompt(
            vulnerable_code, task_description, vulnerability
        )

        # Run agent asynchronously
        result = await self.agent.run(prompt)

        # Extract text from result
        return result.data if hasattr(result, 'data') else str(result)

    def to_a2a_server(self):
        """
        Convert agent to A2A server.

        Returns:
            ASGI app for A2A protocol
        """
        return self.agent.to_a2a()


# Pre-configured A2A agents for each model
def create_gpt_a2a_agent() -> A2AVulnerabilityFixerAgent:
    """Create GPT A2A agent."""
    return A2AVulnerabilityFixerAgent(
        model_name="openai:gpt-4o",
        agent_display_name="GPT-4o Vulnerability Fixer"
    )


def create_claude_a2a_agent() -> A2AVulnerabilityFixerAgent:
    """Create Claude A2A agent."""
    return A2AVulnerabilityFixerAgent(
        model_name="anthropic:claude-sonnet-4-20250514",
        agent_display_name="Claude Sonnet 4 Vulnerability Fixer"
    )


def create_gemini_a2a_agent() -> A2AVulnerabilityFixerAgent:
    """Create Gemini A2A agent."""
    return A2AVulnerabilityFixerAgent(
        model_name="google:gemini-2.0-flash-exp",
        agent_display_name="Gemini 2.0 Flash Vulnerability Fixer"
    )
