"""Code execution checker with sandboxing."""

import os
import tempfile
import subprocess
from typing import Dict, Optional
from dataclasses import dataclass
from src.utils.logger import setup_logger

logger = setup_logger("code_executor")

@dataclass
class ExecutionResult:
    """Result of code execution test."""
    success: bool
    error_message: str
    stdout: str
    stderr: str
    exit_code: int

class CodeExecutor:
    """Execute code in sandboxed environment."""

    def __init__(self, timeout: int = 10):
        """
        Initialize code executor.

        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
        logger.info(f"Initialized code executor with {timeout}s timeout")

    def execute(self, code: str, language: str) -> ExecutionResult:
        """
        Execute code and check if it runs without errors.

        Args:
            code: Source code to execute
            language: Programming language

        Returns:
            ExecutionResult with execution status
        """
        language_lower = language.lower()

        if language_lower == "python":
            return self._execute_python(code)
        elif language_lower in ["javascript", "js"]:
            return self._execute_javascript(code)
        elif language_lower in ["c++", "cpp"]:
            return self._execute_cpp(code)
        elif language_lower == "java":
            return self._execute_java(code)
        else:
            logger.warning(f"Execution not supported for {language}")
            return ExecutionResult(
                success=False,
                error_message=f"Execution not supported for {language}",
                stdout="",
                stderr="",
                exit_code=-1
            )

    def _execute_python(self, code: str) -> ExecutionResult:
        """Execute Python code."""
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False
            ) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Run Python with restricted environment
                result = subprocess.run(
                    ['python', '-c', f"import sys; sys.exit(compile(open('{temp_file}').read(), '{temp_file}', 'exec'))"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                success = result.returncode == 0
                error_msg = "" if success else "Syntax or compilation error"

                return ExecutionResult(
                    success=success,
                    error_message=error_msg,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode
                )

            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error_message="Execution timeout",
                stdout="",
                stderr="Timeout",
                exit_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}",
                stdout="",
                stderr=str(e),
                exit_code=-1
            )

    def _execute_javascript(self, code: str) -> ExecutionResult:
        """Execute JavaScript code using Node.js."""
        try:
            result = subprocess.run(
                ['node', '--check', '-'],
                input=code,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            success = result.returncode == 0
            error_msg = "" if success else "Syntax error"

            return ExecutionResult(
                success=success,
                error_message=error_msg,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )

        except FileNotFoundError:
            logger.warning("Node.js not found, skipping execution")
            return ExecutionResult(
                success=False,
                error_message="Node.js not installed",
                stdout="",
                stderr="",
                exit_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}",
                stdout="",
                stderr=str(e),
                exit_code=-1
            )

    def _execute_cpp(self, code: str) -> ExecutionResult:
        """Check C++ code compilation."""
        logger.warning("C++ execution requires compiler, returning placeholder")
        return ExecutionResult(
            success=False,
            error_message="C++ compilation not available",
            stdout="",
            stderr="",
            exit_code=-1
        )

    def _execute_java(self, code: str) -> ExecutionResult:
        """Check Java code compilation."""
        logger.warning("Java execution requires JDK, returning placeholder")
        return ExecutionResult(
            success=False,
            error_message="Java compilation not available",
            stdout="",
            stderr="",
            exit_code=-1
        )
