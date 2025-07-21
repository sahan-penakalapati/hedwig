"""
Agent Executor for tool orchestration in the Hedwig system.

The AgentExecutor is the core execution engine that provides LLM-based agents
with access to tools through the SecurityGateway, handling the orchestration
of multi-step task execution.
"""

import json
import re
from typing import Dict, Any, List, Optional, Callable, Union

from hedwig.core.models import TaskInput, ToolOutput, Artifact
from hedwig.core.logging_config import get_logger
from hedwig.core.exceptions import AgentExecutionError
from hedwig.tools.registry import ToolRegistry
from hedwig.tools.security import SecurityGateway
from hedwig.tools.base import Tool


class AgentExecutor:
    """
    Core execution engine that orchestrates tool calls for LLM-based agents.
    
    The AgentExecutor provides a bridge between LLM agents and the tool system,
    handling:
    - Tool discovery and description formatting for LLM context
    - Secure tool execution through the SecurityGateway
    - Multi-step task orchestration
    - Artifact collection and management
    - Error handling and recovery
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        security_gateway: SecurityGateway,
        llm_callback: Optional[Callable[[str], str]] = None,
        max_iterations: int = 10
    ):
        """
        Initialize the AgentExecutor.
        
        Args:
            tool_registry: Registry of available tools
            security_gateway: Security gateway for tool execution
            llm_callback: Function to call LLM with prompt and get response
            max_iterations: Maximum number of execution steps to prevent infinite loops
        """
        self.tool_registry = tool_registry
        self.security_gateway = security_gateway
        self.llm_callback = llm_callback
        self.max_iterations = max_iterations
        
        self.logger = get_logger("hedwig.agents.executor")
        
        # Track execution state
        self.current_iteration = 0
        self.collected_artifacts: List[Artifact] = []
        self.execution_log: List[Dict[str, Any]] = []
    
    def invoke(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using available tools and LLM reasoning.
        
        This is the main entry point for agent task execution.
        
        Args:
            task_input: Dictionary containing:
                - input: The main task prompt
                - conversation: Optional conversation history
                - tools: Optional list of specific tools to use
                - parameters: Optional additional parameters
                
        Returns:
            Dictionary containing execution results and artifacts
        """
        try:
            self.logger.info("Starting agent execution")
            
            # Reset execution state
            self.current_iteration = 0
            self.collected_artifacts = []
            self.execution_log = []
            
            # Extract task components
            main_prompt = task_input.get("input", "")
            conversation = task_input.get("conversation", "")
            available_tools = task_input.get("tools", None)
            parameters = task_input.get("parameters", {})
            
            if not main_prompt:
                raise AgentExecutionError("No input prompt provided", "AgentExecutor")
            
            # Get available tools context
            tools_context = self._build_tools_context(available_tools)
            
            # Build the initial LLM prompt
            system_prompt = self._build_system_prompt(tools_context, conversation)
            full_prompt = f"{system_prompt}\n\nUser Request: {main_prompt}"
            
            # Execute the reasoning loop
            final_result = self._execute_reasoning_loop(full_prompt, parameters)
            
            self.logger.info(f"Agent execution completed in {self.current_iteration} iterations")
            
            return {
                "output": final_result,
                "artifacts": self.collected_artifacts,
                "iterations": self.current_iteration,
                "execution_log": self.execution_log,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {str(e)}")
            
            return {
                "output": f"Task execution failed: {str(e)}",
                "artifacts": self.collected_artifacts,
                "iterations": self.current_iteration,
                "execution_log": self.execution_log,
                "success": False,
                "error": str(e)
            }
    
    def _execute_reasoning_loop(self, initial_prompt: str, parameters: Dict[str, Any]) -> str:
        """
        Execute the main reasoning loop with tool calling.
        
        Args:
            initial_prompt: The initial system prompt with context
            parameters: Additional execution parameters
            
        Returns:
            Final response from the execution
        """
        current_prompt = initial_prompt
        
        for iteration in range(self.max_iterations):
            self.current_iteration = iteration + 1
            
            self.logger.debug(f"Iteration {self.current_iteration}/{self.max_iterations}")
            
            # Get LLM response
            if not self.llm_callback:
                # If no LLM callback, return a simple mock response
                return self._generate_mock_response(current_prompt)
            
            llm_response = self.llm_callback(current_prompt)
            
            # Log this step
            self._log_execution_step("llm_response", {
                "iteration": self.current_iteration,
                "response": llm_response[:500] + "..." if len(llm_response) > 500 else llm_response
            })
            
            # Check if the response contains a tool call
            tool_call = self._extract_tool_call(llm_response)
            
            if not tool_call:
                # No tool call found - this is the final response
                self.logger.info("No tool call found, treating as final response")
                return llm_response
            
            # Execute the tool call
            tool_result = self._execute_tool_call(tool_call)
            
            # Update prompt with tool result for next iteration
            current_prompt = self._build_followup_prompt(
                initial_prompt, 
                llm_response, 
                tool_call, 
                tool_result
            )
        
        # If we hit max iterations, return what we have
        self.logger.warning(f"Reached max iterations ({self.max_iterations})")
        return f"Task partially completed. Reached maximum iteration limit ({self.max_iterations})."
    
    def _build_tools_context(self, specific_tools: Optional[List[str]] = None) -> str:
        """
        Build context about available tools for the LLM.
        
        Args:
            specific_tools: Optional list of specific tool names to include
            
        Returns:
            Formatted string describing available tools
        """
        if specific_tools:
            # Filter to only specific tools
            available_tools = []
            for tool_name in specific_tools:
                if self.tool_registry.has_tool(tool_name):
                    available_tools.append(self.tool_registry.get(tool_name))
        else:
            # Use all available tools
            available_tools = self.tool_registry.list_tools()
        
        if not available_tools:
            return "No tools available."
        
        lines = ["Available Tools:"]
        lines.append("=" * 50)
        
        for tool in available_tools:
            lines.append(f"\n**{tool.name}**")
            lines.append(f"Description: {tool.description}")
            lines.append(f"Risk Level: {tool.risk_tier.value}")
            lines.append(tool.get_schema_description())
        
        return "\n".join(lines)
    
    def _build_system_prompt(self, tools_context: str, conversation: str) -> str:
        """
        Build the system prompt for the LLM.
        
        Args:
            tools_context: Description of available tools
            conversation: Previous conversation context
            
        Returns:
            Complete system prompt
        """
        prompt = """You are an AI assistant with access to specialized tools to help complete user tasks.

IMPORTANT: When you need to use a tool, format your tool call EXACTLY like this:
TOOL_CALL: {
  "tool_name": "exact_tool_name",
  "arguments": {
    "arg1": "value1",
    "arg2": "value2"
  }
}

After making a tool call, wait for the tool result before proceeding. You can make multiple tool calls if needed.

When you have completed the task, provide a final response without any tool calls.

"""
        
        if conversation:
            prompt += f"\n{conversation}\n"
        
        prompt += f"\n{tools_context}\n"
        
        return prompt
    
    def _extract_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Extract tool call from LLM response.
        
        Args:
            llm_response: Response from the LLM
            
        Returns:
            Dictionary with tool call details, or None if no tool call found
        """
        # Look for TOOL_CALL: pattern
        pattern = r'TOOL_CALL:\s*\{([^}]+)\}'
        match = re.search(pattern, llm_response, re.DOTALL)
        
        if not match:
            return None
        
        try:
            # Extract and parse the JSON
            tool_call_json = '{' + match.group(1) + '}'
            tool_call = json.loads(tool_call_json)
            
            # Validate required fields
            if "tool_name" not in tool_call:
                self.logger.warning("Tool call missing 'tool_name' field")
                return None
            
            return {
                "tool_name": tool_call["tool_name"],
                "arguments": tool_call.get("arguments", {}),
                "raw_call": tool_call_json
            }
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse tool call JSON: {e}")
            return None
    
    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call through the security gateway.
        
        Args:
            tool_call: Tool call details
            
        Returns:
            Tool execution results
        """
        tool_name = tool_call["tool_name"]
        arguments = tool_call["arguments"]
        
        self.logger.info(f"Executing tool call: {tool_name}")
        
        try:
            # Get the tool from registry
            if not self.tool_registry.has_tool(tool_name):
                error_msg = f"Tool '{tool_name}' not found in registry"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "text_summary": f"Error: {error_msg}"
                }
            
            tool = self.tool_registry.get(tool_name)
            
            # Execute through security gateway
            result = self.security_gateway.execute_tool(tool, **arguments)
            
            # Collect any artifacts
            if hasattr(result, 'artifacts') and result.artifacts:
                self.collected_artifacts.extend(result.artifacts)
                self.logger.info(f"Collected {len(result.artifacts)} artifacts from {tool_name}")
            
            # Log successful execution
            self._log_execution_step("tool_execution", {
                "tool_name": tool_name,
                "arguments": arguments,
                "success": getattr(result, 'success', True),
                "artifacts_count": len(getattr(result, 'artifacts', []))
            })
            
            return {
                "success": getattr(result, 'success', True),
                "text_summary": getattr(result, 'text_summary', str(result)),
                "artifacts": getattr(result, 'artifacts', []),
                "metadata": getattr(result, 'metadata', {})
            }
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Log failed execution
            self._log_execution_step("tool_execution_error", {
                "tool_name": tool_name,
                "arguments": arguments,
                "error": str(e)
            })
            
            return {
                "success": False,
                "error": error_msg,
                "text_summary": f"Error executing {tool_name}: {str(e)}"
            }
    
    def _build_followup_prompt(
        self, 
        initial_prompt: str,
        llm_response: str,
        tool_call: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> str:
        """
        Build the follow-up prompt after a tool execution.
        
        Args:
            initial_prompt: The original system prompt
            llm_response: The LLM response that contained the tool call
            tool_call: The tool call that was executed
            tool_result: The result of the tool execution
            
        Returns:
            Updated prompt for the next iteration
        """
        followup = f"""
Previous response: {llm_response}

Tool call executed: {tool_call['tool_name']}
Tool result: {tool_result['text_summary']}

Continue with the task. You can make another tool call if needed, or provide a final response.
"""
        
        return initial_prompt + followup
    
    def _generate_mock_response(self, prompt: str) -> str:
        """
        Generate a mock response when no LLM callback is available.
        
        This is primarily for testing and development.
        
        Args:
            prompt: The prompt that would be sent to the LLM
            
        Returns:
            Mock response
        """
        return "Mock response: Task would be executed with available tools. No LLM callback configured."
    
    def _log_execution_step(self, step_type: str, data: Dict[str, Any]) -> None:
        """
        Log an execution step for debugging and analysis.
        
        Args:
            step_type: Type of execution step
            data: Step data to log
        """
        log_entry = {
            "iteration": self.current_iteration,
            "step_type": step_type,
            "timestamp": None,  # Could add timestamp if needed
            "data": data
        }
        
        self.execution_log.append(log_entry)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current execution state.
        
        Returns:
            Dictionary with execution summary
        """
        return {
            "iterations": self.current_iteration,
            "max_iterations": self.max_iterations,
            "artifacts_collected": len(self.collected_artifacts),
            "execution_steps": len(self.execution_log),
            "tools_available": len(self.tool_registry),
            "security_gateway_active": self.security_gateway is not None
        }