"""
A2A Server for Green Agent

Exposes the green agent via A2A protocol so it can receive
assessment tasks from external launchers or platforms.
"""

import asyncio
import json
import logging
from typing import Optional, AsyncGenerator
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.context import ServerCallContext
from a2a.types import AgentCard, Message, Part, TextPart, Role, MessageSendParams, Task, TaskQueryParams, TaskIdParams, TaskPushNotificationConfig, GetTaskPushNotificationConfigParams, ListTaskPushNotificationConfigParams, DeleteTaskPushNotificationConfigParams
from a2a.server.events.event_queue import Event

from .agent import GreenAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GreenAgentHandler(RequestHandler):
    def __init__(self, green_agent: GreenAgent):
        self.green_agent = green_agent

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
        
        logger.info(f"Received message: {message_text[:100]}...")
        
        try:
            # Parse message as JSON
            try:
                task_data = json.loads(message_text)
            except json.JSONDecodeError:
                return Message(
                    role=Role.agent,
                    parts=[Part(root=TextPart(
                        text="Error: Expected JSON format with 'white_agent_address' and 'tasks' fields"
                    ))]
                )
            
            # Extract white agent address and tasks
            white_agent_address = task_data.get('white_agent_address')
            tasks = task_data.get('tasks', [])
            
            if not white_agent_address or not tasks:
                return Message(
                    role=Role.agent,
                    parts=[Part(root=TextPart(
                        text="Error: Missing 'white_agent_address' or 'tasks' in request"
                    ))]
                )
            
            # Run assessment
            print(f"[Green Agent] Starting assessment with {len(tasks)} tasks...")
            print(f"[Green Agent] White agent address: {white_agent_address}")
            
            metrics = await self.green_agent.assess_multiple_tasks(
                white_agent_address=white_agent_address,
                tasks=tasks
            )
            
            # Format results
            result_message = self.green_agent.format_results_message(metrics)
            
            # Add detailed metrics as JSON
            detailed_results = f"\n\n**Detailed Metrics (JSON)**:\n```json\n{json.dumps(metrics, indent=2)}\n```"
            
            return Message(
                role=Role.agent,
                parts=[Part(root=TextPart(
                    text=result_message + detailed_results
                ))]
            )
            
        except Exception as e:
            error_message = f"Error during assessment: {str(e)}"
            print(f"[Green Agent] {error_message}")
            import traceback
            traceback.print_exc()
            
            return Message(
                role=Role.agent,
                parts=[Part(root=TextPart(
                    text=error_message
                ))]
            )

    async def on_get_task(self, params: TaskQueryParams, context: ServerCallContext | None = None) -> Task | None:
        return None

    async def on_cancel_task(self, params: TaskIdParams, context: ServerCallContext | None = None) -> Task | None:
        return None

    async def on_message_send_stream(self, params: MessageSendParams, context: ServerCallContext | None = None) -> AsyncGenerator[Event]:
        yield

    async def on_set_task_push_notification_config(self, params: TaskPushNotificationConfig, context: ServerCallContext | None = None) -> TaskPushNotificationConfig:
        return params

    async def on_get_task_push_notification_config(self, params: TaskIdParams | GetTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> TaskPushNotificationConfig:
        return TaskPushNotificationConfig()

    async def on_resubscribe_to_task(self, params: TaskIdParams, context: ServerCallContext | None = None) -> AsyncGenerator[Event]:
        yield

    async def on_list_task_push_notification_config(self, params: ListTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> list[TaskPushNotificationConfig]:
        return []

    async def on_delete_task_push_notification_config(self, params: DeleteTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> None:
        pass

def create_green_agent_server(
    host: str = None,
    port: int = None,
    agent_name: str = "VulnerabilityAssessmentGreenAgent"
):
    """
    Create an A2A server for the green agent.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        agent_name: Display name for the agent
        
    Returns:
        ASGI application
    """
    import os
    
    # Use environment variables if arguments are not provided (Controller support)
    if host is None:
        host = os.environ.get("HOST", "0.0.0.0")
    if port is None:
        port = int(os.environ.get("AGENT_PORT", "8001"))
        
    # Initialize green agent
    green_agent = GreenAgent(agent_name=agent_name)
    
    # Create agent card (metadata about the agent)
    # Note: AgentCapabilities needs to be a proper object, not just a list
    agent_card = AgentCard(
        name=agent_name,
        description="Green agent for assessing code vulnerability fixing capabilities",
        capabilities={
            "vulnerability_assessment": {"type": "assessment"},
            "code_evaluation": {"type": "evaluation"},
            "security_testing": {"type": "testing"}
        },
        supported_protocols=["a2a"],
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[],
        url=f"http://{host}:{port}"
    )
    
    # Create handler
    handler = GreenAgentHandler(green_agent)
    
    # Create A2A server app
    app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=handler
    )
    
    # A2AFastAPIApplication IS the app instance (it inherits from FastAPI)
    # or it has a .build() method to get the app.
    # Checking the SDK code, it has a build() method.
    return app.build()

if __name__ == "__main__":
    """Run green agent server standalone."""
    import uvicorn
    import os
    
    # Default to environment variables or fallback values
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_PORT", "8001"))
    
    # Need to instantiate the app to run it
    app_instance = create_green_agent_server(host=host, port=port)
    
    print("=" * 60)
    print("🟢 Green Agent A2A Server Starting...")
    print("=" * 60)
    print(f"Address: http://{host}:{port}")
    print("Protocol: A2A (Agent-to-Agent)")
    print("Purpose: Vulnerability Assessment")
    print("=" * 60)
    
    uvicorn.run(app_instance, host=host, port=port)


    
    if __name__ == "__main__":
        """Run green agent server standalone."""
        import uvicorn
        import os
        
        # Default to environment variables or fallback values
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("AGENT_PORT", "8001"))
        
        app = create_green_agent_server(host=host, port=port)
        
        print("=" * 60)
        print("🟢 Green Agent A2A Server Starting...")
        print("=" * 60)
        print(f"Address: http://{host}:{port}")
        print("Protocol: A2A (Agent-to-Agent)")
        print("Purpose: Vulnerability Assessment")
        print("=" * 60)
        
        uvicorn.run(app, host=host, port=port)

