"""
Tests for the Hedwig agent system.

Tests cover BaseAgent, AgentExecutor, DispatcherAgent, and GeneralAgent
implementations with focus on integration and core functionality.
"""

import tempfile
from typing import Dict, Any
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from hedwig.core.models import TaskInput, TaskOutput, ConversationMessage
from hedwig.core.artifact_registry import ArtifactRegistry
from hedwig.tools.registry import ToolRegistry
from hedwig.tools.security import SecurityGateway
from hedwig.tools.file_reader import FileReaderTool
from hedwig.tools.list_artifacts import ListArtifactsTool
from hedwig.agents.base import BaseAgent
from hedwig.agents.executor import AgentExecutor
from hedwig.agents.dispatcher import DispatcherAgent
from hedwig.agents.general import GeneralAgent


class MockAgent(BaseAgent):
    """Mock agent for testing BaseAgent functionality."""
    
    @property
    def description(self) -> Dict[str, Any]:
        return {
            "agent_name": "MockAgent",
            "purpose": "A mock agent for testing purposes",
            "capabilities": ["testing", "mocking"],
            "example_tasks": ["Test something", "Mock something"]
        }
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        return TaskOutput(
            content=f"Mock response to: {task_input.prompt}",
            success=True,
            result="mock_result",
            conversation=task_input.conversation or []
        )


class FailingMockAgent(BaseAgent):
    """Mock agent that always fails for testing error handling."""
    
    @property
    def description(self) -> Dict[str, Any]:
        return {
            "agent_name": "FailingMockAgent", 
            "purpose": "A mock agent that always fails",
            "capabilities": ["failing"],
            "example_tasks": ["Fail at something"]
        }
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        raise Exception("Simulated agent failure")


class TestBaseAgent:
    """Test cases for the BaseAgent abstract class."""
    
    def test_agent_initialization(self):
        """Test agent initialization with default and custom names."""
        # Default name generation
        agent1 = MockAgent()
        assert agent1.name == "mock"
        
        # Custom name
        agent2 = MockAgent(name="custom_agent")
        assert agent2.name == "custom_agent"
    
    def test_agent_name_generation(self):
        """Test automatic agent name generation from class names."""
        agent = MockAgent()
        assert agent.name == "mock"  # MockAgent -> mock
        
        # Test with "Agent" suffix
        class TestCoderAgent(MockAgent):
            pass
        
        coder_agent = TestCoderAgent()
        assert coder_agent.name == "test_coder"
    
    def test_agent_description(self):
        """Test agent description property."""
        agent = MockAgent()
        desc = agent.description
        
        assert desc["agent_name"] == "MockAgent"
        assert desc["purpose"] == "A mock agent for testing purposes"
        assert "testing" in desc["capabilities"]
        assert len(desc["example_tasks"]) == 2
    
    def test_agent_execution_success(self):
        """Test successful agent execution."""
        agent = MockAgent()
        task_input = TaskInput(prompt="Test task")
        
        result = agent.run(task_input)
        
        assert result.success is True
        assert "Mock response to: Test task" in result.content
        assert result.result == "mock_result"
    
    def test_agent_execution_with_empty_prompt(self):
        """Test agent execution with empty prompt."""
        agent = MockAgent()
        task_input = TaskInput(prompt="")
        
        result = agent.run(task_input)
        
        assert result.success is False
        assert "No task prompt provided" in result.content
        assert result.error_code == "INVALID_INPUT"
    
    def test_agent_execution_with_runtime_error(self):
        """Test agent execution with runtime errors."""
        agent = FailingMockAgent()
        task_input = TaskInput(prompt="Test task")
        
        result = agent.run(task_input)
        
        assert result.success is False
        assert "encountered an error" in result.content
        assert result.error_code == "AGENT_EXECUTION_ERROR"
        assert "Simulated agent failure" in result.error
    
    def test_agent_can_handle_task(self):
        """Test task handling capability assessment."""
        agent = MockAgent()
        
        # Default implementation should always return True
        assert agent.can_handle_task("any task") is True
        assert agent.can_handle_task("another task", []) is True
    
    def test_agent_task_rejection(self):
        """Test agent task rejection."""
        agent = MockAgent()
        task_input = TaskInput(prompt="Rejected task")
        
        result = agent.reject_task("Not suitable for this agent", task_input)
        
        assert result.success is False
        assert result.error_code == "TASK_REJECTED_AS_INAPPROPRIATE"
        assert "cannot handle this task" in result.content
        assert result.metadata["can_retry"] is True
    
    def test_conversation_message_handling(self):
        """Test conversation message operations."""
        agent = MockAgent()
        
        # Start with empty conversation
        conversation = agent.add_conversation_message("Hello", "user")
        assert len(conversation) == 1
        assert conversation[0].role == "user"
        assert conversation[0].content == "Hello"
        
        # Add agent response
        conversation = agent.add_conversation_message("Hi there", "assistant", conversation)
        assert len(conversation) == 2
        assert conversation[1].role == "assistant"
        assert conversation[1].content == "Hi there"
    
    def test_conversation_formatting(self):
        """Test conversation formatting for LLM consumption."""
        agent = MockAgent()
        
        # Empty conversation
        formatted = agent.format_conversation_for_llm([])
        assert "No previous conversation" in formatted
        
        # With messages
        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi there")
        ]
        formatted = agent.format_conversation_for_llm(messages)
        
        assert "Previous conversation:" in formatted
        assert "USER: Hello" in formatted
        assert "ASSISTANT: Hi there" in formatted
    
    def test_agent_description_summary(self):
        """Test agent description summary generation."""
        agent = MockAgent()
        summary = agent.get_description_summary()
        
        assert "Agent: MockAgent" in summary
        assert "Purpose: A mock agent for testing purposes" in summary
        assert "Capabilities: testing, mocking" in summary
        assert "Example tasks:" in summary


