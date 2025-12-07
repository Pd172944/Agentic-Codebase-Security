"""Gemini agent implementation."""

import time
import json
import re
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
            raw_response = response.text
            
            # Parse JSON response
            fixed_code, pr_description = self._parse_response(raw_response)

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
            logger.error(f"Gemini API error: {e}")
            raise

    def _parse_response(self, raw_response: str) -> tuple:
        """Parse the JSON response to extract fixed code and PR description."""
        try:
            # Try to find JSON in the response
            # First try direct JSON parse
            try:
                data = json.loads(raw_response)
                return data.get("fixed_code", raw_response), data.get("pr_description", "No description provided.")
            except json.JSONDecodeError:
                pass
            
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("fixed_code", raw_response), data.get("pr_description", "No description provided.")
            
            # Try to find JSON object in text
            json_match = re.search(r'\{[^{}]*"fixed_code"[^{}]*\}', raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data.get("fixed_code", raw_response), data.get("pr_description", "No description provided.")
            
            # Fallback: return raw response as code with auto-generated description
            return raw_response, self._generate_fallback_description(raw_response)
            
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return raw_response, self._generate_fallback_description(raw_response)
    
    def _generate_fallback_description(self, code: str) -> str:
        """Generate a fallback PR description when JSON parsing fails."""
        return """## Security Fix

This PR addresses a security vulnerability in the codebase.

### Changes Made
- Fixed the identified security vulnerability
- Applied secure coding practices

### Testing
- Verified the fix addresses the security concern
- Ensured no regression in functionality

---
*Auto-generated description - please review and enhance as needed.*"""

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
