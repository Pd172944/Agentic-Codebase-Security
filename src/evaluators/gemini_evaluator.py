"""Gemini-based evaluator for code similarity and vulnerability assessment."""

from typing import Dict
from dataclasses import dataclass
import google.generativeai as genai
from src.utils.logger import setup_logger

logger = setup_logger("gemini_evaluator")

@dataclass
class EvaluationResult:
    """Result of LLM-based evaluation."""
    similarity_score: float  # 0-10
    vulnerability_fixed: bool
    vulnerability_confidence: float  # 0-1
    explanation: str

class GeminiEvaluator:
    """Uses Gemini to evaluate code fixes."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini evaluator.

        Args:
            api_key: Google API key
            model: Model to use for evaluation
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        logger.info(f"Initialized Gemini evaluator with model: {model}")

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
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            # Parse JSON response
            import json
            result = json.loads(response.text)

            return EvaluationResult(
                similarity_score=float(result.get("similarity_score", 0)),
                vulnerability_fixed=bool(result.get("vulnerability_fixed", False)),
                vulnerability_confidence=float(result.get("confidence", 0)),
                explanation=result.get("explanation", "")
            )

        except Exception as e:
            logger.error(f"Gemini evaluation error: {e}")
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

Respond in JSON format:
{{
  "similarity_score": <float 0-10>,
  "vulnerability_fixed": <boolean>,
  "confidence": <float 0-1>,
  "explanation": "<brief explanation of your assessment>"
}}"""
