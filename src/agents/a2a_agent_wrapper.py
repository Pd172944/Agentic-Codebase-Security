"""A2A protocol wrapper for evaluation agents."""

from pydantic_ai import Agent
from typing import Dict, AsyncGenerator
import json
import uuid
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.context import ServerCallContext
from a2a.server.events.event_queue import Event
from a2a.types import AgentCard, Message, Part, TextPart, Role, MessageSendParams, Task, TaskQueryParams, TaskIdParams, TaskPushNotificationConfig, GetTaskPushNotificationConfigParams, ListTaskPushNotificationConfigParams, DeleteTaskPushNotificationConfigParams

class WhiteAgentHandler(RequestHandler):
    def __init__(self, pydantic_agent):
        self.agent = pydantic_agent

    async def on_message_send(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> Task | Message:
        """Handle incoming message."""
        message = params.message
        
        # Extract text from message
        message_text = ""
        if message.parts:
            for part in message.parts:
                if hasattr(part.root, 'text'):
                    message_text = part.root.text
                    break
        
        # Run agent
        result = await self.agent.run(message_text)
        response_text = result.data if hasattr(result, 'data') else str(result)
        
        return Message(
            messageId=str(uuid.uuid4()),
            role=Role.agent,
            parts=[Part(root=TextPart(text=response_text))]
        )

    async def on_get_task(self, params: TaskQueryParams, context: ServerCallContext | None = None) -> Task | None:
        return None

    async def on_cancel_task(self, params: TaskIdParams, context: ServerCallContext | None = None) -> Task | None:
        return None

    async def on_message_send_stream(self, params: MessageSendParams, context: ServerCallContext | None = None) -> AsyncGenerator[Event, None]:
        yield

    async def on_set_task_push_notification_config(self, params: TaskPushNotificationConfig, context: ServerCallContext | None = None) -> TaskPushNotificationConfig:
        return params

    async def on_get_task_push_notification_config(self, params: TaskIdParams | GetTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> TaskPushNotificationConfig:
        return TaskPushNotificationConfig()

    async def on_resubscribe_to_task(self, params: TaskIdParams, context: ServerCallContext | None = None) -> AsyncGenerator[Event, None]:
        yield

    async def on_list_task_push_notification_config(self, params: ListTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> list[TaskPushNotificationConfig]:
        return []

    async def on_delete_task_push_notification_config(self, params: DeleteTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> None:
        pass

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
            system_prompt="""You are a Senior Application Security Engineer.
Your goal is to fix vulnerabilities with production-grade security patches.

**Process**:
1.  **Analyze**: Identify the specific attack vector (e.g., SQLi, XSS, Path Traversal).
2.  **Plan**: Decide on the secure pattern (e.g., Parameterization, Input Validation).
3.  **Think in Comments**: Write 1-2 lines of comments at the very top of your code explaining *why* this fix is secure.
4.  **Execute**: Write the Python code.

**Constraints**:
* Do NOT change the function signature.
* Use standard Python libraries (os, sys, shlex, html) whenever possible.
* Return ONLY valid Python code. No Markdown blocks (```python), no conversational text outside the code."""
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

    def to_a2a_server(self, host: str = "localhost", port: int = 8000, protocol: str = "http"):
        """
        Convert agent to A2A server.

        Returns:
            ASGI app for A2A protocol
        """
        import os
        
        # Determine URL: prefer AGENT_URL env var, otherwise construct from args
        agent_url = os.environ.get("AGENT_URL")
        if not agent_url:
            agent_url = f"{protocol}://{host}:{port}"

        # Create agent card
        agent_card = AgentCard(
            name=self.agent_display_name,
            description="Vulnerability Fixer Agent",
            capabilities={
                "vulnerability_fixing": {"type": "fixing"}
            },
            supported_protocols=["a2a"],
            version="1.0.0",
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            skills=[],
            url=agent_url
        )
        
        # Create handler
        handler = WhiteAgentHandler(self.agent)
        
        # Create A2A server app
        app = A2AFastAPIApplication(
            agent_card=agent_card,
            http_handler=handler
        )
        
        return app.build()


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
        model_name="anthropic:claude-3-sonnet-20240229",
        agent_display_name="Claude Sonnet 3 Vulnerability Fixer"
    )


def create_gemini_a2a_agent() -> A2AVulnerabilityFixerAgent:
    """Create Gemini A2A agent."""
    return A2AVulnerabilityFixerAgent(
        model_name="google:gemini-2.0-flash-exp",
        agent_display_name="Gemini 2.0 Flash Vulnerability Fixer"
    )
