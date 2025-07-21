"""
Dispatcher Agent for intelligent task routing in the Hedwig system.

The DispatcherAgent is the central nervous system that analyzes user prompts
and conversation history to determine the most appropriate specialist agent
for handling each task.
"""

import json
from typing import Dict, Any, List, Optional, Callable

from hedwig.core.models import TaskInput, ConversationMessage
from hedwig.core.logging_config import get_logger
from hedwig.core.exceptions import AgentExecutionError
from hedwig.agents.base import BaseAgent


class DispatcherAgent:
    """
    Central task routing agent that selects appropriate specialists.
    
    The DispatcherAgent analyzes user prompts and conversation history
    to intelligently route tasks to the most suitable specialist agent.
    It does not execute tasks itself but acts as an intelligent router.
    
    Key responsibilities:
    - Analyze user prompts for task classification
    - Consider conversation history for context
    - Select the best specialist agent from available options
    - Handle agent rejection and re-routing scenarios
    - Maintain routing decisions for analysis and improvement
    """
    
    def __init__(self, llm_callback: Optional[Callable[[str], str]] = None):
        """
        Initialize the DispatcherAgent.
        
        Args:
            llm_callback: Function to call LLM for routing decisions
        """
        self.llm_callback = llm_callback
        self.logger = get_logger("hedwig.agents.dispatcher")
        
        # Registry of available specialist agents
        self.specialist_agents: Dict[str, BaseAgent] = {}
        
        # Track routing decisions for analysis
        self.routing_history: List[Dict[str, Any]] = []
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register a specialist agent with the dispatcher.
        
        Args:
            agent: BaseAgent instance to register
        """
        agent_name = agent.description["agent_name"]
        self.specialist_agents[agent_name] = agent
        self.logger.info(f"Registered specialist agent: {agent_name}")
    
    def unregister_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Unregister a specialist agent.
        
        Args:
            agent_name: Name of agent to unregister
            
        Returns:
            Removed agent instance, or None if not found
        """
        removed = self.specialist_agents.pop(agent_name, None)
        if removed:
            self.logger.info(f"Unregistered specialist agent: {agent_name}")
        return removed
    
    def route_task(
        self, 
        prompt: str, 
        conversation: Optional[List[ConversationMessage]] = None,
        excluded_agents: Optional[List[str]] = None
    ) -> str:
        """
        Route a task to the most appropriate specialist agent.
        
        Args:
            prompt: User task prompt to analyze
            conversation: Optional conversation history for context
            excluded_agents: List of agent names to exclude (for re-routing)
            
        Returns:
            Name of the selected specialist agent
            
        Raises:
            AgentExecutionError: If no suitable agent can be found
        """
        try:
            self.logger.info(f"Routing task: {prompt[:100]}...")
            
            if not self.specialist_agents:
                raise AgentExecutionError(
                    "No specialist agents registered with dispatcher",
                    "DispatcherAgent"
                )
            
            # Filter out excluded agents
            available_agents = {
                name: agent for name, agent in self.specialist_agents.items()
                if not excluded_agents or name not in excluded_agents
            }
            
            if not available_agents:
                raise AgentExecutionError(
                    f"No available agents after excluding: {excluded_agents}",
                    "DispatcherAgent"
                )
            
            # Build routing context
            routing_context = self._build_routing_context(
                available_agents, conversation, excluded_agents
            )
            
            # Get routing decision
            selected_agent = self._make_routing_decision(prompt, routing_context)
            
            # Validate selection
            if selected_agent not in available_agents:
                self.logger.warning(f"Selected agent '{selected_agent}' not in available agents")
                # Fall back to first available agent
                selected_agent = next(iter(available_agents.keys()))
            
            # Record routing decision
            self._record_routing_decision(prompt, selected_agent, excluded_agents)
            
            self.logger.info(f"Selected agent: {selected_agent}")
            return selected_agent
            
        except Exception as e:
            self.logger.error(f"Task routing failed: {str(e)}")
            raise AgentExecutionError(
                f"Failed to route task: {str(e)}",
                "DispatcherAgent",
                cause=e
            )
    
    def _build_routing_context(
        self,
        available_agents: Dict[str, BaseAgent],
        conversation: Optional[List[ConversationMessage]] = None,
        excluded_agents: Optional[List[str]] = None
    ) -> str:
        """
        Build context for routing decision.
        
        Args:
            available_agents: Dictionary of available agents
            conversation: Optional conversation history
            excluded_agents: List of excluded agent names
            
        Returns:
            Formatted context string for LLM
        """
        lines = ["Available Specialist Agents:"]
        lines.append("=" * 50)
        
        for agent_name, agent in available_agents.items():
            desc = agent.description
            lines.append(f"\n**{agent_name}**")
            lines.append(f"Purpose: {desc.get('purpose', 'No description')}")
            
            capabilities = desc.get('capabilities', [])
            if capabilities:
                lines.append(f"Capabilities: {', '.join(capabilities)}")
            
            examples = desc.get('example_tasks', [])
            if examples:
                lines.append("Example tasks:")
                for i, example in enumerate(examples, 1):
                    lines.append(f"  {i}. {example}")
        
        # Add conversation context if available
        if conversation:
            lines.append("\n" + "=" * 50)
            lines.append("Recent Conversation Context:")
            for msg in conversation[-3:]:  # Last 3 messages for context
                role = msg.role.upper()
                content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                lines.append(f"{role}: {content}")
        
        # Add exclusion context if any
        if excluded_agents:
            lines.append("\n" + "=" * 50)
            lines.append(f"Note: The following agents have already been tried and failed:")
            for agent_name in excluded_agents:
                lines.append(f"- {agent_name}")
            lines.append("Please choose a different agent.")
        
        return "\n".join(lines)
    
    def _make_routing_decision(self, prompt: str, context: str) -> str:
        """
        Make the actual routing decision using LLM or fallback logic.
        
        Args:
            prompt: User task prompt
            context: Routing context with agent descriptions
            
        Returns:
            Name of selected agent
        """
        if not self.llm_callback:
            # Fallback: simple heuristic routing
            return self._heuristic_routing(prompt)
        
        # Build LLM prompt for routing decision
        routing_prompt = f"""You are a task dispatcher that routes user requests to the most appropriate specialist agent.

{context}

User Request: "{prompt}"

IMPORTANT: Respond with ONLY the agent name that is best suited for this task. Choose from the available agents listed above.

Selected Agent:"""
        
        try:
            llm_response = self.llm_callback(routing_prompt)
            
            # Extract agent name from response
            selected_agent = llm_response.strip()
            
            # Clean up response (remove any extra text)
            lines = selected_agent.split('\n')
            selected_agent = lines[0].strip()
            
            # Remove common prefixes/suffixes
            prefixes = ["Selected Agent:", "Agent:", "I choose:", "The best agent is:"]
            for prefix in prefixes:
                if selected_agent.startswith(prefix):
                    selected_agent = selected_agent[len(prefix):].strip()
            
            return selected_agent
            
        except Exception as e:
            self.logger.warning(f"LLM routing failed, using heuristic: {e}")
            return self._heuristic_routing(prompt)
    
    def _heuristic_routing(self, prompt: str) -> str:
        """
        Simple heuristic-based routing when LLM is not available.
        
        Args:
            prompt: User task prompt
            
        Returns:
            Name of selected agent based on simple heuristics
        """
        prompt_lower = prompt.lower()
        
        # Simple keyword-based routing
        if any(word in prompt_lower for word in ['code', 'script', 'program', 'function', 'class', 'bug', 'debug']):
            if 'SWEAgent' in self.specialist_agents:
                return 'SWEAgent'
        
        if any(word in prompt_lower for word in ['research', 'search', 'find', 'investigate', 'analyze', 'study']):
            if 'ResearchAgent' in self.specialist_agents:
                return 'ResearchAgent'
        
        # Default to GeneralAgent if available, otherwise first agent
        if 'GeneralAgent' in self.specialist_agents:
            return 'GeneralAgent'
        
        return next(iter(self.specialist_agents.keys()))
    
    def _record_routing_decision(
        self,
        prompt: str,
        selected_agent: str,
        excluded_agents: Optional[List[str]] = None
    ) -> None:
        """
        Record routing decision for analysis and improvement.
        
        Args:
            prompt: The original user prompt
            selected_agent: Name of selected agent
            excluded_agents: List of excluded agents (if any)
        """
        decision_record = {
            "prompt": prompt[:200],  # Truncate for storage
            "selected_agent": selected_agent,
            "available_agents": list(self.specialist_agents.keys()),
            "excluded_agents": excluded_agents or [],
            "routing_attempt": len(excluded_agents) + 1 if excluded_agents else 1,
            "timestamp": None  # Could add timestamp if needed
        }
        
        self.routing_history.append(decision_record)
        
        # Keep only last 100 decisions to prevent memory growth
        if len(self.routing_history) > 100:
            self.routing_history.pop(0)
    
    def get_agent_by_name(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get a registered agent by name.
        
        Args:
            agent_name: Name of the agent to retrieve
            
        Returns:
            BaseAgent instance, or None if not found
        """
        return self.specialist_agents.get(agent_name)
    
    def list_available_agents(self) -> List[str]:
        """
        Get list of all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self.specialist_agents.keys())
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about routing decisions.
        
        Returns:
            Dictionary with routing statistics
        """
        if not self.routing_history:
            return {
                "total_routings": 0,
                "agents_used": {},
                "retry_rate": 0,
                "available_agents": list(self.specialist_agents.keys())
            }
        
        from collections import Counter
        
        agent_usage = Counter(record["selected_agent"] for record in self.routing_history)
        retry_count = sum(1 for record in self.routing_history if record["routing_attempt"] > 1)
        
        return {
            "total_routings": len(self.routing_history),
            "agents_used": dict(agent_usage),
            "retry_rate": retry_count / len(self.routing_history) if self.routing_history else 0,
            "available_agents": list(self.specialist_agents.keys()),
            "average_routing_attempt": sum(r["routing_attempt"] for r in self.routing_history) / len(self.routing_history)
        }
    
    def clear_history(self) -> None:
        """Clear routing decision history."""
        self.routing_history.clear()
        self.logger.info("Routing history cleared")
    
    def __len__(self) -> int:
        """Return number of registered agents."""
        return len(self.specialist_agents)
    
    def __contains__(self, agent_name: str) -> bool:
        """Check if an agent is registered."""
        return agent_name in self.specialist_agents
    
    def __str__(self) -> str:
        """String representation of the dispatcher."""
        return f"DispatcherAgent({len(self.specialist_agents)} agents registered)"