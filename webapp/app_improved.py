"""FastAPI web application with improved UI - Professional light theme."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict
import json
from datetime import datetime

from src.config import (
    validate_config,
    DATASET_NAME,
    SAMPLE_SIZE,
    RANDOM_SEED,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
)
from src.dataset_loader import DatasetLoader
from src.agents import GPTAgent, ClaudeAgent, GeminiAgent
from src.evaluators.llm_evaluator import LLMEvaluator
from src.evaluators.static_analyzer import StaticAnalyzer
from src.evaluators.code_executor import CodeExecutor
from src.config import GPT_MODEL, CLAUDE_MODEL, GEMINI_MODEL
from src.utils.logger import setup_logger

# Import demo mode
try:
    from webapp.demo_mode import run_demo_evaluation
    DEMO_MODE_AVAILABLE = True
except ImportError:
    DEMO_MODE_AVAILABLE = False

logger = setup_logger("webapp")

app = FastAPI(title="AI Agent Vulnerability Evaluation")

# Global state
evaluation_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_example": None,
    "current_agent": None,
    "results": [],
    "samples": []  # Store samples with full code for visualization
}

class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

manager = ConnectionManager()

@app.get("/")
async def root():
    """Serve the main UI."""
    return HTMLResponse(content=get_html_content(), status_code=200)

@app.get("/api/status")
async def get_status():
    """Get current evaluation status."""
    return JSONResponse(content=evaluation_state)

@app.get("/api/sample/{sample_id}")
async def get_sample(sample_id: int):
    """Get detailed sample information."""
    for sample in evaluation_state.get("samples", []):
        if sample["id"] == sample_id:
            return JSONResponse(content=sample)
    return JSONResponse(content={"error": "Sample not found"}, status_code=404)

@app.post("/api/start")
async def start_evaluation(sample_count: int = 10):
    """Start evaluation with specified sample count."""
    global evaluation_state

    if evaluation_state["running"]:
        return JSONResponse(
            content={"error": "Evaluation already running"},
            status_code=400
        )

    # Reset state
    evaluation_state = {
        "running": True,
        "progress": 0,
        "total": 0,
        "current_example": None,
        "current_agent": None,
        "results": [],
        "samples": [],
        "start_time": datetime.now().isoformat(),
    }

    # Run evaluation in background
    asyncio.create_task(run_evaluation(sample_count))

    return JSONResponse(content={"status": "started"})

@app.post("/api/stop")
async def stop_evaluation():
    """Stop running evaluation."""
    evaluation_state["running"] = False
    return JSONResponse(content={"status": "stopped"})

@app.post("/api/start_demo")
async def start_demo_evaluation(sample_count: int = 5):
    """Start demo evaluation with mock data."""
    global evaluation_state

    if not DEMO_MODE_AVAILABLE:
        return JSONResponse(
            content={"error": "Demo mode not available"},
            status_code=400
        )

    if evaluation_state["running"]:
        return JSONResponse(
            content={"error": "Evaluation already running"},
            status_code=400
        )

    # Reset state
    evaluation_state = {
        "running": True,
        "progress": 0,
        "total": 0,
        "current_example": None,
        "current_agent": None,
        "results": [],
        "samples": [],
        "start_time": datetime.now().isoformat(),
    }

    # Run demo in background
    asyncio.create_task(run_demo_with_samples(sample_count))

    return JSONResponse(content={"status": "started", "mode": "demo"})

async def run_demo_with_samples(sample_count: int):
    """Run demo and populate samples."""
    from webapp.demo_mode import DEMO_SAMPLES

    # Store samples
    evaluation_state["samples"] = DEMO_SAMPLES[:sample_count]

    # Broadcast samples
    await manager.broadcast({
        "type": "samples",
        "data": evaluation_state["samples"]
    })

    # Run demo evaluation
    await run_demo_evaluation(manager.broadcast, sample_count)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "status",
            "data": evaluation_state
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"ack: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_evaluation(sample_count: int):
    """Run evaluation pipeline with real-time updates."""
    global evaluation_state

    try:
        # Validate config
        validate_config()

        # Broadcast start message
        await manager.broadcast({
            "type": "log",
            "data": f"Starting evaluation with {sample_count} Python samples..."
        })

        # Load dataset (Python only)
        dataset_loader = DatasetLoader(
            DATASET_NAME,
            sample_count,
            RANDOM_SEED,
            filter_language="Python"
        )

        await manager.broadcast({
            "type": "log",
            "data": "Loading dataset from HuggingFace..."
        })

        samples = dataset_loader.load()
        evaluation_state["samples"] = samples

        # Broadcast samples
        await manager.broadcast({
            "type": "samples",
            "data": samples
        })

        await manager.broadcast({
            "type": "log",
            "data": f"Loaded {len(samples)} Python examples"
        })

        # Initialize agents
        agents = {
            "GPT-4o": GPTAgent(GPT_MODEL, OPENAI_API_KEY),
            "Claude-Sonnet-4": ClaudeAgent(CLAUDE_MODEL, ANTHROPIC_API_KEY),
            "Gemini-2.0-Flash": GeminiAgent(GEMINI_MODEL, GOOGLE_API_KEY),
        }

        # Initialize evaluators
        llm_evaluator = LLMEvaluator(OPENAI_API_KEY)
        static_analyzer = StaticAnalyzer()
        code_executor = CodeExecutor()

        # Calculate total
        total_evaluations = len(samples) * len(agents)
        evaluation_state["total"] = total_evaluations

        await manager.broadcast({
            "type": "status",
            "data": evaluation_state
        })

        # Evaluate each sample
        progress = 0
        for sample in samples:
            for agent_name, agent in agents.items():
                if not evaluation_state["running"]:
                    await manager.broadcast({
                        "type": "log",
                        "data": "Evaluation stopped by user"
                    })
                    return

                # Update state
                evaluation_state["current_example"] = sample["id"]
                evaluation_state["current_agent"] = agent_name
                evaluation_state["progress"] = progress

                await manager.broadcast({
                    "type": "status",
                    "data": evaluation_state
                })

                await manager.broadcast({
                    "type": "log",
                    "data": f"Evaluating {agent_name} on example {sample['id']}..."
                })

                # Run evaluation
                result = await evaluate_single(
                    sample, agent_name, agent,
                    llm_evaluator, static_analyzer, code_executor
                )

                # Store result
                evaluation_state["results"].append(result)

                # Broadcast result
                await manager.broadcast({
                    "type": "result",
                    "data": result
                })

                progress += 1

        # Complete
        evaluation_state["running"] = False
        evaluation_state["progress"] = total_evaluations
        evaluation_state["end_time"] = datetime.now().isoformat()

        await manager.broadcast({
            "type": "complete",
            "data": evaluation_state
        })

        await manager.broadcast({
            "type": "log",
            "data": f"Evaluation complete! Processed {len(samples)} samples with {len(agents)} agents."
        })

    except Exception as e:
        logger.error(f"Evaluation error: {e}", exc_info=True)
        evaluation_state["running"] = False
        await manager.broadcast({
            "type": "error",
            "data": str(e)
        })

async def evaluate_single(
    sample: dict,
    agent_name: str,
    agent,
    llm_evaluator,
    static_analyzer,
    code_executor
) -> dict:
    """Evaluate single example (async wrapper)."""
    # Agent fix
    agent_response = agent.fix_vulnerability(
        sample["vulnerable_code"],
        sample["task_description"],
        sample["language"],
        sample["vulnerability"]
    )

    # LLM evaluation
    llm_eval = llm_evaluator.evaluate(
        sample["fixed_code"],
        agent_response.fixed_code,
        sample["vulnerability"],
        sample["language"]
    )

    # Static analysis
    static_before = static_analyzer.analyze(sample["vulnerable_code"], "Python")
    static_after = static_analyzer.analyze(agent_response.fixed_code, "Python")
    static_comp = static_analyzer.compare_vulnerabilities(static_before, static_after)

    # Code execution
    exec_result = code_executor.execute(agent_response.fixed_code, "Python")

    return {
        "example_id": sample["id"],
        "agent_name": agent_name,
        "vulnerability": sample["vulnerability"],
        "agent_fixed_code": agent_response.fixed_code,
        "similarity_score": llm_eval.similarity_score,
        "vulnerability_fixed": llm_eval.vulnerability_fixed,
        "static_analysis_pass": static_comp.get("vulnerabilities_reduced", False),
        "code_executes": exec_result.success,
        "time_taken": agent_response.time_taken,
        "cost": agent_response.cost,
    }

def get_html_content() -> str:
    """Get HTML content for the UI."""
    # This will be filled in the next message - file is getting too long
    pass

if __name__ == "__main__":
    import uvicorn
    print("Starting AI Agent Vulnerability Evaluation Web App...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
