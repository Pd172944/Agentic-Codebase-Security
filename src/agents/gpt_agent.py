"""GPT agent implementation."""

import time
from openai import OpenAI
from src.agents.base_agent import BaseAgent, AgentResponse
from src.config import COST_PER_1M_TOKENS
from src.utils.logger import setup_logger

logger = setup_logger("gpt_agent")

class GPTAgent(BaseAgent):
    """GPT model agent for vulnerability fixing."""

    def __init__(self, model_name: str, api_key: str):
        """Initialize GPT agent."""
        super().__init__(model_name, api_key)
        self.client = OpenAI(api_key=api_key)
        logger.info(f"Initialized GPT agent with model: {model_name}")

    def fix_vulnerability(
        self,
        vulnerable_code: str,
        task_description: str,
        language: str,
        vulnerability: str
    ) -> AgentResponse:
        """Fix vulnerability using GPT."""
        prompt = self.create_prompt(
            vulnerable_code, task_description, language, vulnerability
        )

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a Senior Application Security Engineer.
Your goal is to fix vulnerabilities with production-grade security patches.

**Process**:
1.  **Analyze**: Identify the specific attack vector (e.g., SQLi, XSS, Path Traversal).
2.  **Plan**: Decide on the secure pattern (e.g., Parameterization, Input Validation).
3.  **Think in Comments**: Write 1-2 lines of comments at the very top of your code explaining *why* this fix is secure.
4.  **Execute**: Write the Python code.

**Constraints**:
* Do NOT change the function signature.
* Use standard Python libraries (os, sys, shlex, html) whenever possible.
* Return ONLY valid Python code. No Markdown blocks (```python), no conversational text outside the code."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent fixes
            )

            time_taken = time.time() - start_time

            # Extract response
            fixed_code = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            # Calculate cost
            cost = self.calculate_cost(input_tokens, output_tokens)

            # Extract reasoning effort if available
            reasoning_effort = ""
            if hasattr(response.choices[0].message, 'reasoning_content'):
                reasoning_effort = response.choices[0].message.reasoning_content or ""

            logger.debug(
                f"GPT response: {time_taken:.2f}s, "
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
                reasoning_effort=reasoning_effort
            )

        except Exception as e:
            logger.error(f"GPT API error: {e}")
            raise

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for GPT model."""
        # Default to gpt-4o pricing if model not in config
        model_key = "gpt-4o"
        if self.model_name in COST_PER_1M_TOKENS:
            model_key = self.model_name

        pricing = COST_PER_1M_TOKENS.get(model_key, {"input": 2.5, "output": 10.0})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
