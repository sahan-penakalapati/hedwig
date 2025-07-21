"""
Tool Registry for centralized tool management in the Hedwig system.

The ToolRegistry serves as a service locator, allowing agents to discover
and utilize tools without being tightly coupled to their implementations.
"""

from typing import Dict, List, Optional

from hedwig.core.logging_config import get_logger
from hedwig.core.exceptions import ToolExecutionError
from hedwig.tools.base import Tool


class ToolRegistry:
    """
    Central registry for managing tool lifecycle and accessibility.
    
    The ToolRegistry provides a single, consistent source for all available
    tools, enabling decoupling between agents and tool implementations.
    """
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: Dict[str, Tool] = {}
        self.logger = get_logger("hedwig.tools.registry")
    
    def register(self, tool: Tool) -> None:
        """
        Add a tool instance to the registry.
        
        Makes the tool available system-wide for agent use.
        Typically called during application startup.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ToolExecutionError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ToolExecutionError(
                f"Tool '{tool.name}' is already registered",
                "ToolRegistry"
            )
        
        self._tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name} ({tool.__class__.__name__})")
    
    def get(self, tool_name: str) -> Tool:
        """
        Retrieve a tool instance by name.
        
        Args:
            tool_name: Unique name of the tool (e.g., "file_reader")
            
        Returns:
            Tool instance
            
        Raises:
            ToolExecutionError: If the tool is not found
        """
        if tool_name not in self._tools:
            available_tools = ", ".join(self._tools.keys())
            raise ToolExecutionError(
                f"Tool '{tool_name}' not found. Available tools: {available_tools}",
                "ToolRegistry"
            )
        
        return self._tools[tool_name]
    
    def list_tools(self) -> List[Tool]:
        """
        Get a list of all registered tool objects.
        
        Returns:
            List of all Tool instances in the registry
        """
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """
        Get a list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool_descriptions(self) -> str:
        """
        Generate a formatted string describing all registered tools.
        
        This is essential for providing context to LLM agents about
        available capabilities and their parameters.
        
        Returns:
            Multi-line string describing all tools
        """
        if not self._tools:
            return "No tools registered."
        
        lines = ["Available Tools:"]
        lines.append("=" * 50)
        
        for tool in self._tools.values():
            lines.append(f"\n{tool.name} ({tool.__class__.__name__})")
            lines.append(f"Risk Level: {tool.risk_tier.value}")
            lines.append(f"Description: {tool.description}")
            lines.append(tool.get_schema_description())
        
        return "\n".join(lines)
    
    def get_tools_by_risk_tier(self, risk_tier) -> List[Tool]:
        """
        Get all tools with a specific risk tier.
        
        Args:
            risk_tier: RiskTier enum value
            
        Returns:
            List of tools with the specified risk tier
        """
        return [tool for tool in self._tools.values() if tool.risk_tier == risk_tier]
    
    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if the tool is registered, False otherwise
        """
        return tool_name in self._tools
    
    def unregister(self, tool_name: str) -> Optional[Tool]:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: Name of the tool to remove
            
        Returns:
            The removed tool instance, or None if not found
        """
        removed_tool = self._tools.pop(tool_name, None)
        if removed_tool:
            self.logger.info(f"Unregistered tool: {tool_name}")
        else:
            self.logger.warning(f"Attempted to unregister non-existent tool: {tool_name}")
        
        return removed_tool
    
    def clear(self) -> None:
        """Remove all tools from the registry."""
        tool_count = len(self._tools)
        self._tools.clear()
        self.logger.info(f"Cleared registry, removed {tool_count} tools")
    
    def get_registry_stats(self) -> Dict[str, any]:
        """
        Get statistics about the current registry state.
        
        Returns:
            Dictionary with registry statistics
        """
        from collections import Counter
        
        risk_counts = Counter(tool.risk_tier for tool in self._tools.values())
        
        return {
            "total_tools": len(self._tools),
            "tool_names": list(self._tools.keys()),
            "risk_tier_counts": dict(risk_counts),
            "tools_by_class": {
                tool.name: tool.__class__.__name__ 
                for tool in self._tools.values()
            }
        }
    
    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool name is in the registry."""
        return tool_name in self._tools
    
    def __iter__(self):
        """Iterate over tool names."""
        return iter(self._tools.keys())
    
    def __str__(self) -> str:
        """String representation of the registry."""
        return f"ToolRegistry({len(self._tools)} tools registered)"
    
    def __repr__(self) -> str:
        """Developer representation of the registry."""
        tools_list = ", ".join(self._tools.keys())
        return f"ToolRegistry(tools=[{tools_list}])"


# Global registry instance
# This provides a convenient singleton for the application
_global_registry = None


def get_global_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Creates the registry if it doesn't exist yet.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: Tool) -> None:
    """
    Register a tool in the global registry.
    
    Convenience function for registering tools in the global registry.
    
    Args:
        tool: Tool instance to register
    """
    get_global_registry().register(tool)


def get_tool(tool_name: str) -> Tool:
    """
    Get a tool from the global registry.
    
    Convenience function for retrieving tools from the global registry.
    
    Args:
        tool_name: Name of the tool to retrieve
        
    Returns:
        Tool instance
    """
    return get_global_registry().get(tool_name)