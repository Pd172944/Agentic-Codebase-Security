"""Claude agent implementation."""

import time
import json
import re
from anthropic import Anthropic
from src.agents.base_agent import BaseAgent, AgentResponse
from src.config import COST_PER_1M_TOKENS
from src.utils.logger import setup_logger

logger = setup_logger("claude_agent")

class ClaudeAgent(BaseAgent):
    """Claude model agent for vulnerability fixing."""

    def __init__(self, model_name: str, api_key: str):
        """Initialize Claude agent."""
        super().__init__(model_name, api_key)
        self.client = Anthropic(api_key=api_key)
        logger.info(f"Initialized Claude agent with model: {model_name}")

    def fix_vulnerability(
        self,
        vulnerable_code: str,
        task_description: str,
        language: str,
        vulnerability: str
    ) -> AgentResponse:
        """Fix vulnerability using Claude."""
        prompt = self.create_prompt(
            vulnerable_code, task_description, language, vulnerability
        )

        start_time = time.time()

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                temperature=0.3,
                system="You are a security expert specializing in fixing code vulnerabilities.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            time_taken = time.time() - start_time

            # Extract response
            raw_response = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Parse JSON response to extract code and PR description
            fixed_code, pr_description = self._parse_response(raw_response)

            # Calculate cost
            cost = self.calculate_cost(input_tokens, output_tokens)

            logger.debug(
                f"Claude response: {time_taken:.2f}s, "
                f"{input_tokens} in, {output_tokens} out, ${cost:.4f}"
            )

            return AgentResponse(
                fixed_code=fixed_code,
                raw_response=raw_response,
                time_taken=time_taken,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                model_name=self.model_name,
                reasoning_effort="",
                pr_description=pr_description
            )

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def _parse_response(self, raw_response: str) -> tuple:
        """Parse JSON response to extract fixed code and PR description."""
        try:
            # Try to parse as JSON directly
            data = json.loads(raw_response)
            fixed_code = data.get("fixed_code", raw_response)
            pr_description = data.get("pr_description", "")
            return fixed_code, pr_description
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                fixed_code = data.get("fixed_code", raw_response)
                pr_description = data.get("pr_description", "")
                return fixed_code, pr_description
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the response
        json_match = re.search(r'\{[^{}]*"fixed_code"[^{}]*\}', raw_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                fixed_code = data.get("fixed_code", raw_response)
                pr_description = data.get("pr_description", "")
                return fixed_code, pr_description
            except json.JSONDecodeError:
                pass

        # Fallback: extract code from python code block
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', raw_response, re.DOTALL)
        if code_match:
            return code_match.group(1), ""

        return raw_response, ""

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Claude model."""
        # Default to claude-sonnet-4 pricing
        pricing = COST_PER_1M_TOKENS.get(
            "claude-sonnet-4",
            {"input": 3.0, "output": 15.0}
        )

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
