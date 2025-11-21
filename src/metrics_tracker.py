"""Metrics tracking and aggregation."""

from typing import Dict, List
from dataclasses import dataclass, asdict
import json
import csv
import os
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger("metrics_tracker")

@dataclass
class EvaluationMetrics:
    """Complete metrics for a single evaluation."""
    # Identification
    example_id: int
    agent_name: str
    language: str
    vulnerability: str

    # LLM evaluation scores
    similarity_score: float
    vulnerability_fixed: bool
    vulnerability_confidence: float
    llm_explanation: str

    # Static analysis
    static_analysis_available: bool
    vulnerabilities_reduced: bool
    vuln_reduction_count: int

    # Code execution
    code_executes: bool
    execution_error: str

    # Performance metrics
    time_taken: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    reasoning_effort: str

class MetricsTracker:
    """Track and aggregate evaluation metrics."""

    def __init__(self, results_dir: str = "results"):
        """
        Initialize metrics tracker.

        Args:
            results_dir: Directory to save results
        """
        self.results_dir = results_dir
        self.metrics: List[EvaluationMetrics] = []
        os.makedirs(results_dir, exist_ok=True)
        logger.info(f"Initialized metrics tracker, saving to {results_dir}")

    def add_metric(self, metric: EvaluationMetrics):
        """Add a single evaluation metric."""
        self.metrics.append(metric)
        logger.debug(f"Added metric for {metric.agent_name} on example {metric.example_id}")

    def save_detailed_results(self, filename: str = None):
        """
        Save detailed results to CSV.

        Args:
            filename: Optional custom filename
        """
        if not self.metrics:
            logger.warning("No metrics to save")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detailed_results_{timestamp}.csv"

        filepath = os.path.join(self.results_dir, filename)

        # Convert dataclasses to dicts
        rows = [asdict(m) for m in self.metrics]

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Saved detailed results to {filepath}")
        return filepath

    def save_summary_stats(self, filename: str = None):
        """
        Save summary statistics by agent.

        Args:
            filename: Optional custom filename
        """
        if not self.metrics:
            logger.warning("No metrics to summarize")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_stats_{timestamp}.json"

        filepath = os.path.join(self.results_dir, filename)

        # Calculate summary stats per agent
        summary = {}
        agents = set(m.agent_name for m in self.metrics)

        for agent in agents:
            agent_metrics = [m for m in self.metrics if m.agent_name == agent]

            summary[agent] = {
                "total_examples": len(agent_metrics),
                "avg_similarity_score": self._avg([m.similarity_score for m in agent_metrics]),
                "vulnerabilities_fixed_pct": self._pct([m.vulnerability_fixed for m in agent_metrics]),
                "avg_vulnerability_confidence": self._avg([m.vulnerability_confidence for m in agent_metrics]),
                "static_analysis_pass_rate": self._pct([m.vulnerabilities_reduced for m in agent_metrics if m.static_analysis_available]),
                "code_execution_pass_rate": self._pct([m.code_executes for m in agent_metrics]),
                "avg_time_seconds": self._avg([m.time_taken for m in agent_metrics]),
                "avg_input_tokens": self._avg([m.input_tokens for m in agent_metrics]),
                "avg_output_tokens": self._avg([m.output_tokens for m in agent_metrics]),
                "total_cost": sum(m.cost for m in agent_metrics),
                "avg_cost_per_example": self._avg([m.cost for m in agent_metrics]),
            }

        # Save JSON
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Saved summary statistics to {filepath}")
        return filepath

    def _avg(self, values: List[float]) -> float:
        """Calculate average, handling empty lists."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _pct(self, bool_values: List[bool]) -> float:
        """Calculate percentage of True values."""
        if not bool_values:
            return 0.0
        return (sum(bool_values) / len(bool_values)) * 100

    def print_summary(self):
        """Print summary statistics to console."""
        if not self.metrics:
            logger.warning("No metrics to summarize")
            return

        agents = set(m.agent_name for m in self.metrics)

        print("\n" + "=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)

        for agent in sorted(agents):
            agent_metrics = [m for m in self.metrics if m.agent_name == agent]

            print(f"\n{agent}:")
            print(f"  Examples evaluated: {len(agent_metrics)}")
            print(f"  Avg similarity score: {self._avg([m.similarity_score for m in agent_metrics]):.2f}/10")
            print(f"  Vulnerabilities fixed: {self._pct([m.vulnerability_fixed for m in agent_metrics]):.1f}%")
            print(f"  Code execution pass: {self._pct([m.code_executes for m in agent_metrics]):.1f}%")
            print(f"  Avg time: {self._avg([m.time_taken for m in agent_metrics]):.2f}s")
            print(f"  Total cost: ${sum(m.cost for m in agent_metrics):.4f}")

        print("=" * 80 + "\n")
