"""
Base Agent class and agent infrastructure for the Hedwig system.

This module defines the abstract base class that all agents must inherit from,
providing a standardized interface for task execution and agent management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from hedwig.core.models import TaskInput, TaskOutput, ConversationMessage, ErrorCode
from hedwig.core.logging_config import get_logger
from hedwig.core.exceptions import AgentExecutionError


class BaseAgent(ABC):
    """
    Abstract base class for all Hedwig agents.
    
    All agents must inherit from this class and implement the required methods
    to ensure standardized agent behavior and integration with the system.
    
    This class provides:
    - Consistent agent interface with a `run` method signature
    - Shared functionality like logging, error handling, and basic management
    - Structured agent descriptions for dispatcher routing
    - Standard error handling with TaskOutput conversion
    """
    
    def __init__(self, name: str = None):
        """
        Initialize the agent.
        
        Args:
            name: Optional custom name for the agent. If not provided,
                  uses the class name converted to snake_case.
        """
        self.name = name or self._generate_agent_name()
        self.logger = get_logger(f"hedwig.agents.{self.name}")
    
    @property
    @abstractmethod
    def description(self) -> Dict[str, Any]:
        """
        Structured description of the agent for dispatcher routing.
        
        Must return a dictionary with the following schema:
        - agent_name (str): The unique name of the agent (e.g., 'SWEAgent')
        - purpose (str): A one-sentence description of the agent's primary function
        - capabilities (list[str]): List of keywords describing specific abilities
        - example_tasks (list[str]): List of 2-3 concrete example prompts
        
        Returns:
            Dictionary containing agent description
        """
        pass
    
    @abstractmethod
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute the agent's primary functionality.
        
        This method contains the actual implementation logic.
        Subclasses must implement this method.
        
        Args:
            task_input: TaskInput containing prompt, parameters, and context
            
        Returns:
            TaskOutput containing results and any generated artifacts
        """
        pass
    
    def run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute the agent with error handling and logging.
        
        This is the public interface used by HedwigApp and DispatcherAgent.
        It wraps _run with consistent error handling and logging.
        
        Args:
            task_input: TaskInput containing task details
            
        Returns:
            TaskOutput containing results or error information
        """
        try:
            self.logger.info(f"Agent '{self.name}' starting task execution")
            
            # Validate task input
            if not task_input.prompt:
                return TaskOutput(
                    content="No task prompt provided",
                    success=False,
                    error="Empty or missing task prompt",
                    error_code=ErrorCode.INVALID_INPUT,
                    conversation=task_input.conversation or []
                )
            
            # Execute the agent
            result = self._run(task_input)
            
            # Ensure the result has conversation context
            if not result.conversation:
                result.conversation = task_input.conversation or []
            
            self.logger.info(f"Agent '{self.name}' completed task successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error running agent '{self.name}': {str(e)}"
            self.logger.error(error_msg)
            
            # Create error output following PRD specification
            return TaskOutput(
                content=f"I encountered an error while processing your request: {str(e)}",
                success=False,
                error=error_msg,
                error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                conversation=task_input.conversation or [],
                metadata={
                    "agent_name": self.name,
                    "agent_class": self.__class__.__name__,
                    "error_type": type(e).__name__
                }
            )
    
    def can_handle_task(self, prompt: str, conversation: Optional[List[ConversationMessage]] = None) -> bool:
        """
        Determine if this agent can handle a specific task.
        
        This method can be overridden by subclasses to provide more sophisticated
        task matching logic. The default implementation always returns True.
        
        Args:
            prompt: The task prompt to evaluate
            conversation: Optional conversation history for context
            
        Returns:
            True if the agent can handle the task, False otherwise
        """
        return True
    
    def reject_task(self, reason: str, task_input: TaskInput) -> TaskOutput:
        """
        Reject a task that this agent cannot or should not handle.
        
        This creates a standardized rejection response that the dispatcher
        can recognize for re-routing.
        
        Args:
            reason: Human-readable reason for rejection
            task_input: The original task input
            
        Returns:
            TaskOutput with rejection details
        """
        self.logger.info(f"Agent '{self.name}' rejecting task: {reason}")
        
        return TaskOutput(
            content=f"I cannot handle this task: {reason}",
            success=False,
            error=f"Task rejected by {self.name}: {reason}",
            error_code=ErrorCode.TASK_REJECTED_AS_INAPPROPRIATE,
            conversation=task_input.conversation or [],
            metadata={
                "agent_name": self.name,
                "rejection_reason": reason,
                "can_retry": True
            }
        )
    
    def _generate_agent_name(self) -> str:
        """
        Generate agent name from class name.
        
        Converts CamelCase class names to snake_case agent names.
        E.g., "SWEAgent" -> "swe_agent", "GeneralAgent" -> "general_agent"
        
        Returns:
            Snake case agent name
        """
        class_name = self.__class__.__name__
        
        # Remove "Agent" suffix if present
        if class_name.endswith("Agent"):
            class_name = class_name[:-5]
        
        # Convert CamelCase to snake_case
        import re
        snake_case = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_case).lower()
        
        return snake_case
    
    def get_description_summary(self) -> str:
        """
        Get a human-readable summary of the agent's capabilities.
        
        Returns:
            Formatted string describing the agent
        """
        desc = self.description
        
        lines = [
            f"Agent: {desc.get('agent_name', self.name)}",
            f"Purpose: {desc.get('purpose', 'No description available')}",
        ]
        
        capabilities = desc.get('capabilities', [])
        if capabilities:
            lines.append(f"Capabilities: {', '.join(capabilities)}")
        
        examples = desc.get('example_tasks', [])
        if examples:
            lines.append("Example tasks:")
            for i, example in enumerate(examples, 1):
                lines.append(f"  {i}. {example}")
        
        return "\n".join(lines)
    
    def add_conversation_message(
        self, 
        content: str, 
        role: str = "assistant",
        conversation: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Add a message to the conversation history.
        
        Args:
            content: Message content
            role: Message role (assistant, user, system)
            conversation: Existing conversation to append to (in dict format)
            
        Returns:
            Updated conversation history as list of dicts
        """
        if conversation is None:
            conversation = []
        
        message = {
            "role": role,
            "content": content
        }
        
        conversation.append(message)
        return conversation
    
    def format_conversation_for_llm(
        self, 
        conversation: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Format conversation history for LLM consumption.
        
        Args:
            conversation: Conversation history to format (list of dicts)
            
        Returns:
            Formatted conversation string
        """
        if not conversation:
            return "No previous conversation."
        
        lines = ["Previous conversation:"]
        for msg in conversation[-10:]:  # Limit to last 10 messages
            role = msg["role"].upper()
            content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return self.__str__()