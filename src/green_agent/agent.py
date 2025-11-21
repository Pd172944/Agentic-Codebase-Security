"""
Green Agent for Vulnerability Assessment

This agent manages the assessment process by:
1. Receiving assessment tasks via A2A protocol
2. Creating evaluation environment
3. Sending vulnerability fixing tasks to white agents
4. Evaluating responses using existing evaluators
5. Returning metrics

Based on AgentBeats blog: "Agentify the Agent Assessment"
https://agentbeats.ai/blog/agentify-agent-assessment
"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.evaluators.llm_evaluator import LLMEvaluator
from src.evaluators.static_analyzer import StaticAnalyzer
from src.evaluators.code_executor import CodeExecutor
from src.config import OPENAI_API_KEY


@dataclass
class AssessmentResult:
    """Results from evaluating a single task."""
    success: bool
    similarity_score: float
    vulnerability_fixed: bool
    code_executes: bool
    static_analysis_pass: bool
    time_used: float
    error_message: Optional[str] = None


class GreenAgent:
    """
    Green Agent that manages vulnerability assessment.
    
    This agent receives assessment tasks, coordinates with white agents,
    and returns evaluation metrics.
    """
    
    def __init__(self, agent_name: str = "VulnerabilityAssessmentAgent"):
        """
        Initialize green agent.
        
        Args:
            agent_name: Display name for the agent
        """
        self.agent_name = agent_name
        
        # Initialize evaluators (reusing existing framework components)
        self.llm_evaluator = LLMEvaluator(OPENAI_API_KEY)
        self.static_analyzer = StaticAnalyzer()
        self.code_executor = CodeExecutor()
        
        # Track active assessment sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def handle_assessment_task(
        self,
        white_agent_address: str,
        vulnerable_code: str,
        reference_fix: str,
        task_description: str,
        vulnerability: str,
        language: str = "python",
        context_id: Optional[str] = None
    ) -> AssessmentResult:
        """
        Handle a single vulnerability assessment task.
        
        Args:
            white_agent_address: A2A address of white agent to test
            vulnerable_code: The vulnerable code
            reference_fix: Reference solution for comparison
            task_description: Description of the task
            vulnerability: Vulnerability description
            language: Programming language
            context_id: Optional context ID for session management
            
        Returns:
            AssessmentResult with metrics
        """
        start_time = time.time()
        
        try:
            # Step 1: Create task message for white agent
            task_message = self._create_task_message(
                vulnerable_code=vulnerable_code,
                task_description=task_description,
                vulnerability=vulnerability,
                language=language
            )
            
            # Step 2: Send task to white agent and get response
            # For now, we'll use a direct HTTP call to white agent's A2A endpoint
            # In production, this would use the full A2A SDK client
            fixed_code = await self._send_task_to_white_agent(
                white_agent_address=white_agent_address,
                task_message=task_message,
                context_id=context_id
            )
            
            # Step 3: Evaluate the response using existing evaluators
            evaluation_metrics = await self._evaluate_response(
                fixed_code=fixed_code,
                reference_fix=reference_fix,
                vulnerable_code=vulnerable_code,
                task_description=task_description,
                language=language
            )
            
            # Calculate total time
            time_used = time.time() - start_time
            
            # Step 4: Return assessment results
            return AssessmentResult(
                success=evaluation_metrics['vulnerability_fixed'],
                similarity_score=evaluation_metrics['similarity_score'],
                vulnerability_fixed=evaluation_metrics['vulnerability_fixed'],
                code_executes=evaluation_metrics['code_executes'],
                static_analysis_pass=evaluation_metrics['static_analysis_pass'],
                time_used=time_used
            )
            
        except Exception as e:
            time_used = time.time() - start_time
            return AssessmentResult(
                success=False,
                similarity_score=0.0,
                vulnerability_fixed=False,
                code_executes=False,
                static_analysis_pass=False,
                time_used=time_used,
                error_message=str(e)
            )
    
    def _create_task_message(
        self,
        vulnerable_code: str,
        task_description: str,
        vulnerability: str,
        language: str
    ) -> str:
        """
        Create a self-explanatory task message for the white agent.
        
        Following Approach II from the blog: Send instructions in text format.
        The message must be self-explanatory (no benchmark-specific knowledge required).
        
        Args:
            vulnerable_code: The vulnerable code
            task_description: Description of what needs to be fixed
            vulnerability: Type of vulnerability
            language: Programming language
            
        Returns:
            Formatted task message
        """
        return f"""You are a security-focused code expert. Your task is to fix a security vulnerability in the following code.

**Vulnerability Type**: {vulnerability}

**Task**: {task_description}

**Vulnerable Code**:
```{language}
{vulnerable_code}
```

**Instructions**:
1. Analyze the security vulnerability in the code above
2. Provide a fixed version that addresses the vulnerability
3. Ensure the code maintains its original functionality
4. Return ONLY the fixed code without any explanations or markdown formatting

