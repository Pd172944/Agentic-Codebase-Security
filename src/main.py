"""Main orchestrator for AI agent vulnerability fixing evaluation."""

import sys
from tqdm import tqdm

# Import configuration
from src.config import (
    validate_config,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
    GPT_MODEL,
    CLAUDE_MODEL,
    GEMINI_MODEL,
    DATASET_NAME,
    SAMPLE_SIZE,
    RANDOM_SEED,
    RESULTS_DIR,
    TIMEOUT_SECONDS,
)

# Import components
from src.dataset_loader import DatasetLoader
from src.agents import GPTAgent, ClaudeAgent, GeminiAgent
from src.evaluators.llm_evaluator import LLMEvaluator
from src.evaluators.static_analyzer import StaticAnalyzer
from src.evaluators.code_executor import CodeExecutor
from src.metrics_tracker import MetricsTracker, EvaluationMetrics
from src.utils.logger import setup_logger

logger = setup_logger("main")

class EvaluationOrchestrator:
    """Orchestrates the complete evaluation pipeline."""

    def __init__(self):
        """Initialize orchestrator with all components."""
        logger.info("Initializing evaluation orchestrator...")

        # Validate configuration
        try:
            validate_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

        # Initialize dataset loader
        self.dataset_loader = DatasetLoader(
            DATASET_NAME, SAMPLE_SIZE, RANDOM_SEED
        )

        # Initialize agents
        self.agents = {
            "GPT-4o": GPTAgent(GPT_MODEL, OPENAI_API_KEY),
            "Claude-Sonnet-4": ClaudeAgent(CLAUDE_MODEL, ANTHROPIC_API_KEY),
            "Gemini-2.0-Flash": GeminiAgent(GEMINI_MODEL, GOOGLE_API_KEY),
        }

        # Initialize evaluators
        self.llm_evaluator = LLMEvaluator(OPENAI_API_KEY)
        self.static_analyzer = StaticAnalyzer()
        self.code_executor = CodeExecutor(timeout=TIMEOUT_SECONDS)

        # Initialize metrics tracker
        self.metrics_tracker = MetricsTracker(RESULTS_DIR)

        logger.info("Orchestrator initialized successfully")

    def run(self):
        """Run the complete evaluation pipeline."""
        logger.info("Starting evaluation pipeline...")

        # Load dataset
        logger.info("Loading dataset...")
        samples = self.dataset_loader.load()

        total_evaluations = len(samples) * len(self.agents)
        logger.info(f"Will perform {total_evaluations} evaluations")

        # Progress bar
        pbar = tqdm(total=total_evaluations, desc="Evaluating")

        # Evaluate each sample with each agent
        for sample in samples:
            for agent_name, agent in self.agents.items():
                try:
                    metric = self._evaluate_single(sample, agent_name, agent)
                    self.metrics_tracker.add_metric(metric)
                except Exception as e:
                    logger.error(
                        f"Error evaluating {agent_name} on example {sample['id']}: {e}"
                    )

                pbar.update(1)

        pbar.close()

        # Save results
        logger.info("Saving results...")
        csv_file = self.metrics_tracker.save_detailed_results()
        json_file = self.metrics_tracker.save_summary_stats()

        # Print summary
        self.metrics_tracker.print_summary()

        logger.info("Evaluation complete!")
        logger.info(f"Detailed results: {csv_file}")
        logger.info(f"Summary stats: {json_file}")

    def _evaluate_single(self, sample: dict, agent_name: str, agent) -> EvaluationMetrics:
        """
        Evaluate a single example with a single agent.

        Args:
            sample: Dataset sample
            agent_name: Name of the agent
            agent: Agent instance

        Returns:
            EvaluationMetrics for this evaluation
        """
        example_id = sample["id"]
        language = sample["language"]
        vulnerability = sample["vulnerability"]
        task_description = sample["task_description"]
        vulnerable_code = sample["vulnerable_code"]
        fixed_code = sample["fixed_code"]

        logger.debug(f"Evaluating {agent_name} on example {example_id}")

        # Step 1: Agent attempts to fix the vulnerability
        agent_response = agent.fix_vulnerability(
            vulnerable_code, task_description, language, vulnerability
        )

        # Step 2: LLM evaluation
        llm_eval = self.llm_evaluator.evaluate(
            fixed_code, agent_response.fixed_code, vulnerability, language
        )

        # Step 3: Static analysis (if available)
        static_before = self.static_analyzer.analyze(vulnerable_code, language)
        static_after = self.static_analyzer.analyze(agent_response.fixed_code, language)
        static_comparison = self.static_analyzer.compare_vulnerabilities(
            static_before, static_after
        )

        # Step 4: Code execution test
        execution_result = self.code_executor.execute(
            agent_response.fixed_code, language
        )

        # Compile metrics
        return EvaluationMetrics(
            example_id=example_id,
            agent_name=agent_name,
            language=language,
            vulnerability=vulnerability,
            similarity_score=llm_eval.similarity_score,
            vulnerability_fixed=llm_eval.vulnerability_fixed,
            vulnerability_confidence=llm_eval.vulnerability_confidence,
            llm_explanation=llm_eval.explanation,
            static_analysis_available=static_comparison["analysis_available"],
            vulnerabilities_reduced=static_comparison["vulnerabilities_reduced"],
            vuln_reduction_count=static_comparison["reduction_count"],
            code_executes=execution_result.success,
            execution_error=execution_result.error_message,
            time_taken=agent_response.time_taken,
            input_tokens=agent_response.input_tokens,
            output_tokens=agent_response.output_tokens,
            total_tokens=agent_response.input_tokens + agent_response.output_tokens,
            cost=agent_response.cost,
            reasoning_effort=agent_response.reasoning_effort,
        )

def main():
    """Main entry point."""
    print("=" * 80)
    print("AI Agent Vulnerability Fixing Evaluation")
    print("=" * 80)
    print()

    orchestrator = EvaluationOrchestrator()
    orchestrator.run()

if __name__ == "__main__":
    main()
