"""
Research Agent for the Hedwig system.

The ResearchAgent specializes in information gathering, web research, data analysis,
and content summarization. It leverages web research tools and has expertise in
finding, analyzing, and synthesizing information from various sources.
"""

from typing import Dict, List, Any
from hedwig.agents.base import BaseAgent
from hedwig.core.models import TaskInput, TaskOutput
from hedwig.core.logging_config import get_logger


class ResearchAgent(BaseAgent):
    """
    Research Agent specializing in information gathering and analysis.
    
    The ResearchAgent is designed to handle research tasks including web searches,
    content analysis, data gathering, and report generation.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Research Agent."""
        super().__init__(name="ResearchAgent", **kwargs)
        self.logger = get_logger("hedwig.agents.research")
        
        # Preferred tools for research tasks
        self.preferred_tools = [
            "firecrawl_research",  # Primary web research tool
            "browser",             # Web automation for complex interactions
            "file_reader",
            "markdown_generator",
            "pdf_generator", 
            "list_artifacts",
            "bash"  # For data processing commands
        ]
    
    @property
    def description(self) -> Dict[str, Any]:
        """
        Structured description for the DispatcherAgent.
        
        Returns:
            Dictionary with agent metadata for intelligent routing
        """
        return {
            "agent_name": "ResearchAgent",
            "purpose": "Conducts comprehensive research, gathers information, and creates detailed reports and summaries.",
            "capabilities": [
                "web_research",
                "information_gathering", 
                "data_analysis",
                "content_summarization",
                "fact_checking",
                "trend_analysis",
                "competitive_analysis",
                "market_research",
                "academic_research",
                "report_generation",
                "data_synthesis",
                "source_verification"
            ],
            "example_tasks": [
                "Research the latest developments in artificial intelligence and create a summary report",
                "Find information about market trends in renewable energy for 2024",
                "Analyze competitor pricing for cloud computing services",
                "Research best practices for remote team management",
                "Gather information about Python web frameworks and compare their features",
                "Create a report on cybersecurity threats facing small businesses",
                "Research the history and evolution of blockchain technology",
                "Find and summarize academic papers on machine learning in healthcare"
            ],
            "output_formats": [
                "structured_reports", "executive_summaries", "data_tables",
                "comparative_analyses", "trend_reports", "fact_sheets"
            ]
        }
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for the Research Agent.
        
        Returns:
            System prompt tailored for research tasks
        """
        return """You are ResearchAgent, a specialist research assistant with expertise in information gathering, analysis, and synthesis.

Your primary role is to conduct comprehensive research and provide well-structured, accurate information:

## Core Capabilities:
- **Information Gathering**: Find relevant, current, and accurate information from various sources
- **Data Analysis**: Analyze data patterns, trends, and relationships
- **Content Summarization**: Create concise, comprehensive summaries of complex topics
- **Report Generation**: Produce well-structured reports with clear findings and insights
- **Fact Checking**: Verify information accuracy and credibility
- **Comparative Analysis**: Compare different options, products, services, or approaches
- **Trend Analysis**: Identify and analyze patterns and trends over time
- **Source Verification**: Assess the reliability and credibility of information sources

## Available Tools:
- **file_reader**: Read existing research materials, documents, and data files
- **markdown_generator**: Create structured research reports and documentation
- **pdf_generator**: Generate formal reports with tables and professional formatting
- **bash**: Execute commands for data processing and file operations
- **list_artifacts**: View previously generated research materials
- **firecrawl_research**: Web research and content extraction
- **browser**: Automated web browsing and data collection

## Research Methodology:
1. **Define Scope**: Clearly understand the research question and objectives
2. **Source Identification**: Identify reliable and relevant information sources
3. **Data Collection**: Gather information systematically and comprehensively
4. **Analysis**: Analyze collected data for patterns, insights, and conclusions
5. **Synthesis**: Combine findings into coherent, actionable insights
6. **Verification**: Cross-check facts and validate information accuracy
7. **Documentation**: Present findings in clear, well-structured formats

