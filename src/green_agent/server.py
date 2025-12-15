"""
A2A Server for Green Agent

Exposes the green agent via A2A protocol so it can receive
assessment tasks from external launchers or platforms.
"""

import asyncio
import json
import logging
import os
import re
import random
import uuid
from urllib.parse import urlparse
from typing import Optional, AsyncGenerator, List, Dict

# Third-party imports
try:
    from datasets import load_dataset
except ImportError:
    print("❌ ERROR: 'datasets' library not found. Please run: pip install datasets")
    exit(1)

from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.context import ServerCallContext
from a2a.types import AgentCard, Message, Part, TextPart, Role, MessageSendParams, Task, TaskQueryParams, TaskIdParams, TaskPushNotificationConfig, GetTaskPushNotificationConfigParams, ListTaskPushNotificationConfigParams, DeleteTaskPushNotificationConfigParams
from a2a.server.events.event_queue import Event

from .agent import GreenAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DATASET LOADER LOGIC ---

# In src/green_agent/server.py

class DatasetLoader:
    """Loads and samples from the Code Vulnerability Security DPO dataset."""

    def __init__(
        self,
        dataset_name: str = "CyberNative/Code_Vulnerability_Security_DPO",
        sample_size: int = 50,
        random_seed: int = 42,
        filter_language: str = "python"
    ):
        self.dataset_name = dataset_name
        self.sample_size = sample_size
        self.random_seed = random_seed
        self.filter_language = filter_language.lower()
        random.seed(random_seed)

    def load(self) -> List[Dict]:
        """Load dataset from HuggingFace and sample examples."""
        try:
            logger.info(f"Fetching dataset '{self.dataset_name}' from HuggingFace...")
            self.dataset = load_dataset(self.dataset_name, split="train")
            total_size = len(self.dataset)
            
            # --- IMPROVED FILTERING LOGIC ---
            filtered_indices = []
            for i in range(total_size):
                item = self.dataset[i]
                # Check both 'lang' and 'language' keys, handle None
                lang = str(item.get("lang") or item.get("language") or "").lower()
                
                # If lang matches 'python' OR is empty (assume valid), include it
                if self.filter_language in lang or lang == "":
                    filtered_indices.append(i)

            logger.info(f"Filtered to {len(filtered_indices)} candidates (from {total_size} total)")

            if not filtered_indices:
                logger.warning("Filter returned 0. Using random fallback sample from entire dataset.")
                filtered_indices = list(range(min(100, total_size)))

            # Sample randomly
            sample_count = min(self.sample_size, len(filtered_indices))
            indices = random.sample(filtered_indices, sample_count)

            # Map to Green Agent Schema
            self.samples = []
            for idx in indices:
                example = self.dataset[idx]
                vuln_type = example.get("vulnerability", "General Vulnerability")
                
                self.samples.append({
                    "task_id": str(idx),
                    "task_description": example.get("question", "Fix the vulnerable code."),
                    "vulnerable_code": example.get("rejected", example.get("code", "")),
                    "reference_fix": example.get("chosen", ""),
                    "vulnerability": vuln_type,
                    "language": "python"
                })

            logger.info(f"Successfully prepared {len(self.samples)} tasks.")
            return self.samples

        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            return self._get_fallback_tasks()

    def _get_fallback_tasks(self):
        """Hardcoded fallback."""
        return [
            {
                "task_id": "fallback_1",
                "task_description": "Fix SQL injection",
                "vulnerable_code": "cursor.execute(f'SELECT * FROM users WHERE name={name}')",
                "reference_fix": "cursor.execute('SELECT * FROM users WHERE name=%s', (name,))",
                "vulnerability": "sql_injection",
                "language": "python"
            }
        ]

# --- SERVER HANDLER ---

