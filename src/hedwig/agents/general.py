"""
General Agent for handling diverse tasks in the Hedwig system.

The GeneralAgent is a flexible, multi-purpose agent that can handle
a wide variety of tasks using the available tool system. It serves
as the default agent and fallback for tasks that don't require
specialized domain expertise.
"""

from typing import Dict, Any, List, Optional

from hedwig.core.models import TaskInput, TaskOutput, ConversationMessage, ErrorCode
from hedwig.core.logging_config import get_logger
from hedwig.agents.base import BaseAgent
from hedwig.agents.executor import AgentExecutor


class GeneralAgent(BaseAgent):
    """
    General-purpose agent for handling diverse tasks.
    
    The GeneralAgent is designed to handle a wide variety of tasks
    including:
    - File operations and document management
    - Basic research and information gathering
    - Simple automation tasks
    - Artifact management and organization
    - General problem-solving tasks
    
    It uses the AgentExecutor to orchestrate tool usage and provides
    a flexible foundation for task execution.
    """
    
    def __init__(self, agent_executor: Optional[AgentExecutor] = None, name: str = None):
        """
        Initialize the GeneralAgent.
        
        Args:
            agent_executor: AgentExecutor for tool orchestration
            name: Optional custom agent name
        """
        super().__init__(name)
        self.agent_executor = agent_executor
        
        # Track agent usage statistics
        self.tasks_completed = 0
        self.tools_used = set()
        self.task_categories = {
            "file_operations": 0,
            "research": 0,
            "artifacts": 0,
            "general": 0
        }
    
    @property
    def description(self) -> Dict[str, Any]:
        """
        Structured description for dispatcher routing.
        
        Returns:
            Dictionary with agent description following PRD specification
        """
        return {
            "agent_name": "GeneralAgent",
            "purpose": "Handles diverse general-purpose tasks including file operations, basic research, and task automation.",
            "capabilities": [
                "file_operations",
                "document_management", 
                "basic_research",
                "artifact_management",
                "task_automation",
                "information_organization",
                "general_problem_solving"
            ],
            "example_tasks": [
                "List all the PDF files in the current project and summarize their contents",
                "Read the configuration file and explain what each setting does", 
                "Create a summary of all the artifacts generated in this conversation"
            ]
        }
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute a general task using available tools.
        
        Args:
            task_input: TaskInput containing the task details
            
        Returns:
            TaskOutput with execution results
        """
        try:
            self.logger.info(f"GeneralAgent executing task: {task_input.prompt[:100]}...")
            
            if not self.agent_executor:
                return self._handle_without_executor(task_input)
            
            # Categorize the task for statistics
            category = self._categorize_task(task_input.prompt)
            self.task_categories[category] += 1
            
            # Build executor input
            executor_input = {
                "input": task_input.prompt,
                "conversation": self._format_conversation(task_input.conversation),
                "tools": task_input.tools,
                "parameters": task_input.parameters or {}
            }
            
            # Execute using AgentExecutor
            result = self.agent_executor.invoke(executor_input)
            
            # Process results
            if result["success"]:
                self.tasks_completed += 1
                
                # Track tools used
                for log_entry in result.get("execution_log", []):
                    if log_entry["step_type"] == "tool_execution":
                        self.tools_used.add(log_entry["data"]["tool_name"])
                
                # Create successful response
                return TaskOutput(
                    content=result["output"],
                    success=True,
                    result=result["output"],
                    conversation=self._update_conversation(
                        task_input.conversation,
                        task_input.prompt,
                        result["output"]
                    ),
                    metadata={
                        "agent_type": "GeneralAgent",
                        "iterations": result["iterations"],
                        "artifacts_generated": len(result["artifacts"]),
                        "tools_used": len([log for log in result["execution_log"] if log["step_type"] == "tool_execution"]),
                        "task_category": category,
                        "artifacts": result["artifacts"]
                    }
                )
            else:
                # Handle execution failure
                error_msg = result.get("error", "Unknown execution error")
                self.logger.error(f"GeneralAgent execution failed: {error_msg}")
                
                return TaskOutput(
                    content=f"I encountered an error while processing your request: {result['output']}",
                    success=False,
                    error=error_msg,
                    error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                    conversation=task_input.conversation or [],
                    metadata={
                        "agent_type": "GeneralAgent",
                        "iterations": result["iterations"],
                        "error_type": "execution_failure",
                        "task_category": category
                    }
                )
                
        except Exception as e:
            self.logger.error(f"GeneralAgent error: {str(e)}")
            return TaskOutput(
                content=f"I'm sorry, I encountered an unexpected error: {str(e)}",
                success=False,
                error=str(e),
                error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                conversation=task_input.conversation or [],
                metadata={
                    "agent_type": "GeneralAgent",
                    "error_type": "unexpected_error"
                }
            )
    
    def _handle_without_executor(self, task_input: TaskInput) -> TaskOutput:
        """
        Handle tasks when no AgentExecutor is available.
        
        This provides a fallback mode for basic operation.
        
        Args:
            task_input: The task to handle
            
        Returns:
            TaskOutput with basic response
        """
        self.logger.warning("No AgentExecutor available, providing basic response")
        
        # Analyze task for basic capabilities
        prompt_lower = task_input.prompt.lower()
        
        if any(word in prompt_lower for word in ['file', 'read', 'open', 'list']):
            response = ("I understand you want to work with files. However, I need an "
                       "AgentExecutor with tool access to perform file operations. "
                       "Please configure the system with proper tool access.")
        elif any(word in prompt_lower for word in ['artifact', 'generated', 'created']):
            response = ("I understand you want to work with artifacts. However, I need an "
                       "AgentExecutor with tool access to manage artifacts. "
                       "Please configure the system with proper tool access.")
        elif any(word in prompt_lower for word in ['research', 'search', 'find']):
            response = ("I understand you want to research something. However, I need an "
                       "AgentExecutor with tool access to perform research tasks. "
                       "Please configure the system with proper tool access.")
        else:
            response = ("I'm a general-purpose assistant that can help with various tasks "
                       "including file operations, research, and artifact management. "
                       "However, I need an AgentExecutor with tool access to perform most tasks. "
                       "Please configure the system with proper tool access.")
        
        return TaskOutput(
            content=response,
            success=False,
            error="No AgentExecutor configured",
            error_code=ErrorCode.CONFIGURATION_ERROR,
            conversation=self._update_conversation(
                task_input.conversation,
                task_input.prompt,
                response
            ),
            metadata={
                "agent_type": "GeneralAgent",
                "error_type": "no_executor"
            }
        )
    
    def _categorize_task(self, prompt: str) -> str:
        """
        Categorize a task for statistics tracking.
        
        Args:
            prompt: The task prompt
            
        Returns:
            Task category string
        """
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['file', 'read', 'write', 'open', 'save']):
            return "file_operations"
        elif any(word in prompt_lower for word in ['research', 'search', 'find', 'investigate']):
            return "research"
        elif any(word in prompt_lower for word in ['artifact', 'generated', 'list', 'show']):
            return "artifacts"
        else:
            return "general"
    
    def _format_conversation(self, conversation: Optional[List[Dict[str, str]]]) -> str:
        """
        Format conversation history for AgentExecutor.
        
        Args:
            conversation: List of conversation message dicts
            
        Returns:
            Formatted conversation string
        """
        if not conversation:
            return ""
        
        lines = []
        for msg in conversation[-5:]:  # Last 5 messages for context
            role = msg["role"].upper()
            content = msg["content"][:300] + "..." if len(msg["content"]) > 300 else msg["content"]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def _update_conversation(
        self,
        existing_conversation: Optional[List[Dict[str, str]]],
        user_prompt: str,
        agent_response: str
    ) -> List[Dict[str, str]]:
        """
        Update conversation history with the current exchange.
        
        Args:
            existing_conversation: Previous conversation messages (as dicts)
            user_prompt: The user's prompt
            agent_response: The agent's response
            
        Returns:
            Updated conversation history as list of dicts
        """
        conversation = existing_conversation[:] if existing_conversation else []
        
        # Add user message if not already present (avoid duplication)
        if not conversation or conversation[-1]["content"] != user_prompt:
            conversation = self.add_conversation_message(
                user_prompt, 
                role="user", 
                conversation=conversation
            )
        
        # Add agent response
        conversation = self.add_conversation_message(
            agent_response,
            role="assistant",
            conversation=conversation
        )
        
        return conversation
    
    def can_handle_task(self, prompt: str, conversation: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Determine if this agent can handle a specific task.
        
        The GeneralAgent can handle most tasks, but may reject very specialized
        tasks that would be better handled by domain specialists.
        
        Args:
            prompt: The task prompt to evaluate
            conversation: Optional conversation history
            
        Returns:
            True if the agent can handle the task
        """
        prompt_lower = prompt.lower()
        
        # Reject highly specialized tasks that should go to specialists
        specialized_patterns = [
            # Complex software development tasks
            ("complex code", ["refactor entire", "design pattern", "architecture", "microservice"]),
            # Advanced research tasks  
            ("advanced research", ["systematic review", "meta-analysis", "academic paper"]),
            # Very technical tasks
            ("technical analysis", ["performance profiling", "security audit", "penetration test"])
        ]
        
        for category, patterns in specialized_patterns:
            if any(pattern in prompt_lower for pattern in patterns):
                self.logger.info(f"Rejecting {category} task - better suited for specialist")
                return False
        
        return True
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about agent usage.
        
        Returns:
            Dictionary with agent statistics
        """
        return {
            "agent_name": "GeneralAgent",
            "tasks_completed": self.tasks_completed,
            "tools_used": list(self.tools_used),
            "unique_tools_count": len(self.tools_used),
            "task_categories": dict(self.task_categories),
            "has_executor": self.agent_executor is not None
        }
    
    def reset_statistics(self) -> None:
        """Reset agent usage statistics."""
        self.tasks_completed = 0
        self.tools_used.clear()
        self.task_categories = {
            "file_operations": 0,
            "research": 0, 
            "artifacts": 0,
            "general": 0
        }
        self.logger.info("Agent statistics reset")
    
    def set_agent_executor(self, executor: AgentExecutor) -> None:
        """
        Set the AgentExecutor for this agent.
        
        Args:
            executor: AgentExecutor instance to use
        """
        self.agent_executor = executor
        self.logger.info("AgentExecutor configured")
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"GeneralAgent(name='{self.name}', tasks_completed={self.tasks_completed})"