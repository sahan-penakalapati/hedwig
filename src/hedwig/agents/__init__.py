"""Agent implementations for the Hedwig system."""

from hedwig.agents.base import BaseAgent
from hedwig.agents.executor import AgentExecutor
from hedwig.agents.dispatcher import DispatcherAgent
from hedwig.agents.general import GeneralAgent

__all__ = [
    # Core agent infrastructure
    "BaseAgent",
    "AgentExecutor", 
    "DispatcherAgent",
    
    # Specialist agents
    "GeneralAgent",
]