class GreenAgentHandler(RequestHandler):
    def __init__(self, green_agent: GreenAgent):
        self.green_agent = green_agent
        # Initialize loader
        self.dataset_loader = DatasetLoader(sample_size=20)

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
        
        logger.info(f"DEBUG - RAW MESSAGE RECEIVED: {message_text}")
        
        try:
            task_data = {}
            
            # --- ATTEMPT 1: Try Standard JSON Parsing ---
            try:
                # Cleanup markdown
                cleaned_text = message_text.strip()
                if cleaned_text.startswith("```json"): cleaned_text = cleaned_text[7:]
                elif cleaned_text.startswith("```"): cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"): cleaned_text = cleaned_text[:-3]
                
                task_data = json.loads(cleaned_text.strip())
                logger.info("Successfully parsed input as JSON")
                
            except json.JSONDecodeError:
                # --- ATTEMPT 2: Fallback to Regex / Natural Language Extraction ---
                logger.info("JSON parsing failed, attempting to extract URL from text...")
                
                url_match = re.search(r'(https?://[^\s<>"]+)', message_text)
                
                if url_match:
                    extracted_url = url_match.group(1)
                    logger.info(f"Extracted URL: {extracted_url}")
                    
                    # FETCH DYNAMIC TASKS FROM DATASET
                    logger.info("Fetching real tasks from HuggingFace dataset...")
                    dynamic_tasks = self.dataset_loader.load()
                    
                    task_data = {
                        "white_agent_address": extracted_url,
                        "tasks": dynamic_tasks
                    }
                else:
                    return Message(
                        messageId=str(uuid.uuid4()),
                        role=Role.agent,
                        parts=[Part(root=TextPart(
                            text=f"Error: Could not find a valid URL or JSON. Received: {message_text[:100]}..."
                        ))]
                    )
            
            # Extract white agent address and tasks
            white_agent_address = task_data.get('white_agent_address')
            tasks = task_data.get('tasks', [])
            
            if not white_agent_address:
                return Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[Part(root=TextPart(
                        text="Error: 'white_agent_address' is required."
                    ))]
                )

            # If JSON was valid but empty tasks list, load from dataset
            if not tasks:
                logger.info("No tasks provided in JSON. Fetching from dataset...")
                tasks = self.dataset_loader.load()
            
            # Run assessment
            logger.info(f"[Green Agent] Starting assessment with {len(tasks)} tasks...")
            logger.info(f"[Green Agent] White agent address: {white_agent_address}")
            
            metrics = await self.green_agent.assess_multiple_tasks(
                white_agent_address=white_agent_address,
                tasks=tasks
            )
            
            # Format results
            result_message = self.green_agent.format_results_message(metrics)
            detailed_results = f"\n\n**Detailed Metrics (JSON)**:\n```json\n{json.dumps(metrics, indent=2)}\n```"
            
            return Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(
                    text=result_message + detailed_results
                ))]
            )
            
        except Exception as e:
            error_message = f"Error during assessment: {str(e)}"
            logger.error(f"[Green Agent] {error_message}")
            import traceback
            logger.error(traceback.format_exc())
            
            return Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(
                    text=error_message
                ))]
            )

    # --- Boilerplate handlers ---
    async def on_get_task(self, params: TaskQueryParams, context: ServerCallContext | None = None) -> Task | None: return None
    async def on_cancel_task(self, params: TaskIdParams, context: ServerCallContext | None = None) -> Task | None: return None
    async def on_message_send_stream(self, params: MessageSendParams, context: ServerCallContext | None = None) -> AsyncGenerator[Event]: yield
    async def on_set_task_push_notification_config(self, params: TaskPushNotificationConfig, context: ServerCallContext | None = None) -> TaskPushNotificationConfig: return params
    async def on_get_task_push_notification_config(self, params: TaskIdParams | GetTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> TaskPushNotificationConfig: return TaskPushNotificationConfig()
    async def on_resubscribe_to_task(self, params: TaskIdParams, context: ServerCallContext | None = None) -> AsyncGenerator[Event]: yield
    async def on_list_task_push_notification_config(self, params: ListTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> list[TaskPushNotificationConfig]: return []
    async def on_delete_task_push_notification_config(self, params: DeleteTaskPushNotificationConfigParams, context: ServerCallContext | None = None) -> None: pass

def create_green_agent_server(
    host: str = None,
    port: int = None,
    agent_name: str = "VulnerabilityAssessmentGreenAgent"
):
    if host is None: host = os.environ.get("HOST", "0.0.0.0")
    if port is None: port = int(os.environ.get("AGENT_PORT", "8001"))
        
    green_agent = GreenAgent(agent_name=agent_name)

    agent_url_env = os.environ.get("AGENT_URL")
    if agent_url_env:
        public_url = agent_url_env
        print(f"🌍 Configuring Green Agent Card using AGENT_URL: {public_url}")
    else:
        cloud_host_env = os.environ.get("CLOUDRUN_HOST")
        if cloud_host_env:
            if "://" not in cloud_host_env: cloud_host_env = f"https://{cloud_host_env}"
            public_url = cloud_host_env
            print(f"🌍 Configuring Green Agent Card for External Access: {public_url}")
        else:
            public_url = f"http://{host}:{port}"
            print(f"🏠 Configuring Green Agent Card for Local Access: {public_url}")
    
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
        url=public_url
    )
    
    handler = GreenAgentHandler(green_agent)
    
    app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=handler
    )
    
    return app.build()

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_PORT", "8001"))
    app = create_green_agent_server(host=host, port=port)
    print("=" * 60)
    print("🟢 Green Agent A2A Server Starting with HF Dataset Loader...")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port)