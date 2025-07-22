"""
Software Engineering Agent (SWEAgent) for the Hedwig system.

The SWEAgent specializes in software development tasks including code generation,
debugging, refactoring, documentation, and project setup. It leverages code-specific
tools and has deep understanding of software development best practices.
"""

from typing import Dict, List, Any
from hedwig.agents.base import BaseAgent
from hedwig.core.models import TaskInput, TaskOutput
from hedwig.core.logging_config import get_logger


class SWEAgent(BaseAgent):
    """
    Software Engineering Agent specializing in code-related tasks.
    
    The SWEAgent is designed to handle a wide range of software development
    activities with expertise in multiple programming languages and frameworks.
    """
    
    def __init__(self, **kwargs):
        """Initialize the SWE Agent."""
        super().__init__(name="SWEAgent", **kwargs)
        self.logger = get_logger("hedwig.agents.swe")
        
        # Preferred tools for software development tasks
        self.preferred_tools = [
            "code_generator",
            "file_reader", 
            "python_execute",
            "bash",
            "list_artifacts"
        ]
    
    @property
    def description(self) -> Dict[str, Any]:
        """
        Structured description for the DispatcherAgent.
        
        Returns:
            Dictionary with agent metadata for intelligent routing
        """
        return {
            "agent_name": "SWEAgent",
            "purpose": "Designs, writes, modifies, and debugs source code in multiple programming languages.",
            "capabilities": [
                "code_generation",
                "code_review", 
                "debugging",
                "refactoring",
                "documentation",
                "script_execution",
                "file_operations",
                "project_setup",
                "testing",
                "software_architecture"
            ],
            "example_tasks": [
                "Write a Python script to parse CSV and output JSON",
                "Debug this JavaScript function that's not working properly", 
                "Refactor this code to be more modular and maintainable",
                "Create a simple REST API using Flask",
                "Write unit tests for this Python class",
                "Set up a basic React project structure",
                "Generate documentation for this codebase",
                "Optimize this algorithm for better performance"
            ],
            "languages": [
                "python", "javascript", "typescript", "java", "cpp", "c",
                "go", "rust", "html", "css", "sql", "bash", "powershell"
            ]
        }
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for the SWE Agent.
        
        Returns:
            System prompt tailored for software development tasks
        """
        return """You are SWEAgent, a specialist software engineering assistant with deep expertise in code development, debugging, and software architecture.

Your primary role is to help with all aspects of software development:

## Core Capabilities:
- **Code Generation**: Write clean, efficient, well-documented code in multiple languages
- **Code Review**: Analyze existing code for bugs, improvements, and best practices
- **Debugging**: Identify and fix issues in broken code
- - **Refactoring**: Improve code structure, readability, and maintainability
- **Testing**: Create comprehensive unit tests and integration tests
- **Documentation**: Generate clear technical documentation and code comments
- **Architecture**: Design software systems and recommend best practices
- **Project Setup**: Initialize new projects with proper structure and tooling

## Available Tools:
- **code_generator**: Create new source code files with syntax validation
- **file_reader**: Read existing code files for analysis and modification
- **python_execute**: Run Python code to test functionality and debug issues
- **bash**: Execute shell commands for project setup, build processes, and system operations
- **list_artifacts**: View previously generated code files and documents

## Programming Languages:
You are proficient in: Python, JavaScript, TypeScript, Java, C++, C, Go, Rust, HTML, CSS, SQL, Bash, and more.

## Best Practices:
- Always write clean, readable, and well-commented code
- Follow language-specific conventions and style guidelines
- Include error handling and input validation
- Generate comprehensive tests when creating new functionality
- Provide clear explanations of your code and design decisions
- Use version control best practices when relevant
- Consider security implications in your code

## Task Approach:
1. **Understand Requirements**: Carefully analyze the task and ask clarifying questions if needed
2. **Plan Solution**: Break down complex tasks into manageable steps
3. **Implement**: Write or modify code using appropriate tools
4. **Test**: Validate functionality using execution tools when possible
5. **Document**: Provide clear explanations and documentation
6. **Optimize**: Suggest improvements for performance and maintainability

When working with existing code, always read the files first to understand the current implementation before making changes. Test your solutions whenever possible to ensure they work correctly."""
    
    def _create_task_specific_prompt(self, task_input: TaskInput) -> str:
        """
        Create a task-specific prompt for the SWE Agent.
        
        Args:
            task_input: The input task to process
            
        Returns:
            Task-specific prompt with context
        """
        base_prompt = f"""
## Current Task:
{task_input.user_message}

## Context:
You are working on a software development task. Use your available tools to:
1. Analyze any existing code or requirements
2. Generate or modify code as needed
3. Test your implementations when possible
4. Provide clear documentation and explanations

