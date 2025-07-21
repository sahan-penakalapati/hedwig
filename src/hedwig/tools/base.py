"""
Base Tool class and tool infrastructure for the Hedwig system.

This module defines the abstract base class that all tools must inherit from,
providing a standardized interface for tool execution and metadata.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from pydantic import BaseModel

from hedwig.core.models import RiskTier, ToolOutput
from hedwig.core.logging_config import get_logger


class Tool(ABC):
    """
    Abstract base class for all Hedwig tools.
    
    All tools must inherit from this class and implement the required methods
    to ensure standardized tool behavior and integration with the agent system.
    """
    
    def __init__(self, name: str = None):
        """
        Initialize the tool.
        
        Args:
            name: Optional custom name for the tool. If not provided,
                  uses the class name converted to snake_case.
        """
        self.name = name or self._generate_tool_name()
        self.logger = get_logger(f"hedwig.tools.{self.name}")
    
    @property
    @abstractmethod
    def args_schema(self) -> Type[BaseModel]:
        """
        Pydantic model defining the tool's input parameters.
        
        This schema is used by the AgentExecutor to validate and provide
        the correct arguments to the tool at runtime.
        
        Returns:
            Pydantic model class defining input schema
        """
        pass
    
    @property
    @abstractmethod
    def risk_tier(self) -> RiskTier:
        """
        Base risk tier for this tool.
        
        The SecurityGateway may escalate this risk based on dynamic
        analysis of the specific arguments provided.
        
        Returns:
            RiskTier enum value
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what this tool does.
        
        Used for tool discovery and to provide context to LLM agents
        about available capabilities.
        
        Returns:
            Tool description string
        """
        pass
    
    @abstractmethod
    def _run(self, **kwargs) -> ToolOutput:
        """
        Execute the tool's primary functionality.
        
        This method contains the actual implementation logic.
        Subclasses must implement this method.
        
        Args:
            **kwargs: Tool parameters validated against args_schema
            
        Returns:
            ToolOutput containing results and any generated artifacts
        """
        pass
    
    def run(self, **kwargs) -> ToolOutput:
        """
        Execute the tool with error handling and logging.
        
        This is the public interface used by the AgentExecutor.
        It wraps _run with consistent error handling and logging.
        
        Args:
            **kwargs: Tool parameters validated against args_schema
            
        Returns:
            ToolOutput containing results or error information
        """
        try:
            self.logger.info(f"Executing tool '{self.name}' with args: {kwargs}")
            
            # Validate input arguments against schema
            validated_args = self.args_schema(**kwargs)
            
            # Execute the tool
            result = self._run(**validated_args.model_dump())
            
            self.logger.info(f"Tool '{self.name}' completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Tool '{self.name}' failed: {str(e)}")
            return ToolOutput(
                text_summary=f"Tool execution failed: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _generate_tool_name(self) -> str:
        """
        Generate tool name from class name.
        
        Converts CamelCase class names to snake_case tool names.
        E.g., "FileReaderTool" -> "file_reader"
        
        Returns:
            Snake case tool name
        """
        class_name = self.__class__.__name__
        
        # Remove "Tool" suffix if present
        if class_name.endswith("Tool"):
            class_name = class_name[:-4]
        
        # Convert CamelCase to snake_case
        import re
        snake_case = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_case).lower()
        
        return snake_case
    
    def get_schema_description(self) -> str:
        """
        Get a formatted description of the tool's input schema.
        
        Returns:
            Human-readable schema description
        """
        schema = self.args_schema.model_json_schema()
        properties = schema.get("properties", {})
        
        if not properties:
            return "No input parameters required."
        
        lines = ["Input parameters:"]
        for field_name, field_info in properties.items():
            field_type = field_info.get("type", "unknown")
            field_desc = field_info.get("description", "No description")
            required = field_name in schema.get("required", [])
            req_marker = " (required)" if required else " (optional)"
            
            lines.append(f"  - {field_name} ({field_type}){req_marker}: {field_desc}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.__class__.__name__}(name='{self.name}', risk={self.risk_tier.value})"
    
    def __repr__(self) -> str:
        """Developer representation of the tool."""
        return self.__str__()