## Quality Standards:
- Always prioritize accuracy and factual correctness
- Use multiple sources to verify important information
- Clearly distinguish between facts, opinions, and speculation
- Provide source attribution when possible
- Present information in an objective, unbiased manner
- Structure reports for clarity and easy consumption
- Include relevant data, statistics, and examples
- Highlight key findings and actionable insights

## Output Formats:
- **Executive Summaries**: Concise overviews for decision-makers
- **Detailed Reports**: Comprehensive analysis with supporting data
- **Comparative Tables**: Side-by-side comparisons of options
- **Trend Analysis**: Time-based analysis with charts and data
- **Fact Sheets**: Quick reference documents with key information
- **Research Briefs**: Focused summaries on specific topics

When conducting research, always start by clearly defining the research question and scope. Use systematic approaches to gather information, and present findings in formats that best serve the user's needs."""
    
    def _create_task_specific_prompt(self, task_input: TaskInput) -> str:
        """
        Create a task-specific prompt for the Research Agent.
        
        Args:
            task_input: The input task to process
            
        Returns:
            Task-specific prompt with context
        """
        base_prompt = f"""
## Research Task:
{task_input.user_message}

## Research Instructions:
You are conducting research on the above topic. Follow these steps:

1. **Define Research Scope**: Clearly identify what information is needed
2. **Gather Information**: Use available tools to collect relevant data
3. **Analyze Findings**: Look for patterns, trends, and key insights
4. **Structure Results**: Organize information in a clear, useful format
5. **Generate Report**: Create appropriate documentation for the findings

## Approach:
- Be thorough but focused on the specific research question
- Use multiple perspectives and sources when possible
- Highlight key findings and actionable insights
- Present information in the most useful format for the user
- Include relevant data, examples, and supporting details
"""
        
        # Add conversation history context if available
        if task_input.conversation:
            recent_messages = task_input.conversation[-3:]  # Last 3 messages for context
            context_lines = []
            for msg in recent_messages:
                role = "User" if msg.role == "user" else "Assistant"
                content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                context_lines.append(f"{role}: {content_preview}")
            
            if context_lines:
                base_prompt += f"""
## Previous Context:
{chr(10).join(context_lines)}
"""
        
        return base_prompt
    
    def _determine_research_type(self, task_input: TaskInput) -> Dict[str, Any]:
        """
        Determine the type of research needed based on the task.
        
        Args:
            task_input: The input task
            
        Returns:
            Dictionary with research type analysis
        """
        task_lower = task_input.user_message.lower()
        
        research_types = []
        output_format = "report"
        complexity = "medium"
        
        # Determine research types
        if any(keyword in task_lower for keyword in ["market", "industry", "business", "competitor"]):
            research_types.append("market_research")
        
        if any(keyword in task_lower for keyword in ["trend", "pattern", "change", "evolution"]):
            research_types.append("trend_analysis")
        
        if any(keyword in task_lower for keyword in ["compare", "versus", "vs", "difference"]):
            research_types.append("comparative_analysis")
        
        if any(keyword in task_lower for keyword in ["academic", "study", "paper", "scientific"]):
            research_types.append("academic_research")
        
        if any(keyword in task_lower for keyword in ["technology", "tech", "software", "innovation"]):
            research_types.append("technology_research")
        
        if any(keyword in task_lower for keyword in ["news", "current", "recent", "latest"]):
            research_types.append("current_events")
        
        # Determine output format
        if any(keyword in task_lower for keyword in ["summary", "brief", "overview"]):
            output_format = "summary"
        elif any(keyword in task_lower for keyword in ["report", "analysis", "detailed"]):
            output_format = "detailed_report"
        elif any(keyword in task_lower for keyword in ["table", "comparison", "compare"]):
            output_format = "comparative_table"
        elif any(keyword in task_lower for keyword in ["fact sheet", "quick reference"]):
            output_format = "fact_sheet"
        
        # Determine complexity
        if any(keyword in task_lower for keyword in ["simple", "basic", "quick", "brief"]):
            complexity = "simple"
        elif any(keyword in task_lower for keyword in ["comprehensive", "detailed", "thorough", "in-depth"]):
            complexity = "complex"
        
        # Default to general research if no specific type identified
        if not research_types:
            research_types = ["general_research"]
        
        return {
            "research_types": research_types,
            "output_format": output_format,
            "complexity": complexity,
            "estimated_sources": 3 if complexity == "simple" else 5 if complexity == "medium" else 8
        }
    
    def _get_preferred_tools(self, task_input: TaskInput) -> List[str]:
        """
        Get preferred tools based on the research task.
        
        Args:
            task_input: The input task
            
        Returns:
            List of preferred tool names for this task
        """
        task_lower = task_input.user_message.lower()
        tools = self.preferred_tools.copy()
        
        # Prioritize PDF generation for formal reports
        if any(keyword in task_lower for keyword in ["report", "formal", "professional", "analysis"]):
            tools = ["pdf_generator"] + [t for t in tools if t != "pdf_generator"]
        
        # Prioritize markdown for summaries and quick reports
        elif any(keyword in task_lower for keyword in ["summary", "brief", "quick", "overview"]):
            tools = ["markdown_generator"] + [t for t in tools if t != "markdown_generator"]
        
        # Add file reading for research on existing materials
        if any(keyword in task_lower for keyword in ["existing", "current", "review", "analyze"]):
            tools = ["file_reader", "list_artifacts"] + [t for t in tools if t not in ["file_reader", "list_artifacts"]]
        
        return tools
    
    def can_handle_task(self, task_input: TaskInput) -> bool:
        """
        Determine if this agent can handle the given task.
        
        Args:
            task_input: Task to evaluate
            
        Returns:
            True if this agent should handle the task
        """
        task_lower = task_input.user_message.lower()
        
        # Strong indicators for research tasks
        research_indicators = [
            # Research keywords
            "research", "find", "gather", "collect", "investigate",
            "study", "analyze", "examine", "explore", "discover",
            
            # Information seeking
            "information", "data", "facts", "details", "statistics",
            "trends", "patterns", "insights", "findings",
            
            # Question words
            "what", "how", "why", "when", "where", "which",
            
            # Report/summary generation
            "report", "summary", "analysis", "overview", "brief",
            "document", "findings", "conclusions",
            
            # Comparison tasks
            "compare", "versus", "vs", "difference", "similar",
            "best", "top", "ranking", "options",
            
            # Market/business research
            "market", "industry", "business", "competitor",
            "pricing", "strategy", "trends"
        ]
        
        # Check for research indicators
        for indicator in research_indicators:
            if indicator in task_lower:
                return True
        
        # Question patterns
        question_patterns = [
            "tell me about", "what is", "how does", "why do",
            "can you find", "look up", "search for",
            "latest on", "current state of", "recent developments"
        ]
        
        for pattern in question_patterns:
            if pattern in task_lower:
                return True
        
        # Academic/professional contexts
        if any(term in task_lower for term in ["academic", "scientific", "study", "paper", "journal"]):
            return True
        
        return False
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute a research task.
        
        Args:
            task_input: The research task to execute
            
        Returns:
            TaskOutput with the research results
        """
        try:
            self.logger.info(f"ResearchAgent executing task: {task_input.user_message[:100]}...")
            
            # Analyze research requirements
            research_analysis = self._determine_research_type(task_input)
            self.logger.info(f"Research analysis: {research_analysis}")
            
            # Create system and task-specific prompts
            system_prompt = self._create_system_prompt()
            task_prompt = self._create_task_specific_prompt(task_input)
            
            # Get preferred tools for this research task
            preferred_tools = self._get_preferred_tools(task_input)
            
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n{task_prompt}"
            
            # Execute using the agent executor
            result = self.agent_executor.invoke({
                "input": full_prompt,
                "conversation": self._format_conversation_history(task_input.conversation),
                "preferred_tools": preferred_tools
            })
            
            # Process and return results
            return TaskOutput(
                content=result.get("output", "Research completed"),
                success=True,
                result=result,
                metadata={
                    "agent_type": self.name,
                    "research_analysis": research_analysis,
                    "tools_used": result.get("tools_used", []),
                    "preferred_tools": preferred_tools
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error in ResearchAgent execution: {str(e)}")
            return TaskOutput(
                content=f"I encountered an error while conducting your research: {str(e)}",
                success=False,
                result=None,
                metadata={
                    "agent_type": self.name,
                    "error": str(e)
                }
            )