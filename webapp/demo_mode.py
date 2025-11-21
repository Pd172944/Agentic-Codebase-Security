"""Demo mode with mock data for quick testing."""

import asyncio
import random
from datetime import datetime

# Sample demo data
DEMO_SAMPLES = [
    {
        "id": 1,
        "language": "Python",
        "vulnerability": "SQL injection vulnerability due to string concatenation",
        "task_description": "Create a function to query user data from database",
        "vulnerable_code": "query = \"SELECT * FROM users WHERE id = '\" + user_id + \"'\"",
        "fixed_code": "query = \"SELECT * FROM users WHERE id = ?\"\ndb.execute(query, (user_id,))"
    },
    {
        "id": 2,
        "language": "Python",
        "vulnerability": "Command injection via os.system with user input",
        "task_description": "Execute a system command with user-provided filename",
        "vulnerable_code": "os.system('cat ' + filename)",
        "fixed_code": "subprocess.run(['cat', filename], check=True, capture_output=True)"
    },
    {
        "id": 3,
        "language": "Python",
        "vulnerability": "Path traversal vulnerability in file access",
        "task_description": "Read a file from user-specified path",
        "vulnerable_code": "with open(user_path, 'r') as f:\n    return f.read()",
        "fixed_code": "safe_path = os.path.abspath(user_path)\nif not safe_path.startswith('/safe/dir/'):\n    raise ValueError('Invalid path')\nwith open(safe_path, 'r') as f:\n    return f.read()"
    },
    {
        "id": 4,
        "language": "Python",
        "vulnerability": "Use of pickle with untrusted data",
        "task_description": "Deserialize user-provided data",
        "vulnerable_code": "data = pickle.loads(user_input)",
        "fixed_code": "data = json.loads(user_input)"
    },
    {
        "id": 5,
        "language": "Python",
        "vulnerability": "Hardcoded credentials in source code",
        "task_description": "Connect to database with credentials",
        "vulnerable_code": "conn = psycopg2.connect(host='localhost', password='admin123')",
        "fixed_code": "import os\nconn = psycopg2.connect(host='localhost', password=os.getenv('DB_PASSWORD'))"
    }
]

DEMO_AGENTS = ["GPT-4o", "Claude-Sonnet-4", "Gemini-2.0-Flash"]

async def run_demo_evaluation(broadcast_callback, sample_count: int = 5):
    """
    Run a demo evaluation with mock data.

    Args:
        broadcast_callback: Async function to broadcast updates
        sample_count: Number of samples to run
    """
    samples = DEMO_SAMPLES[:min(sample_count, len(DEMO_SAMPLES))]
    total = len(samples) * len(DEMO_AGENTS)

    await broadcast_callback({
        "type": "log",
        "data": f"[DEMO MODE] Starting evaluation with {len(samples)} samples..."
    })

    await asyncio.sleep(0.5)

    progress = 0
    results = []

    for sample in samples:
        for agent_name in DEMO_AGENTS:
            await broadcast_callback({
                "type": "status",
                "data": {
                    "running": True,
                    "progress": progress,
                    "total": total,
                    "current_example": sample["id"],
                    "current_agent": agent_name
                }
            })

            await broadcast_callback({
                "type": "log",
                "data": f"[DEMO] Evaluating {agent_name} on example {sample['id']}..."
            })

            # Simulate processing time
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Generate mock result with realistic values
            similarity_score = random.uniform(6.5, 9.8)
            vulnerability_fixed = random.random() > 0.15  # 85% success rate
            static_pass = random.random() > 0.20  # 80% static analysis pass
            code_executes = random.random() > 0.10  # 90% execution success
            time_taken = random.uniform(2.0, 5.0)
            cost = random.uniform(0.001, 0.015)

            result = {
                "example_id": sample["id"],
                "agent_name": agent_name,
                "vulnerability": sample["vulnerability"],
                "similarity_score": similarity_score,
                "vulnerability_fixed": vulnerability_fixed,
                "static_analysis_pass": static_pass,
                "code_executes": code_executes,
                "time_taken": time_taken,
                "cost": cost,
            }

            results.append(result)

            await broadcast_callback({
                "type": "result",
                "data": result
            })

            progress += 1

    await broadcast_callback({
        "type": "complete",
        "data": {
            "running": False,
            "progress": total,
            "total": total,
            "results": results,
            "end_time": datetime.now().isoformat()
        }
    })

    await broadcast_callback({
        "type": "log",
        "data": f"[DEMO MODE] Evaluation complete! Processed {len(samples)} samples with {len(DEMO_AGENTS)} agents."
    })

    # Calculate summary stats
    avg_similarity = sum(r["similarity_score"] for r in results) / len(results)
    fix_rate = sum(1 for r in results if r["vulnerability_fixed"]) / len(results) * 100
    exec_rate = sum(1 for r in results if r["code_executes"]) / len(results) * 100
    total_cost = sum(r["cost"] for r in results)

    await broadcast_callback({
        "type": "log",
        "data": f"[DEMO SUMMARY] Avg Similarity: {avg_similarity:.2f}/10, Fix Rate: {fix_rate:.1f}%, Exec Rate: {exec_rate:.1f}%, Total Cost: ${total_cost:.4f}"
    })
