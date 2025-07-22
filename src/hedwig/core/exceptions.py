"""
Standardized error handling framework for the Hedwig system.

Provides custom exception classes and error handling utilities
to ensure consistent error reporting across all components.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from hedwig.core.models import ErrorCode, TaskOutput, ToolOutput


class HedwigError(Exception):
    """Base exception class for all Hedwig-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize Hedwig error.
        
        Args:
            message: Human-readable error message
            error_code: Standard error code for programmatic handling
            details: Additional error details/context
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code.value,
            "details": self.details
        }
        
        if self.cause:
            result["caused_by"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
        
        return result


class TaskRejectedError(HedwigError):
    """Raised when an agent rejects a task as inappropriate."""
    
    def __init__(self, message: str, agent_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.TASK_REJECTED_AS_INAPPROPRIATE,
            details={"agent_name": agent_name, **(details or {})}
        )
        self.agent_name = agent_name


class SecurityGatewayError(HedwigError):
    """Raised when security gateway denies a tool execution."""
    
    def __init__(self, message: str, tool_name: str, risk_tier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.SECURITY_GATEWAY_DENIAL,
            details={"tool_name": tool_name, "risk_tier": risk_tier, **(details or {})}
        )
        self.tool_name = tool_name
        self.risk_tier = risk_tier


class ToolExecutionError(HedwigError):
    """Raised when a tool execution fails."""
    
    def __init__(self, message: str, tool_name: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.TOOL_EXECUTION_FAILED,
            details={"tool_name": tool_name, **(details or {})},
            cause=cause
        )
        self.tool_name = tool_name


class AgentExecutionError(HedwigError):
    """Raised when an agent execution fails."""
    
    def __init__(self, message: str, agent_name: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AGENT_EXECUTION_FAILED,
            details={"agent_name": agent_name, **(details or {})},
            cause=cause
        )
        self.agent_name = agent_name


class ArtifactNotFoundError(HedwigError):
    """Raised when a requested artifact cannot be found."""
    
    def __init__(self, message: str, artifact_id: Optional[str] = None, file_path: Optional[str] = None):
        details = {}
        if artifact_id:
            details["artifact_id"] = artifact_id
        if file_path:
            details["file_path"] = file_path
            
        super().__init__(
            message=message,
            error_code=ErrorCode.ARTIFACT_NOT_FOUND,
            details=details
        )


class ValidationError(HedwigError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_INPUT,
            details={"field": field, **(details or {})} if field else details
        )
        self.field = field


class TimeoutError(HedwigError):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, timeout_seconds: Optional[float] = None, operation: Optional[str] = None):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code=ErrorCode.TIMEOUT_EXCEEDED,
            details=details
        )


class LLMIntegrationError(HedwigError):
    """Error raised when LLM integration fails."""
    
    def __init__(self, message: str, component: str, provider: str = None):
        super().__init__(
            message,
            ErrorCode.GENERAL_ERROR,  # Using general error, could add specific LLM error code
            details={"component": component, "provider": provider}
        )


class ErrorHandler:
    """Utility class for consistent error handling across Hedwig components."""
    
    def __init__(self, component_name: str):
        """
        Initialize error handler for a specific component.
        
        Args:
            component_name: Name of the component (for logging context)
        """
        self.component_name = component_name
        self.logger = logging.getLogger(f"{__name__}.{component_name}")
    
    def handle_exception(self, e: Exception, context: str = "") -> HedwigError:
        """
        Convert a general exception to a HedwigError with proper logging.
        
        Args:
            e: The original exception
            context: Additional context about where the error occurred
            
        Returns:
            Appropriate HedwigError subclass
        """
        if isinstance(e, HedwigError):
            # Already a Hedwig error, just log and return
            self.logger.error(f"{context}: {e.message}", exc_info=e.cause is not None)
            return e
        
        # Convert general exception to HedwigError
        error_message = f"Unexpected error in {self.component_name}"
        if context:
            error_message += f" ({context})"
        error_message += f": {str(e)}"
        
        # Log the full traceback
        self.logger.error(error_message, exc_info=True)
        
        # Determine appropriate error type
        if "timeout" in str(e).lower():
            return TimeoutError(error_message, details={"original_error": str(e)})
        elif "validation" in str(e).lower():
            return ValidationError(error_message, details={"original_error": str(e)})
        else:
            # Generic execution error
            if "agent" in self.component_name.lower():
                return AgentExecutionError(error_message, self.component_name, cause=e)
            elif "tool" in self.component_name.lower():
                return ToolExecutionError(error_message, self.component_name, cause=e)
            else:
                return HedwigError(error_message, ErrorCode.AGENT_EXECUTION_FAILED, cause=e)
    
    def create_error_task_output(self, error: HedwigError, conversation: Optional[list] = None) -> TaskOutput:
        """
        Create a TaskOutput representing an error condition.
        
        Args:
            error: The error that occurred
            conversation: Optional conversation history to include
            
        Returns:
            TaskOutput with error information
        """
        return TaskOutput(
            content=f"I'm sorry, an error occurred: {error.message}",
            success=False,
            error=error.message,
            error_code=error.error_code,
            metadata={
                "error_details": error.to_dict(),
                "component": self.component_name
            },
            conversation=conversation or []
        )
    
    def create_error_tool_output(self, error: HedwigError) -> ToolOutput:
        """
        Create a ToolOutput representing an error condition.
        
        Args:
            error: The error that occurred
            
        Returns:
            ToolOutput with error information
        """
        return ToolOutput(
            text_summary=f"Tool execution failed: {error.message}",
            success=False,
            error=error.message,
            error_code=error.error_code,
            metadata={
                "error_details": error.to_dict(),
                "component": self.component_name
            }
        )
    
    def log_and_raise(self, error: HedwigError, context: str = "") -> None:
        """
        Log an error and raise it.
        
        Args:
            error: The error to log and raise
            context: Additional context for logging
        """
        log_message = f"{context}: {error.message}" if context else error.message
        self.logger.error(log_message, exc_info=error.cause is not None)
        raise error


def handle_errors(component_name: str):
    """
    Decorator for automatic error handling in methods.
    
    Args:
        component_name: Name of the component for error context
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(component_name)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise handler.handle_exception(e, func.__name__)
        return wrapper
    return decorator