class TestAgentExecutor:
    """Test cases for the AgentExecutor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create tool registry with basic tools
        self.tool_registry = ToolRegistry()
        
        # Create file reader tool
        self.file_reader = FileReaderTool()
        self.tool_registry.register(self.file_reader)
        
        # Create security gateway  
        self.security_gateway = SecurityGateway()
        
        # Create executor
        self.executor = AgentExecutor(
            tool_registry=self.tool_registry,
            security_gateway=self.security_gateway,
            llm_callback=None  # No LLM for basic tests
        )
    
    def test_executor_initialization(self):
        """Test executor initialization."""
        assert self.executor.tool_registry is not None
        assert self.executor.security_gateway is not None
        assert self.executor.max_iterations == 10
        assert self.executor.current_iteration == 0
        assert len(self.executor.collected_artifacts) == 0
    
    def test_executor_invoke_without_llm(self):
        """Test executor invocation without LLM callback."""
        task_input = {
            "input": "Test task",
            "conversation": "Previous conversation",
            "parameters": {}
        }
        
        result = self.executor.invoke(task_input)
        
        assert result["success"] is True
        assert "Mock response" in result["output"]
        assert result["iterations"] == 1
        assert isinstance(result["artifacts"], list)
    
    def test_executor_invoke_with_empty_input(self):
        """Test executor with empty input."""
        result = self.executor.invoke({})
        
        assert result["success"] is False
        assert "No input prompt provided" in result["output"]
    
    def test_executor_tools_context_building(self):
        """Test tools context building."""
        # All tools
        context = self.executor._build_tools_context()
        assert "Available Tools:" in context
        assert "file_reader" in context
        
        # Specific tools
        context = self.executor._build_tools_context(["file_reader"])
        assert "file_reader" in context
        
        # Non-existent tools
        context = self.executor._build_tools_context(["nonexistent"])
        assert "No tools available" in context
    
    def test_executor_system_prompt_building(self):
        """Test system prompt building."""
        tools_context = "Available tools: file_reader"
        conversation = "USER: Hello"
        
        prompt = self.executor._build_system_prompt(tools_context, conversation)
        
        assert "AI assistant with access to specialized tools" in prompt
        assert "TOOL_CALL:" in prompt
        assert "Available tools: file_reader" in prompt
        assert "USER: Hello" in prompt
    
    def test_executor_tool_call_extraction(self):
        """Test tool call extraction from LLM response."""
        # Valid tool call
        response_with_call = """
        I need to read a file.
        
        TOOL_CALL: {
          "tool_name": "file_reader",
          "arguments": {
            "file_path": "/tmp/test.txt"
          }
        }
        
        Let me read this file for you.
        """
        
        tool_call = self.executor._extract_tool_call(response_with_call)
        assert tool_call is not None
        assert tool_call["tool_name"] == "file_reader"
        assert tool_call["arguments"]["file_path"] == "/tmp/test.txt"
        
        # No tool call
        response_without_call = "This is just a regular response."
        tool_call = self.executor._extract_tool_call(response_without_call)
        assert tool_call is None
    
    def test_executor_tool_execution(self):
        """Test tool execution through security gateway."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            tool_call = {
                "tool_name": "file_reader",
                "arguments": {"file_path": temp_path}
            }
            
            result = self.executor._execute_tool_call(tool_call)
            
            assert result["success"] is True
            assert "Successfully read file" in result["text_summary"]
        finally:
            # Clean up
            import os
            os.unlink(temp_path)
    
    def test_executor_nonexistent_tool(self):
        """Test execution of non-existent tool."""
        tool_call = {
            "tool_name": "nonexistent_tool",
            "arguments": {}
        }
        
        result = self.executor._execute_tool_call(tool_call)
        
        assert result["success"] is False
        assert "not found in registry" in result["error"]
    
    def test_executor_get_summary(self):
        """Test execution summary."""
        summary = self.executor.get_execution_summary()
        
        assert summary["iterations"] == 0
        assert summary["max_iterations"] == 10
        assert summary["artifacts_collected"] == 0
        assert summary["tools_available"] == 1  # file_reader
        assert summary["security_gateway_active"] is True


