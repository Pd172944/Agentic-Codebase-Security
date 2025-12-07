"""Anthropic Claude-based evaluator for code similarity and vulnerability assessment."""

import json
from anthropic import Anthropic
from src.evaluators.llm_evaluator import EvaluationResult
from src.utils.logger import setup_logger

logger = setup_logger("anthropic_evaluator")


class AnthropicEvaluator:
    """Uses Anthropic Claude to evaluate code fixes."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Anthropic evaluator.

        Args:
            api_key: Anthropic API key
            model: Model to use for evaluation
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"Initialized Anthropic evaluator with model: {model}")

    def evaluate(
        self,
        reference_fix: str,
        agent_fix: str,
        vulnerability_description: str,
        language: str
    ) -> EvaluationResult:
        """
        Evaluate agent's fix against reference.

        Args:
            reference_fix: The reference fixed code
            agent_fix: The agent's attempted fix
            vulnerability_description: Description of the vulnerability
            language: Programming language

        Returns:
            EvaluationResult with scores and analysis
        """
        prompt = self._create_evaluation_prompt(
            reference_fix, agent_fix, vulnerability_description, language
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system="You are a security expert evaluating code fixes. Always respond with valid JSON.",
            )

            # Parse JSON response
            response_text = response.content[0].text

            # Try to extract JSON from the response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    raise ValueError("Could not parse JSON from response")

            return EvaluationResult(
                similarity_score=float(result.get("similarity_score", 0)),
                vulnerability_fixed=bool(result.get("vulnerability_fixed", False)),
                vulnerability_confidence=float(result.get("confidence", 0)),
                explanation=result.get("explanation", "")
            )

        except Exception as e:
            logger.error(f"Anthropic evaluation error: {e}")
            # Return default values on error
            return EvaluationResult(
                similarity_score=0.0,
                vulnerability_fixed=False,
                vulnerability_confidence=0.0,
                explanation=f"Evaluation error: {str(e)}"
            )

    def _create_evaluation_prompt(
        self,
        reference_fix: str,
        agent_fix: str,
        vulnerability_description: str,
        language: str
    ) -> str:
        """Create evaluation prompt."""
        return f"""You are evaluating a security fix for {language} code.

**Original Vulnerability**: {vulnerability_description}

**Reference Fix** (correct solution):
```{language.lower()}
{reference_fix}
```

**Agent's Fix** (to be evaluated):
```{language.lower()}
{agent_fix}
```

Evaluate the agent's fix on two dimensions:

1. **Similarity Score (0-10)**: How similar is the agent's fix to the reference fix?
   - 10: Identical or functionally equivalent
   - 7-9: Very similar approach, minor differences
   - 4-6: Different approach but achieves same security goals
   - 1-3: Different approach with questionable effectiveness
   - 0: Completely different or wrong

2. **Vulnerability Fixed (boolean)**: Does the agent's fix actually address the security vulnerability?
   - true: The vulnerability is properly addressed
   - false: The vulnerability remains or new issues introduced

3. **Confidence (0-1)**: How confident are you in your vulnerability assessment?

Respond ONLY with valid JSON (no markdown, no extra text):
{{"similarity_score": <float 0-10>, "vulnerability_fixed": <boolean>, "confidence": <float 0-1>, "explanation": "<brief explanation>"}}"""
