"""Agent implementations for the Hedwig system."""

from hedwig.agents.base import BaseAgent
from hedwig.agents.executor import AgentExecutor
from hedwig.agents.dispatcher import DispatcherAgent
from hedwig.agents.general import GeneralAgent
from hedwig.agents.swe import SWEAgent
from hedwig.agents.research import ResearchAgent

__all__ = [
    # Core agent infrastructure
    "BaseAgent",
    "AgentExecutor", 
    "DispatcherAgent",
    
    # Specialist agents
    "GeneralAgent",
    "SWEAgent",
    "ResearchAgent",
]


def create_specialist_agents(**kwargs) -> list[BaseAgent]:
    """
    Create instances of all specialist agents.
    
    Args:
        **kwargs: Arguments to pass to agent constructors
        
    Returns:
        List of specialist agent instances
    """
    return [
        GeneralAgent(**kwargs),
        SWEAgent(**kwargs),
        ResearchAgent(**kwargs)
    ]