**Response Format**: Return only the fixed {language} code. Do not include explanations, comments about what you changed, or markdown code blocks."""
    
    async def _send_task_to_white_agent(
        self,
        white_agent_address: str,
        task_message: str,
        context_id: Optional[str] = None
    ) -> str:
        """
        Send task to white agent via A2A protocol.
        
        Args:
            white_agent_address: A2A endpoint address
            task_message: The task message
            context_id: Optional context ID
            
        Returns:
            Fixed code from white agent
        """
        # Import A2A SDK for sending messages
        try:
            from a2a import ClientSession, Message, Part, TextPart, Role
            
            # Create A2A client session
            async with ClientSession(white_agent_address) as session:
                # Create message
                message = Message(
                    role=Role.user,
                    parts=[Part(root=TextPart(kind='text', text=task_message))],
                    context_id=context_id
                )
                
                # Send message and get response
                response = await session.send_message(message)
                
                # Extract text from response
                if response and response.parts:
                    for part in response.parts:
                        if hasattr(part.root, 'text'):
                            return part.root.text
                
                raise ValueError("No text response from white agent")
                
        except ImportError:
            # Fallback: If A2A SDK not available, use HTTP directly
            import aiohttp
            
            async with aiohttp.ClientSession() as http_session:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": task_message}],
                            "context_id": context_id
                        }
                    },
                    "id": "1"
                }
                
                async with http_session.post(
                    white_agent_address,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    result = await resp.json()
                    
                    if 'result' in result and 'parts' in result['result']:
                        for part in result['result']['parts']:
                            if 'text' in part:
                                return part['text']
                    
                    raise ValueError(f"Invalid response from white agent: {result}")
    
    async def _evaluate_response(
        self,
        fixed_code: str,
        reference_fix: str,
        vulnerable_code: str,
        task_description: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Evaluate the white agent's response using existing evaluators.
        
        Args:
            fixed_code: Code returned by white agent
            reference_fix: Reference solution
            vulnerable_code: Original vulnerable code
            task_description: Task description
            language: Programming language
            
        Returns:
            Dictionary with evaluation metrics
        """
        # LLM Evaluation (similarity score and vulnerability fixed)
        llm_result = self.llm_evaluator.evaluate(
            agent_response=fixed_code,
            reference_solution=reference_fix,
            task_description=task_description,
            vulnerable_code=vulnerable_code
        )
        
        # Static Analysis (for Python only)
        static_analysis_pass = False
        if language.lower() == "python":
            static_result = self.static_analyzer.analyze(
                code=fixed_code,
                language=language
            )
            # Pass if no high/critical vulnerabilities
            static_analysis_pass = (
                static_result.get('high_severity', 0) == 0 and
                static_result.get('critical_severity', 0) == 0
            )
        
        # Code Execution (syntax check)
        exec_result = self.code_executor.test_code(
            code=fixed_code,
            language=language
        )
        code_executes = exec_result.get('success', False)
        
        return {
            'similarity_score': llm_result.get('similarity_score', 0.0),
            'vulnerability_fixed': llm_result.get('vulnerability_fixed', False),
            'static_analysis_pass': static_analysis_pass,
            'code_executes': code_executes
        }
    
    async def assess_multiple_tasks(
        self,
        white_agent_address: str,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assess multiple tasks and return aggregated metrics.
        
        Args:
            white_agent_address: A2A address of white agent
            tasks: List of task dictionaries with keys:
                   - vulnerable_code
                   - reference_fix
                   - task_description
                   - vulnerability
                   - language (optional, defaults to 'python')
            
        Returns:
            Dictionary with aggregated metrics
        """
        results = []
        
        for i, task in enumerate(tasks):
            print(f"[Green Agent] Evaluating task {i+1}/{len(tasks)}...")
            
            result = await self.handle_assessment_task(
                white_agent_address=white_agent_address,
                vulnerable_code=task['vulnerable_code'],
                reference_fix=task['reference_fix'],
                task_description=task['task_description'],
                vulnerability=task['vulnerability'],
                language=task.get('language', 'python'),
                context_id=f"task_{i}"
            )
            
            results.append(result)
        
        # Aggregate metrics
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.success)
        avg_similarity = sum(r.similarity_score for r in results) / total_tasks
        avg_time = sum(r.time_used for r in results) / total_tasks
        vulnerability_fix_rate = sum(1 for r in results if r.vulnerability_fixed) / total_tasks
        execution_rate = sum(1 for r in results if r.code_executes) / total_tasks
        
        return {
            'total_tasks': total_tasks,
            'successful_tasks': successful_tasks,
            'success_rate': successful_tasks / total_tasks,
            'avg_similarity_score': avg_similarity,
            'vulnerability_fix_rate': vulnerability_fix_rate,
            'execution_rate': execution_rate,
            'avg_time_per_task': avg_time,
            'individual_results': [asdict(r) for r in results]
        }
    
    def format_results_message(self, metrics: Dict[str, Any]) -> str:
        """
        Format assessment results as a human-readable message.
        
        Args:
            metrics: Assessment metrics dictionary
            
        Returns:
            Formatted message string
        """
        success_rate = metrics.get('success_rate', 0)
        success_emoji = "✅" if success_rate > 0.8 else "⚠️"
        
        total = metrics.get('total_tasks', 0)
        successful = metrics.get('successful_fixes', metrics.get('successful_tasks', 0))
        
        message = f"""Assessment Complete {success_emoji}

📊 **Overall Metrics**:
- Agent: {metrics.get('agent', 'Unknown')}
- Model: {metrics.get('model', 'Unknown')}
- Total Tasks: {total}
- Successful Fixes: {successful}
- Success Rate: {success_rate:.1%}
- Code Execution Rate: {metrics.get('execution_rate', 0):.1%}
- Average Similarity Score: {metrics.get('avg_similarity_score', 0):.2f}/10
- Average Time per Task: {metrics.get('avg_time_per_task', 0):.2f}s

🎯 **Assessment Summary**:
The agent successfully fixed {successful}/{total} vulnerabilities.
"""
        return message