## Instructions:
- Break down the task into logical steps
- Use appropriate tools for each step
- Prioritize code quality and best practices
- Test your solutions when feasible
- Explain your approach and any design decisions
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
## Recent Conversation:
{chr(10).join(context_lines)}
"""
        
        return base_prompt
    
    def _get_preferred_tools(self, task_input: TaskInput) -> List[str]:
        """
        Get preferred tools based on the task content.
        
        Args:
            task_input: The input task
            
        Returns:
            List of preferred tool names for this task
        """
        task_lower = task_input.user_message.lower()
        tools = self.preferred_tools.copy()
        
        # Add markdown generator for documentation tasks
        if any(keyword in task_lower for keyword in ["document", "readme", "guide", "docs"]):
            tools.insert(1, "markdown_generator")
        
        # Add PDF generator for reports
        if any(keyword in task_lower for keyword in ["report", "analysis", "summary"]):
            tools.insert(1, "pdf_generator")
        
        # Prioritize execution tools for testing/debugging tasks
        if any(keyword in task_lower for keyword in ["test", "debug", "run", "execute", "check"]):
            tools = ["python_execute", "bash"] + [t for t in tools if t not in ["python_execute", "bash"]]
        
        # Prioritize file operations for existing code tasks
        if any(keyword in task_lower for keyword in ["existing", "current", "modify", "update", "fix"]):
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
        
        # Strong indicators for software development tasks
        strong_indicators = [
            # Code-related keywords
            "code", "program", "script", "function", "class", "method",
            "python", "javascript", "java", "cpp", "rust", "go",
            
            # Development activities
            "write", "create", "generate", "implement", "build",
            "debug", "fix", "refactor", "optimize", "test",
            
            # Software concepts
            "algorithm", "api", "database", "frontend", "backend",
            "framework", "library", "package", "module",
            
            # File types
            ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs",
            ".html", ".css", ".sql", ".sh", ".json", ".xml", ".yaml"
        ]
        
        # Check for strong indicators
        for indicator in strong_indicators:
            if indicator in task_lower:
                return True
        
        # Additional context-based checks
        development_phrases = [
            "software development", "programming task", "coding problem",
            "development project", "build an application", "create a program",
            "write some code", "programming help", "software engineering"
        ]
        
        for phrase in development_phrases:
            if phrase in task_lower:
                return True
        
        return False
    
    def _analyze_task_complexity(self, task_input: TaskInput) -> Dict[str, Any]:
        """
        Analyze the complexity and requirements of a software development task.
        
        Args:
            task_input: The task to analyze
            
        Returns:
            Dictionary with complexity analysis
        """
        task_lower = task_input.user_message.lower()
        
        # Complexity indicators
        complexity_score = 0
        requirements = []
        
        # Simple tasks (complexity +1)
        simple_indicators = ["simple", "basic", "quick", "small", "hello world"]
        for indicator in simple_indicators:
            if indicator in task_lower:
                complexity_score += 1
                break
        
        # Medium tasks (complexity +2)
        medium_indicators = ["api", "database", "class", "module", "package"]
        for indicator in medium_indicators:
            if indicator in task_lower:
                complexity_score += 2
                break
        
        # Complex tasks (complexity +3)
        complex_indicators = ["system", "architecture", "framework", "full application", "microservice"]
        for indicator in complex_indicators:
            if indicator in task_lower:
                complexity_score += 3
                break
        
        # Determine estimated complexity
        if complexity_score <= 1:
            complexity_level = "simple"
        elif complexity_score <= 3:
            complexity_level = "medium"
        else:
            complexity_level = "complex"
        
        # Extract specific requirements
        if "test" in task_lower:
            requirements.append("testing")
        if "document" in task_lower:
            requirements.append("documentation")
        if "ui" in task_lower or "interface" in task_lower:
            requirements.append("user_interface")
        if "api" in task_lower:
            requirements.append("api_development")
        if "database" in task_lower or "db" in task_lower:
            requirements.append("database_integration")
        
        return {
            "complexity_level": complexity_level,
            "complexity_score": complexity_score,
            "requirements": requirements,
            "estimated_steps": min(10, max(3, complexity_score * 2))
        }
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        """
        Execute a software development task.
        
        Args:
            task_input: The software development task to execute
            
        Returns:
            TaskOutput with the results of the software development work
        """
        try:
            self.logger.info(f"SWEAgent executing task: {task_input.user_message[:100]}...")
            
            # Analyze task complexity and requirements
            task_analysis = self._analyze_task_complexity(task_input)
            self.logger.info(f"Task analysis: {task_analysis}")
            
            # Create system and task-specific prompts
            system_prompt = self._create_system_prompt()
            task_prompt = self._create_task_specific_prompt(task_input)
            
            # Get preferred tools for this task
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
                content=result.get("output", "Task completed"),
                success=True,
                result=result,
                metadata={
                    "agent_type": self.name,
                    "task_analysis": task_analysis,
                    "tools_used": result.get("tools_used", []),
                    "preferred_tools": preferred_tools
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error in SWEAgent execution: {str(e)}")
            return TaskOutput(
                content=f"I encountered an error while working on your software development task: {str(e)}",
                success=False,
                result=None,
                metadata={
                    "agent_type": self.name,
                    "error": str(e)
                }
            )