"""Static analysis evaluator using free security tools."""

import os
import tempfile
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.utils.logger import setup_logger

logger = setup_logger("static_analyzer")

@dataclass
class StaticAnalysisResult:
    """Result of static analysis."""
    vulnerabilities_found: int
    severity_high: int
    severity_medium: int
    severity_low: int
    tool_used: str
    issues: List[Dict]

class StaticAnalyzer:
    """Static analysis using free security tools."""

    def __init__(self):
        """Initialize static analyzer."""
        logger.info("Initialized static analyzer")

    def analyze(self, code: str, language: str) -> Optional[StaticAnalysisResult]:
        """
        Analyze code for vulnerabilities.

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            StaticAnalysisResult if analysis successful, None otherwise
        """
        language_lower = language.lower()

        if language_lower == "python":
            return self._analyze_python(code)
        elif language_lower in ["javascript", "js"]:
            return self._analyze_javascript(code)
        else:
            logger.warning(f"No static analysis tool available for {language}")
            return None

    def _analyze_python(self, code: str) -> Optional[StaticAnalysisResult]:
        """Analyze Python code using Bandit."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False
            ) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Run Bandit
                result = subprocess.run(
                    ['bandit', '-f', 'json', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Parse JSON output
                import json
                output = json.loads(result.stdout)

                # Extract metrics
                metrics = output.get('metrics', {})
                results = output.get('results', [])

                severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
                for issue in results:
                    severity = issue.get('issue_severity', 'LOW')
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                return StaticAnalysisResult(
                    vulnerabilities_found=len(results),
                    severity_high=severity_counts.get("HIGH", 0),
                    severity_medium=severity_counts.get("MEDIUM", 0),
                    severity_low=severity_counts.get("LOW", 0),
                    tool_used="Bandit",
                    issues=results
                )

            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        except subprocess.TimeoutExpired:
            logger.error("Bandit analysis timed out")
            return None
        except FileNotFoundError:
            logger.warning("Bandit not installed, skipping static analysis")
            return None
        except Exception as e:
            logger.error(f"Bandit analysis error: {e}")
            return None

    def _analyze_javascript(self, code: str) -> Optional[StaticAnalysisResult]:
        """
        Analyze JavaScript code.

        Note: Semgrep can be used but requires more complex setup.
        For now, returns None as a placeholder.
        """
        logger.warning("JavaScript static analysis not yet implemented")
        return None

    def compare_vulnerabilities(
        self,
        before: Optional[StaticAnalysisResult],
        after: Optional[StaticAnalysisResult]
    ) -> Dict:
        """
        Compare static analysis results before and after fix.

        Args:
            before: Analysis of vulnerable code
            after: Analysis of fixed code

        Returns:
            Comparison metrics
        """
        if before is None or after is None:
            return {
                "analysis_available": False,
                "vulnerabilities_reduced": False,
                "reduction_count": 0
            }

        reduction = before.vulnerabilities_found - after.vulnerabilities_found

        return {
            "analysis_available": True,
            "vulnerabilities_reduced": reduction > 0,
            "reduction_count": reduction,
            "before_count": before.vulnerabilities_found,
            "after_count": after.vulnerabilities_found,
            "before_high": before.severity_high,
            "after_high": after.severity_high,
        }
