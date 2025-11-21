"""
Simplified Launcher for Green Agent Assessment

This script runs the green agent assessment using existing agents directly.
Only implements the GREEN AGENT portion from the AgentBeats blog.

Based on AgentBeats blog: "Agentify the Agent Assessment"
https://agentbeats.ai/blog/agentify-agent-assessment
"""

import asyncio
import argparse
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from green_agent.agent import GreenAgent
from dataset_loader import DatasetLoader


def load_test_data(num_samples: int = 5) -> list:
    """
    Load test data from dataset.
    
    Args:
        num_samples: Number of samples to load
        
    Returns:
        List of task dictionaries
    """
    print(f"[Launcher] Loading {num_samples} test samples...")
    
    loader = DatasetLoader()
    dataset = loader.load_dataset(
        sample_size=num_samples,
        language_filter="python"
    )
    
    tasks = []
    for item in dataset:
        tasks.append({
            "vulnerable_code": item['rejected'],
            "reference_fix": item['chosen'],
            "task_description": item['prompt'],
            "vulnerability": item.get('vulnerability_type', 'Security vulnerability'),
            "language": "python"
        })
    
    print(f"[Launcher] Loaded {len(tasks)} tasks")
    return tasks


async def run_assessment(agent_type: str, num_samples: int):
    """
    Run green agent assessment on existing agents.
    
    Args:
        agent_type: Type of agent to test ('gpt', 'claude', or 'gemini')
        num_samples: Number of samples to test
    """
    print("\n" + "=" * 60)
    print("🟢 GREEN AGENT ASSESSMENT")
    print("=" * 60)
    print(f"Agent to test: {agent_type}")
    print(f"Test samples: {num_samples}")
    print("=" * 60 + "\n")
    
    # Initialize green agent
    green_agent = GreenAgent("VulnerabilityAssessmentGreenAgent")
    
    # Load test data
    tasks = load_test_data(num_samples)
    
    # Import the appropriate agent
    from agents.gpt_agent import GPTAgent
    from agents.claude_agent import ClaudeAgent
    from agents.gemini_agent import GeminiAgent
    from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
    
    if agent_type == "gpt":
        test_agent = GPTAgent("gpt-4o", OPENAI_API_KEY)
    elif agent_type == "claude":
        test_agent = ClaudeAgent("claude-sonnet-4-20250514", ANTHROPIC_API_KEY)
    elif agent_type == "gemini":
        test_agent = GeminiAgent("gemini-2.0-flash-exp", GOOGLE_API_KEY)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    print(f"[Green Agent] Testing agent: {test_agent.model_name}")
    
    # Run assessment on each task
    results = []
    for i, task in enumerate(tasks):
        print(f"\n[Green Agent] Evaluating task {i+1}/{len(tasks)}...")
        
        # Get agent's fix
        print(f"[Green Agent] Requesting fix from {agent_type} agent...")
        agent_response = test_agent.fix_vulnerability(
            vulnerable_code=task['vulnerable_code'],
            task_description=task['task_description'],
            language=task['language'],
            vulnerability=task['vulnerability']
        )
        
        # Evaluate the response
        result = await green_agent._evaluate_response(
            fixed_code=agent_response.fixed_code,
            reference_fix=task['reference_fix'],
            vulnerable_code=task['vulnerable_code'],
            task_description=task['task_description'],
            language=task['language']
        )
        
        # Add metadata
        result['time_taken'] = agent_response.time_taken
        result['model'] = agent_response.model_name
        
        results.append(result)
        
        print(f"  ✓ Similarity: {result['similarity_score']:.2f}/10")
        print(f"  ✓ Vulnerability fixed: {result['vulnerability_fixed']}")
        print(f"  ✓ Code executes: {result['code_executes']}")
        print(f"  ✓ Time: {result['time_taken']:.2f}s")
    
    # Calculate aggregated metrics
    total_tasks = len(results)
    successful_fixes = sum(1 for r in results if r['vulnerability_fixed'])
    avg_similarity = sum(r['similarity_score'] for r in results) / total_tasks
    avg_time = sum(r['time_taken'] for r in results) / total_tasks
    execution_rate = sum(1 for r in results if r['code_executes']) / total_tasks
    
    metrics = {
        'agent': agent_type,
        'model': test_agent.model_name,
        'total_tasks': total_tasks,
        'successful_fixes': successful_fixes,
        'success_rate': successful_fixes / total_tasks,
        'avg_similarity_score': avg_similarity,
        'execution_rate': execution_rate,
        'avg_time_per_task': avg_time,
        'individual_results': results
    }
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 ASSESSMENT RESULTS")
    print("=" * 60)
    print(green_agent.format_results_message(metrics))
    print("=" * 60 + "\n")
    
    # Save results
    os.makedirs("results", exist_ok=True)
    results_file = f"results/green_agent_assessment_{agent_type}_{int(asyncio.get_event_loop().time())}.json"
    
    with open(results_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"[Launcher] Results saved to {results_file}")
    
    return metrics


def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(
        description="Run Green Agent assessment on existing agents"
    )
    parser.add_argument(
        "--agent",
        choices=["gpt", "claude", "gemini"],
        default="gpt",
        help="Type of agent to test"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of test samples"
    )
    
    args = parser.parse_args()
    
    try:
        # Run assessment
        asyncio.run(run_assessment(args.agent, args.samples))
        print("\n[Launcher] ✅ Assessment complete!\n")
        
    except KeyboardInterrupt:
        print("\n[Launcher] Interrupted by user")
    
    except Exception as e:
        print(f"\n[Launcher] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
