"""Gemini agent implementation."""

import time
import google.generativeai as genai
from src.agents.base_agent import BaseAgent, AgentResponse
from src.config import COST_PER_1M_TOKENS
from src.utils.logger import setup_logger

logger = setup_logger("gemini_agent")

class GeminiAgent(BaseAgent):
    """Gemini model agent for vulnerability fixing."""

    def __init__(self, model_name: str, api_key: str):
        """Initialize Gemini agent."""
        super().__init__(model_name, api_key)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Initialized Gemini agent with model: {model_name}")

    def fix_vulnerability(
        self,
        vulnerable_code: str,
        task_description: str,
        language: str,
        vulnerability: str
    ) -> AgentResponse:
        """Fix vulnerability using Gemini."""
        prompt = self.create_prompt(
            vulnerable_code, task_description, language, vulnerability
        )

        full_prompt = f"""You are a security expert specializing in fixing code vulnerabilities.

{prompt}"""

        start_time = time.time()

        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                )
            )

            time_taken = time.time() - start_time

            # Extract response
            fixed_code = response.text

            # Token usage (Gemini provides this in usage_metadata)
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count

            # Calculate cost
            cost = self.calculate_cost(input_tokens, output_tokens)

            logger.debug(
                f"Gemini response: {time_taken:.2f}s, "
                f"{input_tokens} in, {output_tokens} out, ${cost:.4f}"
            )

            return AgentResponse(
                fixed_code=fixed_code,
                raw_response=fixed_code,
                time_taken=time_taken,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                model_name=self.model_name,
                reasoning_effort=""
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Gemini model."""
        # Default to gemini-2.0-flash-exp pricing
        pricing = COST_PER_1M_TOKENS.get(
            "gemini-2.0-flash-exp",
            {"input": 0.075, "output": 0.30}
        )

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
