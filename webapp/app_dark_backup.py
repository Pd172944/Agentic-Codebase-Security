"""FastAPI web application for AI agent vulnerability evaluation."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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
    logger.warning("Demo mode not available")

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
}

class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

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
        "start_time": datetime.now().isoformat(),
    }

    # Run demo in background
    asyncio.create_task(run_demo_evaluation(manager.broadcast, sample_count))

    return JSONResponse(content={"status": "started", "mode": "demo"})

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
            # Echo back for keepalive
            await websocket.send_text(f"ack: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_evaluation(sample_count: int):
    """
    Run evaluation pipeline with real-time updates.

    Args:
        sample_count: Number of samples to evaluate
    """
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
        "vulnerability": sample["vulnerability"][:100],
        "similarity_score": llm_eval.similarity_score,
        "vulnerability_fixed": llm_eval.vulnerability_fixed,
        "static_analysis_pass": static_comp.get("vulnerabilities_reduced", False),
        "code_executes": exec_result.success,
        "time_taken": agent_response.time_taken,
        "cost": agent_response.cost,
    }

def get_html_content() -> str:
    """Get HTML content for the UI."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Vulnerability Evaluation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { opacity: 0.9; font-size: 1.1em; }
        .controls {
            background: #1e293b;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
        }
        input[type="number"] {
            padding: 10px;
            border-radius: 6px;
            border: 2px solid #475569;
            background: #0f172a;
            color: #e2e8f0;
            font-size: 16px;
            width: 120px;
        }
        button {
            padding: 12px 24px;
            border-radius: 6px;
            border: none;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-start {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }
        .btn-start:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(16, 185, 129, 0.4); }
        .btn-stop {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
        }
        .btn-stop:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(239, 68, 68, 0.4); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #334155;
        }
        .card h3 { margin-bottom: 15px; color: #94a3b8; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }
        .progress-bar {
            background: #0f172a;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }
        .log-container {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .log-entry {
            padding: 4px 0;
            border-bottom: 1px solid #1e293b;
        }
        .results-table {
            width: 100%;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; }
        th {
            background: #0f172a;
            color: #94a3b8;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        tr:hover { background: #334155; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-success { background: #10b981; color: white; }
        .badge-danger { background: #ef4444; color: white; }
        .badge-warning { background: #f59e0b; color: white; }
        .status { font-size: 1.2em; margin: 10px 0; }
        .metric { font-size: 2em; font-weight: 700; color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI Agent Vulnerability Evaluation</h1>
            <div class="subtitle">Real-time evaluation of GPT-4o, Claude Sonnet 4, and Gemini 2.0 Flash on Python security vulnerabilities</div>
        </header>

        <div class="controls">
            <label>Sample Count:</label>
            <input type="number" id="sampleCount" value="5" min="1" max="100">
            <button class="btn-start" onclick="startEvaluation()">Start Real Evaluation</button>
            <button class="btn-start" onclick="startDemo()" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">Start Demo</button>
            <button class="btn-stop" onclick="stopEvaluation()">Stop</button>
            <span id="statusText" class="status">Ready</span>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Progress</h3>
                <div id="progressText" class="metric">0 / 0</div>
                <div class="progress-bar">
                    <div id="progressBar" class="progress-fill" style="width: 0%">0%</div>
                </div>
            </div>
            <div class="card">
                <h3>Current Task</h3>
                <div id="currentTask" style="margin-top: 10px; font-size: 1.1em;">Waiting to start...</div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 20px;">
            <h3>Logs</h3>
            <div id="logs" class="log-container"></div>
        </div>

        <div class="card">
            <h3>Results</h3>
            <div class="results-table">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Agent</th>
                            <th>Vulnerability</th>
                            <th>Similarity</th>
                            <th>Fixed?</th>
                            <th>Static</th>
                            <th>Runs?</th>
                            <th>Time (s)</th>
                            <th>Cost ($)</th>
                        </tr>
                    </thead>
                    <tbody id="resultsBody">
                        <tr><td colspan="9" style="text-align: center; opacity: 0.5;">No results yet</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let ws = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                addLog('Connected to server');
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleMessage(message);
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                setTimeout(connectWebSocket, 3000);
            };
        }

        function handleMessage(message) {
            if (message.type === 'status') {
                updateStatus(message.data);
            } else if (message.type === 'log') {
                addLog(message.data);
            } else if (message.type === 'result') {
                addResult(message.data);
            } else if (message.type === 'complete') {
                addLog('Evaluation complete!');
                document.getElementById('statusText').textContent = 'Complete';
            } else if (message.type === 'error') {
                addLog('ERROR: ' + message.data);
            }
        }

        function updateStatus(state) {
            const progress = state.progress || 0;
            const total = state.total || 0;
            const pct = total > 0 ? Math.round((progress / total) * 100) : 0;

            document.getElementById('progressText').textContent = `${progress} / ${total}`;
            document.getElementById('progressBar').style.width = `${pct}%`;
            document.getElementById('progressBar').textContent = `${pct}%`;

            if (state.running) {
                document.getElementById('statusText').textContent = 'Running...';
                if (state.current_agent && state.current_example !== null) {
                    document.getElementById('currentTask').textContent =
                        `${state.current_agent} on example #${state.current_example}`;
                }
            }
        }

        function addLog(text) {
            const logs = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
        }

        function addResult(result) {
            const tbody = document.getElementById('resultsBody');
            if (tbody.children[0]?.colSpan === 9) {
                tbody.innerHTML = '';
            }

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${result.example_id}</td>
                <td>${result.agent_name}</td>
                <td style="font-size: 0.85em;">${result.vulnerability}</td>
                <td>${result.similarity_score.toFixed(1)}/10</td>
                <td><span class="badge ${result.vulnerability_fixed ? 'badge-success' : 'badge-danger'}">
                    ${result.vulnerability_fixed ? 'Yes' : 'No'}</span></td>
                <td><span class="badge ${result.static_analysis_pass ? 'badge-success' : 'badge-warning'}">
                    ${result.static_analysis_pass ? 'Pass' : 'N/A'}</span></td>
                <td><span class="badge ${result.code_executes ? 'badge-success' : 'badge-danger'}">
                    ${result.code_executes ? 'Yes' : 'No'}</span></td>
                <td>${result.time_taken.toFixed(2)}</td>
                <td>${result.cost.toFixed(4)}</td>
            `;
            tbody.appendChild(row);
        }

        async function startEvaluation() {
            const sampleCount = parseInt(document.getElementById('sampleCount').value);
            const response = await fetch(`/api/start?sample_count=${sampleCount}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.error) {
                addLog('ERROR: ' + data.error);
            } else {
                addLog('Starting evaluation...');
                document.getElementById('resultsBody').innerHTML =
                    '<tr><td colspan="9" style="text-align: center; opacity: 0.5;">Loading...</td></tr>';
            }
        }

        async function stopEvaluation() {
            await fetch('/api/stop', { method: 'POST' });
            addLog('Stopping evaluation...');
        }

        async function startDemo() {
            const sampleCount = parseInt(document.getElementById('sampleCount').value);
            const response = await fetch(`/api/start_demo?sample_count=${sampleCount}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.error) {
                addLog('ERROR: ' + data.error);
            } else {
                addLog('Starting DEMO evaluation...');
                document.getElementById('resultsBody').innerHTML =
                    '<tr><td colspan="9" style="text-align: center; opacity: 0.5;">Loading demo...</td></tr>';
            }
        }

        // Connect on load
        connectWebSocket();
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    print("Starting AI Agent Vulnerability Evaluation Web App...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