class TestDispatcherAgent:
    """Test cases for the DispatcherAgent class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dispatcher = DispatcherAgent()
        
        # Register test agents
        self.general_agent = MockAgent(name="general_test")
        self.failing_agent = FailingMockAgent(name="failing_test")
        
        # Mock the descriptions to match expected format
        self.general_agent.description = {
            "agent_name": "GeneralAgent",
            "purpose": "Handles general tasks",
            "capabilities": ["general"],
            "example_tasks": ["General task"]
        }
        
        self.failing_agent.description = {
            "agent_name": "SpecialistAgent", 
            "purpose": "Handles specialist tasks",
            "capabilities": ["specialist"],
            "example_tasks": ["Specialist task"]
        }
        
        self.dispatcher.register_agent(self.general_agent)
        self.dispatcher.register_agent(self.failing_agent)
    
    def test_dispatcher_initialization(self):
        """Test dispatcher initialization."""
        dispatcher = DispatcherAgent()
        assert len(dispatcher) == 0
        assert dispatcher.llm_callback is None
    
    def test_agent_registration(self):
        """Test agent registration and unregistration."""
        dispatcher = DispatcherAgent()
        agent = MockAgent()
        agent.description = {"agent_name": "TestAgent", "purpose": "Test"}
        
        # Register
        dispatcher.register_agent(agent)
        assert len(dispatcher) == 1
        assert "TestAgent" in dispatcher
        
        # Unregister
        removed = dispatcher.unregister_agent("TestAgent")
        assert removed is agent
        assert len(dispatcher) == 0
        assert "TestAgent" not in dispatcher
    
    def test_dispatcher_routing_heuristic(self):
        """Test heuristic-based routing."""
        # Test general task routing
        selected = self.dispatcher.route_task("Help me with something general")
        assert selected in ["GeneralAgent", "SpecialistAgent"]
        
        # Test with conversation context
        conversation = [ConversationMessage(role="user", content="Previous message")]
        selected = self.dispatcher.route_task("Another task", conversation)
        assert selected in ["GeneralAgent", "SpecialistAgent"]
    
    def test_dispatcher_routing_with_exclusions(self):
        """Test routing with excluded agents."""
        selected = self.dispatcher.route_task(
            "Test task", 
            excluded_agents=["GeneralAgent"]
        )
        assert selected == "SpecialistAgent"
    
    def test_dispatcher_routing_no_agents(self):
        """Test routing when no agents are available."""
        dispatcher = DispatcherAgent()
        
        with pytest.raises(Exception):  # Should raise AgentExecutionError
            dispatcher.route_task("Test task")
    
    def test_dispatcher_routing_all_excluded(self):
        """Test routing when all agents are excluded."""
        with pytest.raises(Exception):  # Should raise AgentExecutionError
            self.dispatcher.route_task(
                "Test task",
                excluded_agents=["GeneralAgent", "SpecialistAgent"]
            )
    
    def test_dispatcher_get_agent(self):
        """Test getting agents by name."""
        agent = self.dispatcher.get_agent_by_name("GeneralAgent")
        assert agent is self.general_agent
        
        # Non-existent agent
        agent = self.dispatcher.get_agent_by_name("NonexistentAgent")
        assert agent is None
    
    def test_dispatcher_list_agents(self):
        """Test listing available agents."""
        agents = self.dispatcher.list_available_agents()
        assert "GeneralAgent" in agents
        assert "SpecialistAgent" in agents
        assert len(agents) == 2
    
    def test_dispatcher_routing_context(self):
        """Test routing context building."""
        available_agents = {
            "GeneralAgent": self.general_agent,
            "SpecialistAgent": self.failing_agent
        }
        
        context = self.dispatcher._build_routing_context(available_agents)
        
        assert "Available Specialist Agents:" in context
        assert "GeneralAgent" in context
        assert "SpecialistAgent" in context
        assert "Purpose:" in context
    
    def test_dispatcher_statistics(self):
        """Test routing statistics."""
        # Make some routing decisions
        self.dispatcher.route_task("Task 1")
        self.dispatcher.route_task("Task 2", excluded_agents=["GeneralAgent"])
        
        stats = self.dispatcher.get_routing_statistics()
        
        assert stats["total_routings"] == 2
        assert len(stats["agents_used"]) > 0
        assert stats["available_agents"] == ["GeneralAgent", "SpecialistAgent"]
    
    def test_dispatcher_clear_history(self):
        """Test clearing routing history."""
        self.dispatcher.route_task("Test task")
        assert len(self.dispatcher.routing_history) == 1
        
        self.dispatcher.clear_history()
        assert len(self.dispatcher.routing_history) == 0


class TestGeneralAgent:
    """Test cases for the GeneralAgent class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = GeneralAgent()
    
    def test_general_agent_initialization(self):
        """Test GeneralAgent initialization."""
        assert self.agent.name == "general"
        assert self.agent.tasks_completed == 0
        assert len(self.agent.tools_used) == 0
        assert self.agent.agent_executor is None
    
    def test_general_agent_description(self):
        """Test GeneralAgent description."""
        desc = self.agent.description
        
        assert desc["agent_name"] == "GeneralAgent"
        assert desc["purpose"] is not None
        assert "file_operations" in desc["capabilities"]
        assert len(desc["example_tasks"]) == 3
    
    def test_general_agent_without_executor(self):
        """Test GeneralAgent execution without AgentExecutor."""
        task_input = TaskInput(prompt="Test file operation")
        
        result = self.agent.run(task_input)
        
        assert result.success is False
        assert result.error_code == "CONFIGURATION_ERROR"
        assert "AgentExecutor" in result.content
    
    def test_general_agent_task_categorization(self):
        """Test task categorization logic."""
        # File operations
        assert self.agent._categorize_task("Read the file") == "file_operations"
        assert self.agent._categorize_task("Open document") == "file_operations"
        
        # Research tasks
        assert self.agent._categorize_task("Search for information") == "research"
        assert self.agent._categorize_task("Find details about") == "research"
        
        # Artifact tasks
        assert self.agent._categorize_task("List artifacts") == "artifacts"
        assert self.agent._categorize_task("Show generated files") == "artifacts"
        
        # General tasks
        assert self.agent._categorize_task("Help me with something") == "general"
    
    def test_general_agent_can_handle_task(self):
        """Test task handling capability."""
        # Should handle most general tasks
        assert self.agent.can_handle_task("Help me read a file") is True
        assert self.agent.can_handle_task("List my artifacts") is True
        
        # Should reject very specialized tasks
        assert self.agent.can_handle_task("Refactor entire codebase architecture") is False
        assert self.agent.can_handle_task("Perform systematic review analysis") is False
    
    def test_general_agent_conversation_formatting(self):
        """Test conversation formatting."""
        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi")
        ]
        
        formatted = self.agent._format_conversation(messages)
        assert "USER: Hello" in formatted
        assert "ASSISTANT: Hi" in formatted
    
    def test_general_agent_conversation_update(self):
        """Test conversation history updates."""
        initial_conversation = [
            ConversationMessage(role="user", content="Previous message")
        ]
        
        updated = self.agent._update_conversation(
            initial_conversation,
            "New user message", 
            "Agent response"
        )
        
        assert len(updated) == 3
        assert updated[-2].content == "New user message"
        assert updated[-1].content == "Agent response"
        assert updated[-1].role == "assistant"
    
    def test_general_agent_statistics(self):
        """Test agent statistics tracking."""
        stats = self.agent.get_agent_statistics()
        
        assert stats["agent_name"] == "GeneralAgent"
        assert stats["tasks_completed"] == 0
        assert stats["unique_tools_count"] == 0
        assert "task_categories" in stats
        assert stats["has_executor"] is False
    
    def test_general_agent_reset_statistics(self):
        """Test statistics reset."""
        # Simulate some usage
        self.agent.tasks_completed = 5
        self.agent.tools_used.add("file_reader")
        
        self.agent.reset_statistics()
        
        assert self.agent.tasks_completed == 0
        assert len(self.agent.tools_used) == 0
    
    def test_general_agent_executor_configuration(self):
        """Test AgentExecutor configuration."""
        mock_executor = Mock()
        
        self.agent.set_agent_executor(mock_executor)
        
        assert self.agent.agent_executor is mock_executor


def test_agent_integration():
    """Integration test for the complete agent system."""
    # Set up complete system
    tool_registry = ToolRegistry()
    security_gateway = SecurityGateway()
    
    # Register tools
    file_reader = FileReaderTool()
    tool_registry.register(file_reader)
    
    # Create executor
    executor = AgentExecutor(
        tool_registry=tool_registry,
        security_gateway=security_gateway
    )
    
    # Create and configure agent
    agent = GeneralAgent()
    agent.set_agent_executor(executor)
    
    # Create dispatcher
    dispatcher = DispatcherAgent()
    dispatcher.register_agent(agent)
    
    # Test routing
    selected = dispatcher.route_task("Help me read a file")
    assert selected == "GeneralAgent"
    
    # Get the agent and test execution
    selected_agent = dispatcher.get_agent_by_name(selected)
    assert selected_agent is not None
    
    # Test task execution (without LLM, will use fallback)
    task_input = TaskInput(prompt="Help me with file operations")
    result = selected_agent.run(task_input)
    
    # Should handle gracefully even without full LLM integration
    assert result is not None
    assert isinstance(result, TaskOutput)