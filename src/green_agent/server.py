"""
A2A Server for Green Agent

Exposes the green agent via A2A protocol so it can receive
assessment tasks from external launchers or platforms.
"""

import asyncio
import json
from typing import Optional
from a2a_sdk import create_a2a_server, AgentCard, Message, Part, TextPart, Role

from .agent import GreenAgent


def create_green_agent_server(
    host: str = "0.0.0.0",
    port: int = 8001,
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
    # Initialize green agent
    green_agent = GreenAgent(agent_name=agent_name)
    
    # Create agent card (metadata about the agent)
    agent_card = AgentCard(
        name=agent_name,
        description="Green agent for assessing code vulnerability fixing capabilities",
        capabilities=[
            "vulnerability_assessment",
            "code_evaluation",
            "security_testing"
        ],
        supported_protocols=["a2a"],
        version="1.0.0"
    )
    
    async def handle_message(message: Message, context_id: Optional[str] = None) -> Message:
        """
        Handle incoming A2A messages.
        
        Expected message format:
        {
            "white_agent_address": "http://localhost:8002",
            "tasks": [
                {
                    "vulnerable_code": "...",
                    "reference_fix": "...",
                    "task_description": "...",
                    "vulnerability": "...",
                    "language": "python"
                }
            ]
        }
        """
        try:
            # Extract text from message
            message_text = ""
            if message.parts:
                for part in message.parts:
                    if hasattr(part.root, 'text'):
                        message_text = part.root.text
                        break
            
            # Parse message as JSON
            try:
                task_data = json.loads(message_text)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text request
                return Message(
                    role=Role.agent,
                    parts=[Part(root=TextPart(
                        kind='text',
                        text="Error: Expected JSON format with 'white_agent_address' and 'tasks' fields"
                    ))],
                    context_id=context_id
                )
            
            # Extract white agent address and tasks
            white_agent_address = task_data.get('white_agent_address')
            tasks = task_data.get('tasks', [])
            
            if not white_agent_address or not tasks:
                return Message(
                    role=Role.agent,
                    parts=[Part(root=TextPart(
                        kind='text',
                        text="Error: Missing 'white_agent_address' or 'tasks' in request"
                    ))],
                    context_id=context_id
                )
            
            # Run assessment
            print(f"[Green Agent] Starting assessment with {len(tasks)} tasks...")
            print(f"[Green Agent] White agent address: {white_agent_address}")
            
            metrics = await green_agent.assess_multiple_tasks(
                white_agent_address=white_agent_address,
                tasks=tasks
            )
            
            # Format results
            result_message = green_agent.format_results_message(metrics)
            
            # Add detailed metrics as JSON
            detailed_results = f"\n\n**Detailed Metrics (JSON)**:\n```json\n{json.dumps(metrics, indent=2)}\n```"
            
            return Message(
                role=Role.agent,
                parts=[Part(root=TextPart(
                    kind='text',
                    text=result_message + detailed_results
                ))],
                context_id=context_id
            )
            
        except Exception as e:
            error_message = f"Error during assessment: {str(e)}"
            print(f"[Green Agent] {error_message}")
            import traceback
            traceback.print_exc()
            
            return Message(
                role=Role.agent,
                parts=[Part(root=TextPart(
                    kind='text',
                    text=error_message
                ))],
                context_id=context_id
            )
    
    # Create A2A server
    app = create_a2a_server(
        agent_card=agent_card,
        message_handler=handle_message
    )
    
    return app


if __name__ == "__main__":
    """Run green agent server standalone."""
    import uvicorn
    
    app = create_green_agent_server()
    
    print("=" * 60)
    print("🟢 Green Agent A2A Server Starting...")
    print("=" * 60)
    print("Address: http://localhost:8001")
    print("Protocol: A2A (Agent-to-Agent)")
    print("Purpose: Vulnerability Assessment")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)

