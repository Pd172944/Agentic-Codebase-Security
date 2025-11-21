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
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Vulnerability Evaluation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', sans-serif; background: #f8f9fa; color: #1e293b; padding: 20px; }
        .container { max-width: 1600px; margin: 0 auto; }
        header { background: linear-gradient(135deg, #1e40af 0%, #0f172a 100%); color: white; padding: 30px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        h1 { font-size: 2em; margin-bottom: 8px; font-weight: 600; }
        .subtitle { opacity: 0.9; font-size: 0.95em; font-weight: 400; }
        .controls { background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        input[type="number"] { padding: 10px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 14px; width: 100px; }
        button { padding: 10px 20px; border: none; border-radius: 4px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: #1e40af; color: white; }
        .btn-primary:hover { background: #1e3a8a; box-shadow: 0 2px 4px rgba(30,64,175,0.3); }
        .btn-warning { background: #f59e0b; color: white; }
        .btn-warning:hover { background: #d97706; box-shadow: 0 2px 4px rgba(245,158,11,0.3); }
        .btn-danger { background: #dc2626; color: white; }
        .btn-danger:hover { background: #b91c1c; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
        .card h3 { color: #475569; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 15px; font-weight: 600; }
        .metric { font-size: 2em; font-weight: 600; color: #0f172a; }
        .progress-bar { background: #e2e8f0; height: 28px; border-radius: 6px; overflow: hidden; margin-top: 10px; }
        .progress-fill { background: linear-gradient(90deg, #1e40af 0%, #3b82f6 100%); height: 100%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-weight: 500; font-size: 0.85em; }
        .log-container { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 15px; height: 200px; overflow-y: auto; font-family: 'SF Mono', 'Monaco', 'Courier New', monospace; font-size: 12px; }
        .log-entry { padding: 4px 0; color: #64748b; border-bottom: 1px solid #f1f5f9; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f8fafc; color: #64748b; font-weight: 600; font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.5px; padding: 12px; text-align: left; border-bottom: 2px solid #e2e8f0; }
        td { padding: 12px; border-bottom: 1px solid #f1f5f9; font-size: 0.9em; }
        tr:hover { background: #f8fafc; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 3px; font-size: 0.8em; font-weight: 500; }
        .badge-success { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .badge-danger { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        .badge-warning { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
        .badge-info { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
        .status { font-size: 1.1em; color: #1e40af; font-weight: 600; }
        .vuln-code { background: #fef3c7; padding: 3px 6px; border-radius: 3px; font-family: 'SF Mono', monospace; font-size: 0.85em; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(2px); }
        .modal-content { background: white; margin: 3% auto; padding: 0; border-radius: 8px; width: 90%; max-width: 1200px; max-height: 90vh; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04); }
        .modal-header { background: linear-gradient(135deg, #1e40af 0%, #0f172a 100%); color: white; padding: 24px 30px; border-bottom: 1px solid #e2e8f0; }
        .modal-header h2 { font-size: 1.4em; font-weight: 600; margin: 0; }
        .modal-header .meta { font-size: 0.9em; opacity: 0.9; margin-top: 6px; }
        .modal-close { position: absolute; top: 20px; right: 25px; font-size: 32px; font-weight: 300; color: white; cursor: pointer; opacity: 0.8; line-height: 1; }
        .modal-close:hover { opacity: 1; }
        .modal-body { padding: 30px; max-height: calc(90vh - 100px); overflow-y: auto; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; padding: 20px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0; }
        .info-item { }
        .info-label { font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; font-weight: 600; margin-bottom: 6px; }
        .info-value { font-size: 1.1em; color: #0f172a; font-weight: 600; }
        .section { margin-bottom: 30px; }
        .section-title { font-size: 1.1em; font-weight: 600; color: #0f172a; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; display: flex; align-items: center; gap: 8px; }
        .code-compare { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 15px; }
        .code-block { background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 6px; padding: 0; overflow: hidden; }
        .code-block-header { background: #0f172a; color: white; padding: 10px 15px; font-weight: 600; font-size: 0.85em; display: flex; align-items: center; gap: 8px; }
        .code-block-body { padding: 15px; overflow-x: auto; max-height: 400px; overflow-y: auto; }
        .code-block pre { font-family: 'SF Mono', 'Monaco', 'Courier New', monospace; font-size: 0.8em; color: #1e293b; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; }
        .view-btn { color: #1e40af; text-decoration: none; cursor: pointer; font-size: 0.85em; font-weight: 500; }
        .view-btn:hover { color: #1e3a8a; text-decoration: underline; }
        .metric-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 4px; font-size: 0.9em; font-weight: 500; }
        .score-excellent { background: #dcfce7; color: #166534; }
        .score-good { background: #dbeafe; color: #1e40af; }
        .score-fair { background: #fef3c7; color: #92400e; }
        .score-poor { background: #fee2e2; color: #991b1b; }
        .task-description { background: #f8fafc; padding: 20px; border-radius: 6px; border-left: 4px solid #1e40af; margin-bottom: 25px; }
        .task-description p { color: #475569; line-height: 1.6; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔒 AI Security Vulnerability Evaluation</h1>
            <div class="subtitle">Benchmarking GPT-4o, Claude Sonnet 4, and Gemini 2.0 Flash on Python Security Fixes</div>
        </header>

        <div class="controls">
            <label>Sample Count:</label>
            <input type="number" id="sampleCount" value="5" min="1" max="100">
            <button class="btn-primary" onclick="startEvaluation()">▶ Start Real Evaluation</button>
            <button class="btn-warning" onclick="startDemo()">🎬 Start Demo</button>
            <button class="btn-danger" onclick="stopEvaluation()">⬛ Stop</button>
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
                <div id="currentTask" style="margin-top: 10px; font-size: 1.1em; color: #6b7280;">Waiting to start...</div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 20px;">
            <h3>📋 Evaluation Logs</h3>
            <div id="logs" class="log-container"></div>
        </div>

        <div class="card">
            <h3>📊 Results</h3>
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
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody id="resultsBody">
                    <tr><td colspan="10" style="text-align: center; color: #9ca3af;">No results yet</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <div id="codeModal" class="modal">
        <div class="modal-content">
            <span class="modal-close" onclick="closeModal()">&times;</span>
            <div class="modal-header" id="modalHeader">
                <h2 id="modalTitle">Evaluation Details</h2>
                <div class="meta" id="modalMeta"></div>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let samples = [];
        let results = [];

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                addLog('✓ Connected to server');
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
                addLog('✓ Evaluation complete!');
                document.getElementById('statusText').textContent = 'Complete';
            } else if (message.type === 'error') {
                addLog('✗ ERROR: ' + message.data);
            } else if (message.type === 'samples') {
                samples = message.data;
                console.log('Loaded samples:', samples.length);
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
                document.getElementById('statusText').textContent = '⚡ Running...';
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
            // Store result for later access
            results.push(result);

            const tbody = document.getElementById('resultsBody');
            if (tbody.children[0]?.colSpan === 10) {
                tbody.innerHTML = '';
            }

            const row = document.createElement('tr');
            const vulnShort = result.vulnerability.length > 50 ?
                result.vulnerability.substring(0, 47) + '...' : result.vulnerability;

            row.innerHTML = `
                <td>${result.example_id}</td>
                <td><strong>${result.agent_name}</strong></td>
                <td><span class="vuln-code">${vulnShort}</span></td>
                <td><strong>${result.similarity_score.toFixed(1)}</strong>/10</td>
                <td><span class="badge ${result.vulnerability_fixed ? 'badge-success' : 'badge-danger'}">
                    ${result.vulnerability_fixed ? '✓ Yes' : '✗ No'}</span></td>
                <td><span class="badge ${result.static_analysis_pass ? 'badge-success' : 'badge-warning'}">
                    ${result.static_analysis_pass ? '✓ Pass' : '- N/A'}</span></td>
                <td><span class="badge ${result.code_executes ? 'badge-success' : 'badge-danger'}">
                    ${result.code_executes ? '✓ Yes' : '✗ No'}</span></td>
                <td>${result.time_taken.toFixed(2)}</td>
                <td>$${result.cost.toFixed(4)}</td>
                <td><span class="view-btn" onclick="viewCode(${result.example_id}, '${result.agent_name}')">View Details</span></td>
            `;
            tbody.appendChild(row);
        }

        function viewCode(exampleId, agentName) {
            const sample = samples.find(s => s.id === exampleId);
            const result = results.find(r => r.example_id === exampleId && r.agent_name === agentName);

            if (!sample) {
                alert('Sample data not available');
                return;
            }

            // Update modal header
            document.getElementById('modalTitle').textContent = sample.vulnerability;
            document.getElementById('modalMeta').textContent =
                `Example #${exampleId} • Agent: ${agentName} • Language: ${sample.language || 'Python'}`;

            // Calculate score class
            let scoreClass = 'score-poor';
            if (result && result.similarity_score >= 9) scoreClass = 'score-excellent';
            else if (result && result.similarity_score >= 7) scoreClass = 'score-good';
            else if (result && result.similarity_score >= 5) scoreClass = 'score-fair';

            // Build comprehensive modal body
            let modalContent = '';

            // Evaluation Metrics (if result available)
            if (result) {
                modalContent += `
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Similarity Score</div>
                            <div class="info-value">
                                <span class="metric-badge ${scoreClass}">
                                    ${result.similarity_score.toFixed(1)}/10
                                </span>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Vulnerability Fixed</div>
                            <div class="info-value">
                                <span class="badge ${result.vulnerability_fixed ? 'badge-success' : 'badge-danger'}">
                                    ${result.vulnerability_fixed ? '✓ Yes' : '✗ No'}
                                </span>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Static Analysis</div>
                            <div class="info-value">
                                <span class="badge ${result.static_analysis_pass ? 'badge-success' : 'badge-warning'}">
                                    ${result.static_analysis_pass ? '✓ Pass' : '- N/A'}
                                </span>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Code Executes</div>
                            <div class="info-value">
                                <span class="badge ${result.code_executes ? 'badge-success' : 'badge-danger'}">
                                    ${result.code_executes ? '✓ Yes' : '✗ No'}
                                </span>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Processing Time</div>
                            <div class="info-value">${result.time_taken.toFixed(2)}s</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">API Cost</div>
                            <div class="info-value">$${result.cost.toFixed(4)}</div>
                        </div>
                    </div>
                `;
            }

            // Task Description
            modalContent += `
                <div class="section">
                    <div class="section-title">📋 Task Description</div>
                    <div class="task-description">
                        <p>${escapeHtml(sample.task_description)}</p>
                    </div>
                </div>
            `;

            // Code Comparison
            modalContent += `
                <div class="section">
                    <div class="section-title">💻 Code Analysis</div>
                    <div class="code-compare">
                        <div class="code-block">
                            <div class="code-block-header">
                                <span>⚠️</span>
                                <span>Vulnerable Code</span>
                            </div>
                            <div class="code-block-body">
                                <pre>${escapeHtml(sample.vulnerable_code)}</pre>
                            </div>
                        </div>
            `;

            // Add Agent Fix if available
            if (result && result.agent_fixed_code) {
                modalContent += `
                        <div class="code-block">
                            <div class="code-block-header">
                                <span>🤖</span>
                                <span>${agentName} Fix</span>
                            </div>
                            <div class="code-block-body">
                                <pre>${escapeHtml(result.agent_fixed_code)}</pre>
                            </div>
                        </div>
                `;
            }

            // Reference Fix
            modalContent += `
                        <div class="code-block">
                            <div class="code-block-header">
                                <span>✅</span>
                                <span>Reference Fix</span>
                            </div>
                            <div class="code-block-body">
                                <pre>${escapeHtml(sample.fixed_code)}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Additional Information
            modalContent += `
                <div class="section">
                    <div class="section-title">ℹ️ Additional Information</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Example ID</div>
                            <div class="info-value">#${exampleId}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Language</div>
                            <div class="info-value">${sample.language || 'Python'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Agent</div>
                            <div class="info-value">${agentName}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Vulnerability Type</div>
                            <div class="info-value" style="font-size: 0.9em;">${sample.vulnerability}</div>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('modalBody').innerHTML = modalContent;
            document.getElementById('codeModal').style.display = 'block';
        }

        function closeModal() {
            document.getElementById('codeModal').style.display = 'none';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function startEvaluation() {
            const sampleCount = parseInt(document.getElementById('sampleCount').value);
            const response = await fetch(`/api/start?sample_count=${sampleCount}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.error) {
                addLog('✗ ERROR: ' + data.error);
            } else {
                addLog('▶ Starting real evaluation...');
                document.getElementById('resultsBody').innerHTML =
                    '<tr><td colspan="10" style="text-align: center; color: #9ca3af;">Loading...</td></tr>';
            }
        }

        async function stopEvaluation() {
            await fetch('/api/stop', { method: 'POST' });
            addLog('⬛ Stopping evaluation...');
        }

        async function startDemo() {
            const sampleCount = parseInt(document.getElementById('sampleCount').value);
            const response = await fetch(`/api/start_demo?sample_count=${sampleCount}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.error) {
                addLog('✗ ERROR: ' + data.error);
            } else {
                addLog('🎬 Starting DEMO evaluation...');
                document.getElementById('resultsBody').innerHTML =
                    '<tr><td colspan="10" style="text-align: center; color: #9ca3af;">Loading demo...</td></tr>';
            }
        }

        window.onclick = function(event) {
            const modal = document.getElementById('codeModal');
            if (event.target == modal) {
                closeModal();
            }
        }

        connectWebSocket();
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    print("Starting AI Agent Vulnerability Evaluation Web App...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)
