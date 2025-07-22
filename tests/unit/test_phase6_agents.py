"""
Tests for Phase 6 specialized agents: SWEAgent and ResearchAgent.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from hedwig.core.models import TaskInput, TaskOutput, ConversationMessage
from hedwig.agents.swe import SWEAgent
from hedwig.agents.research import ResearchAgent
from hedwig.agents.executor import AgentExecutor


class TestSWEAgent:
    """Test cases for the SWEAgent."""
    
    def test_swe_agent_initialization(self):
        """Test SWEAgent initialization."""
        agent = SWEAgent()
        
        assert agent.name == "SWEAgent"
        assert "code_generator" in agent.preferred_tools
        assert "python_execute" in agent.preferred_tools
        assert "bash" in agent.preferred_tools
    
    def test_swe_agent_description(self):
        """Test SWEAgent structured description."""
        agent = SWEAgent()
        description = agent.description
        
        assert description["agent_name"] == "SWEAgent"
        assert "software development" in description["purpose"].lower()
        assert "code_generation" in description["capabilities"]
        assert "debugging" in description["capabilities"]
        assert "refactoring" in description["capabilities"]
        assert len(description["example_tasks"]) >= 3
        assert "python" in description["languages"]
        assert "javascript" in description["languages"]
    
    def test_can_handle_task_code_keywords(self):
        """Test SWEAgent can identify code-related tasks."""
        agent = SWEAgent()
        
        # Code-related tasks
        code_tasks = [
            "Write a Python script to parse CSV files",
            "Debug this JavaScript function",
            "Create a REST API using Flask",
            "Refactor this code to be more modular",
            "Generate unit tests for this class",
            "Fix the bug in this.py file"
        ]
        
        for task in code_tasks:
            task_input = TaskInput(user_message=task)
            assert agent.can_handle_task(task_input), f"Should handle: {task}"
    
    def test_can_handle_task_file_extensions(self):
        """Test SWEAgent recognizes file extensions."""
        agent = SWEAgent()
        
        file_extension_tasks = [
            "Analyze this script.py for errors",
            "Update the config.js file",
            "Review this component.tsx code",
            "Optimize the query.sql statement"
        ]
        
        for task in file_extension_tasks:
            task_input = TaskInput(user_message=task)
            assert agent.can_handle_task(task_input), f"Should handle: {task}"
    
    def test_cannot_handle_non_code_tasks(self):
        """Test SWEAgent rejects non-code tasks."""
        agent = SWEAgent()
        
        non_code_tasks = [
            "What's the weather today?",
            "Write a business plan",
            "Find information about climate change",
            "Schedule a meeting"
        ]
        
        for task in non_code_tasks:
            task_input = TaskInput(user_message=task)
            assert not agent.can_handle_task(task_input), f"Should not handle: {task}"
    
    def test_analyze_task_complexity(self):
        """Test task complexity analysis."""
        agent = SWEAgent()
        
        # Simple task
        simple_task = TaskInput(user_message="Write a simple hello world script")
        simple_analysis = agent._analyze_task_complexity(simple_task)
        assert simple_analysis["complexity_level"] == "simple"
        
        # Complex task
        complex_task = TaskInput(user_message="Build a microservice architecture with database integration")
        complex_analysis = agent._analyze_task_complexity(complex_task)
        assert complex_analysis["complexity_level"] == "complex"
        
        # Medium task
        medium_task = TaskInput(user_message="Create a REST API with user authentication")
        medium_analysis = agent._analyze_task_complexity(medium_task)
        assert medium_analysis["complexity_level"] in ["medium", "complex"]
    
    def test_get_preferred_tools_by_task_type(self):
        """Test tool selection based on task type."""
        agent = SWEAgent()
        
        # Documentation task
        doc_task = TaskInput(user_message="Generate documentation for this API")
        doc_tools = agent._get_preferred_tools(doc_task)
        assert "markdown_generator" in doc_tools
        
        # Testing task
        test_task = TaskInput(user_message="Run tests and debug any failures")
        test_tools = agent._get_preferred_tools(test_task)
        assert test_tools[0] in ["python_execute", "bash"]
        
        # Existing code task
        existing_task = TaskInput(user_message="Fix the existing authentication module")
        existing_tools = agent._get_preferred_tools(existing_task)
        assert existing_tools[0] in ["file_reader", "list_artifacts"]
    
    @patch.object(SWEAgent, 'agent_executor')
    def test_run_success(self, mock_executor):
        """Test successful SWEAgent execution."""
        # Mock the agent executor
        mock_executor.invoke.return_value = {
            "output": "Successfully created Python script",
            "tools_used": ["code_generator", "python_execute"]
        }
        
        agent = SWEAgent()
        agent.agent_executor = mock_executor
        
        task_input = TaskInput(user_message="Write a Python script to calculate fibonacci numbers")
        result = agent._run(task_input)
        
        assert result.success is True
        assert "Successfully created Python script" in result.content
        assert result.metadata["agent_type"] == "SWEAgent"
        assert "task_analysis" in result.metadata
    
    @patch.object(SWEAgent, 'agent_executor')
    def test_run_failure(self, mock_executor):
        """Test SWEAgent execution failure handling."""
        # Mock executor failure
        mock_executor.invoke.side_effect = Exception("Mock execution error")
        
        agent = SWEAgent()
        agent.agent_executor = mock_executor
        
        task_input = TaskInput(user_message="Write some code")
        result = agent._run(task_input)
        
        assert result.success is False
        assert "Mock execution error" in result.content
        assert result.metadata["agent_type"] == "SWEAgent"


class TestResearchAgent:
    """Test cases for the ResearchAgent."""
    
    def test_research_agent_initialization(self):
        """Test ResearchAgent initialization."""
        agent = ResearchAgent()
        
        assert agent.name == "ResearchAgent"
        assert "firecrawl_research" in agent.preferred_tools
        assert "browser" in agent.preferred_tools
        assert "markdown_generator" in agent.preferred_tools
    
    def test_research_agent_description(self):
        """Test ResearchAgent structured description."""
        agent = ResearchAgent()
        description = agent.description
        
        assert description["agent_name"] == "ResearchAgent"
        assert "research" in description["purpose"].lower()
        assert "web_research" in description["capabilities"]
        assert "information_gathering" in description["capabilities"]
        assert "content_summarization" in description["capabilities"]
        assert len(description["example_tasks"]) >= 3
        assert "output_formats" in description
    
    def test_can_handle_task_research_keywords(self):
        """Test ResearchAgent can identify research tasks."""
        agent = ResearchAgent()
        
        research_tasks = [
            "Research the latest AI developments",
            "Find information about renewable energy trends",
            "Analyze competitor pricing strategies",
            "What are the best practices for remote work?",
            "Investigate market trends in blockchain technology",
            "Study the impact of climate change on agriculture"
        ]
        
        for task in research_tasks:
            task_input = TaskInput(user_message=task)
            assert agent.can_handle_task(task_input), f"Should handle: {task}"
    
    def test_can_handle_task_question_patterns(self):
        """Test ResearchAgent recognizes question patterns."""
        agent = ResearchAgent()
        
        question_tasks = [
            "What is the current state of quantum computing?",
            "How does machine learning work in healthcare?",
            "Tell me about recent developments in space exploration",
            "Can you find information about electric vehicle adoption?"
        ]
        
        for task in question_tasks:
            task_input = TaskInput(user_message=task)
            assert agent.can_handle_task(task_input), f"Should handle: {task}"
    
    def test_cannot_handle_non_research_tasks(self):
        """Test ResearchAgent rejects non-research tasks."""
        agent = ResearchAgent()
        
        non_research_tasks = [
            "Write a Python function to sort arrays",
            "Create a login form in HTML",
            "Debug this JavaScript code",
            "Generate a PDF with this data"
        ]
        
        for task in non_research_tasks:
            task_input = TaskInput(user_message=task)
            assert not agent.can_handle_task(task_input), f"Should not handle: {task}"
    
    def test_determine_research_type(self):
        """Test research type determination."""
        agent = ResearchAgent()
        
        # Market research
        market_task = TaskInput(user_message="Research competitor pricing in the cloud computing market")
        market_analysis = agent._determine_research_type(market_task)
        assert "market_research" in market_analysis["research_types"]
        
        # Trend analysis
        trend_task = TaskInput(user_message="Analyze trends in artificial intelligence development")
        trend_analysis = agent._determine_research_type(trend_task)
        assert "trend_analysis" in trend_analysis["research_types"]
        
        # Comparative analysis
        compare_task = TaskInput(user_message="Compare different web frameworks for Python")
        compare_analysis = agent._determine_research_type(compare_task)
        assert "comparative_analysis" in compare_analysis["research_types"]
        
        # Academic research
        academic_task = TaskInput(user_message="Find academic papers on machine learning in healthcare")
        academic_analysis = agent._determine_research_type(academic_task)
        assert "academic_research" in academic_analysis["research_types"]
    
    def test_determine_output_format(self):
        """Test output format determination."""
        agent = ResearchAgent()
        
        # Summary format
        summary_task = TaskInput(user_message="Give me a brief summary of AI trends")
        summary_analysis = agent._determine_research_type(summary_task)
        assert summary_analysis["output_format"] == "summary"
        
        # Detailed report
        report_task = TaskInput(user_message="Create a detailed report on renewable energy")
        report_analysis = agent._determine_research_type(report_task)
        assert report_analysis["output_format"] == "detailed_report"
        
        # Comparative table
        table_task = TaskInput(user_message="Compare the features of different programming languages in a table")
        table_analysis = agent._determine_research_type(table_task)
        assert table_analysis["output_format"] == "comparative_table"
    
    def test_get_preferred_tools_by_output_format(self):
        """Test tool selection based on output format."""
        agent = ResearchAgent()
        
        # Formal report task
        report_task = TaskInput(user_message="Create a professional analysis report on market trends")
        report_tools = agent._get_preferred_tools(report_task)
        assert report_tools[0] == "pdf_generator"
        
        # Summary task
        summary_task = TaskInput(user_message="Give me a quick overview of recent developments")
        summary_tools = agent._get_preferred_tools(summary_task)
        assert summary_tools[0] == "markdown_generator"
        
        # Existing research task
        existing_task = TaskInput(user_message="Review and analyze the current research documents")
        existing_tools = agent._get_preferred_tools(existing_task)
        assert existing_tools[0] in ["file_reader", "list_artifacts"]
    
    @patch.object(ResearchAgent, 'agent_executor')
    def test_run_success(self, mock_executor):
        """Test successful ResearchAgent execution."""
        # Mock the agent executor
        mock_executor.invoke.return_value = {
            "output": "Completed comprehensive research on AI trends",
            "tools_used": ["firecrawl_research", "markdown_generator"]
        }
        
        agent = ResearchAgent()
        agent.agent_executor = mock_executor
        
        task_input = TaskInput(user_message="Research the latest developments in artificial intelligence")
        result = agent._run(task_input)
        
        assert result.success is True
        assert "Completed comprehensive research" in result.content
        assert result.metadata["agent_type"] == "ResearchAgent"
        assert "research_analysis" in result.metadata
    
    @patch.object(ResearchAgent, 'agent_executor')
    def test_run_failure(self, mock_executor):
        """Test ResearchAgent execution failure handling."""
        # Mock executor failure
        mock_executor.invoke.side_effect = Exception("Mock research error")
        
        agent = ResearchAgent()
        agent.agent_executor = mock_executor
        
        task_input = TaskInput(user_message="Research something")
        result = agent._run(task_input)
        
        assert result.success is False
        assert "Mock research error" in result.content
        assert result.metadata["agent_type"] == "ResearchAgent"


class TestAgentIntegration:
    """Integration tests for specialized agents."""
    
    def test_agent_registration(self):
        """Test that specialized agents can be registered properly."""
        from hedwig.agents import create_specialist_agents
        
        # Mock agent executor
        mock_executor = Mock(spec=AgentExecutor)
        
        # Create specialist agents
        agents = create_specialist_agents(agent_executor=mock_executor)
        
        assert len(agents) == 3  # GeneralAgent, SWEAgent, ResearchAgent
        
        # Check that all agents have required properties
        for agent in agents:
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'description')
            assert hasattr(agent, 'can_handle_task')
            assert callable(agent.can_handle_task)
    
    def test_agent_descriptions_format(self):
        """Test that all agents have properly formatted descriptions."""
        from hedwig.agents.swe import SWEAgent
        from hedwig.agents.research import ResearchAgent
        from hedwig.agents.general import GeneralAgent
        
        agents = [SWEAgent(), ResearchAgent(), GeneralAgent()]
        
        for agent in agents:
            desc = agent.description
            
            # Check required fields
            assert "agent_name" in desc
            assert "purpose" in desc
            assert "capabilities" in desc
            assert "example_tasks" in desc
            
            # Check data types
            assert isinstance(desc["agent_name"], str)
            assert isinstance(desc["purpose"], str)
            assert isinstance(desc["capabilities"], list)
            assert isinstance(desc["example_tasks"], list)
            
            # Check content
            assert len(desc["capabilities"]) > 0
            assert len(desc["example_tasks"]) >= 3
    
    def test_task_routing_simulation(self):
        """Test simulated task routing between agents."""
        swe_agent = SWEAgent()
        research_agent = ResearchAgent()
        
        # Test tasks and expected routing
        test_cases = [
            ("Write a Python script to analyze data", swe_agent, True),
            ("Research market trends in AI", research_agent, True),
            ("Debug this JavaScript function", swe_agent, True),
            ("Find information about climate change", research_agent, True),
            ("Create a REST API endpoint", swe_agent, True),
            ("Analyze competitor pricing strategies", research_agent, True)
        ]
        
        for task_text, expected_agent, should_handle in test_cases:
            task_input = TaskInput(user_message=task_text)
            
            if expected_agent == swe_agent:
                assert swe_agent.can_handle_task(task_input) == should_handle
                assert research_agent.can_handle_task(task_input) != should_handle
            else:
                assert research_agent.can_handle_task(task_input) == should_handle
                assert swe_agent.can_handle_task(task_input) != should_handle