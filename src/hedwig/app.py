"""
HedwigApp: Main application class for the Hedwig multi-agent system.

The HedwigApp is the central orchestrator that manages the overall user experience
and application state. It coordinates between the GUI, agent system, and artifact
management to provide a seamless multi-agent task execution platform.

Key Responsibilities:
- Thread Management: Create, persist, and load chat threads
- Context Provisioning: Load thread context for agent execution
- Command Handling: Pre-filter simple commands and route complex tasks
- Task Re-routing: Handle agent rejections with retry logic
- Artifact Processing: Register artifacts and handle auto-opening
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from hedwig.core.artifact_registry import ArtifactRegistry
from hedwig.core.config import HedwigConfig, ConfigManager
from hedwig.core.logging_config import get_logger
from hedwig.core.llm_integration import get_llm_callback, validate_llm_connection
from hedwig.core.models import (
    TaskInput, TaskOutput, ChatThread, ConversationMessage, 
    Artifact, ArtifactType, ErrorCode
)
from hedwig.agents.dispatcher import DispatcherAgent
from hedwig.agents.general import GeneralAgent
from hedwig.agents.swe import SWEAgent
from hedwig.agents.research import ResearchAgent
from hedwig.agents.executor import AgentExecutor
from hedwig.tools.registry import ToolRegistry
from hedwig.tools.security import SecurityGateway
from hedwig.tools.file_reader import FileReaderTool
from hedwig.tools.list_artifacts import ListArtifactsTool
from hedwig.tools import register_all_tools


class HedwigApp:
    """
    Main application class for the Hedwig multi-agent system.
    
    The HedwigApp manages the overall user experience and application state,
    including thread management, agent orchestration, and artifact handling.
    
    Features:
    - Thread-scoped conversation and artifact management
    - Intelligent task routing with rejection handling
    - Auto-opening of generated artifacts
    - Command pre-filtering for performance
    - Persistent thread state across sessions
    """
    
    def __init__(self, config: Optional[HedwigConfig] = None):
        """
        Initialize the HedwigApp.
        
        Args:
            config: Optional configuration. If not provided, loads from ConfigManager.
        """
        # Configuration and logging
        self.config = config or ConfigManager.get_config()
        self.config.setup_directories()
        self.logger = get_logger("hedwig.app")
        
        # Application state
        self.current_thread: Optional[ChatThread] = None
        self.threads_dir = self.config.get_threads_dir()
        
        # Agent system components
        self.tool_registry = ToolRegistry()
        self.security_gateway = SecurityGateway()
        
        # Initialize LLM integration
        self.llm_callback = get_llm_callback()
        
        # Validate LLM connection
        if not validate_llm_connection():
            self.logger.warning("LLM connection validation failed - some features may not work correctly")
        else:
            self.logger.info("LLM connection validated successfully")
        
        self.agent_executor = AgentExecutor(
            tool_registry=self.tool_registry,
            security_gateway=self.security_gateway,
            llm_callback=self.llm_callback
        )
        
        # Initialize tools and agents
        self._initialize_tools()
        self._initialize_agents()
        
        # Application statistics
        self.session_stats = {
            "threads_created": 0,
            "threads_loaded": 0,
            "tasks_executed": 0,
            "rejections_handled": 0,
            "artifacts_generated": 0,
            "commands_pre_filtered": 0
        }
        
        self.logger.info("HedwigApp initialized successfully")
    
    def _initialize_tools(self) -> None:
        """Initialize and register all available tools."""
        # Register all tools using the centralized registration function
        register_all_tools()
        
        # Get the global registry that now contains all tools
        from hedwig.tools.registry import get_global_registry
        global_registry = get_global_registry()
        
        # Copy all tools from global registry to our local registry
        for tool in global_registry.list_tools():
            if not self.tool_registry.has_tool(tool.name):
                self.tool_registry.register(tool)
        
        # Set up artifact provider for ListArtifactsTool
        def get_current_artifacts():
            if self.current_thread:
                return self.current_thread.artifacts
            return []
        
        # Update ListArtifactsTool with artifact provider if it exists
        if self.tool_registry.has_tool("list_artifacts"):
            list_artifacts = self.tool_registry.get("list_artifacts")
            if hasattr(list_artifacts, 'set_artifact_provider'):
                list_artifacts.set_artifact_provider(get_current_artifacts)
            self.list_artifacts_tool = list_artifacts
        
        self.logger.info(f"Initialized {len(self.tool_registry.list_tools())} tools including Phase 5 tools")
    
    def _initialize_agents(self) -> None:
        """Initialize the agent system with dispatcher and specialists."""
        # Create specialist agents
        general_agent = GeneralAgent(agent_executor=self.agent_executor)
        swe_agent = SWEAgent(agent_executor=self.agent_executor)
        research_agent = ResearchAgent(agent_executor=self.agent_executor)
        
        specialist_agents = [general_agent, swe_agent, research_agent]
        
        # Create dispatcher agent
        self.dispatcher = DispatcherAgent(
            specialists=specialist_agents,
            default_agent=general_agent,
            llm_callback=self.llm_callback
        )
        
        self.logger.info(f"Initialized dispatcher with {len(specialist_agents)} specialist agents")
    
    def run(self, prompt: str, thread_id: Optional[UUID] = None) -> TaskOutput:
        """
        Main entry point for task execution.
        
        This is the primary interface used by the GUI and other clients
        to execute user tasks through the multi-agent system.
        
        Args:
            prompt: User's task prompt
            thread_id: Optional thread ID. If not provided, creates new thread.
            
        Returns:
            TaskOutput containing execution results and artifacts
        """
        try:
            self.logger.info(f"Processing user prompt: {prompt[:100]}...")
            
            # Load or create thread
            if thread_id:
                self._load_thread(thread_id)
            else:
                self._create_new_thread()
            
            # Check for pre-filterable commands
            if self._should_pre_filter(prompt):
                return self._handle_pre_filtered_command(prompt)
            
            # Execute through agent system with re-routing
            result = self._execute_with_retry(prompt)
            
            # Process results and artifacts
            self._process_execution_result(result)
            
            # Update statistics
            self.session_stats["tasks_executed"] += 1
            
            # Persist thread state
            self._persist_current_thread()
            
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error in HedwigApp.run: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return TaskOutput(
                content=f"I'm sorry, something went wrong: {str(e)}",
                success=False,
                error=error_msg,
                error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                conversation=self.current_thread.get_conversation_history() if self.current_thread else [],
                metadata={
                    "component": "HedwigApp",
                    "error_type": "unexpected_error"
                }
            )
    
    def _create_new_thread(self) -> ChatThread:
        """Create a new chat thread."""
        thread = ChatThread(
            thread_id=uuid4(),
            metadata={
                "created_by": "HedwigApp",
                "session_id": str(uuid4())
            }
        )
        
        # Create thread-specific artifact registry
        thread_artifacts_dir = self.threads_dir / str(thread.thread_id) / "artifacts"
        thread_artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Store artifact registry in thread metadata for now
        # TODO: Properly integrate ArtifactRegistry with ChatThread model
        
        self.current_thread = thread
        self.session_stats["threads_created"] += 1
        
        self.logger.info(f"Created new thread: {thread.thread_id}")
        return thread
    
    def _load_thread(self, thread_id: UUID) -> Optional[ChatThread]:
        """
        Load an existing thread from disk.
        
        Args:
            thread_id: ID of the thread to load
            
        Returns:
            Loaded ChatThread or None if not found
        """
        thread_dir = self.threads_dir / str(thread_id)
        thread_file = thread_dir / "thread.json"
        
        if not thread_file.exists():
            self.logger.warning(f"Thread {thread_id} not found, creating new thread")
            return self._create_new_thread()
        
        try:
            with open(thread_file, 'r', encoding='utf-8') as f:
                thread_data = json.load(f)
            
            # Reconstruct ChatThread from saved data
            thread = ChatThread(
                thread_id=UUID(thread_data["thread_id"]),
                created_at=datetime.fromisoformat(thread_data["created_at"]),
                updated_at=datetime.fromisoformat(thread_data["updated_at"]),
                metadata=thread_data.get("metadata", {})
            )
            
            # Reconstruct messages
            for msg_data in thread_data.get("messages", []):
                thread.add_message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    metadata=msg_data.get("metadata", {})
                )
            
            # Reconstruct artifacts
            for artifact_data in thread_data.get("artifacts", []):
                artifact = Artifact(
                    file_path=artifact_data["file_path"],
                    artifact_type=ArtifactType(artifact_data["artifact_type"]),
                    description=artifact_data["description"],
                    created_at=datetime.fromisoformat(artifact_data["created_at"]),
                    artifact_id=UUID(artifact_data["artifact_id"]),
                    metadata=artifact_data.get("metadata", {})
                )
                thread.add_artifact(artifact)
            
            self.current_thread = thread
            self.session_stats["threads_loaded"] += 1
            
            self.logger.info(f"Loaded thread: {thread_id}")
            return thread
            
        except Exception as e:
            self.logger.error(f"Failed to load thread {thread_id}: {str(e)}")
            return self._create_new_thread()
    
    def _persist_current_thread(self) -> None:
        """Persist the current thread state to disk."""
        if not self.current_thread:
            return
        
        thread_dir = self.threads_dir / str(self.current_thread.thread_id)
        thread_dir.mkdir(parents=True, exist_ok=True)
        thread_file = thread_dir / "thread.json"
        
        try:
            thread_data = {
                "thread_id": str(self.current_thread.thread_id),
                "created_at": self.current_thread.created_at.isoformat(),
                "updated_at": self.current_thread.updated_at.isoformat(),
                "metadata": self.current_thread.metadata,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "message_id": str(msg.message_id),
                        "metadata": msg.metadata
                    }
                    for msg in self.current_thread.messages
                ],
                "artifacts": [artifact.to_dict() for artifact in self.current_thread.artifacts]
            }
            
            with open(thread_file, 'w', encoding='utf-8') as f:
                json.dump(thread_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Persisted thread {self.current_thread.thread_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to persist thread: {str(e)}")
    
    def _should_pre_filter(self, prompt: str) -> bool:
        """
        Determine if a prompt can be handled by pre-filtering.
        
        Pre-filterable commands are simple meta-commands that can be
        handled directly without invoking the full agent system.
        
        Args:
            prompt: User prompt to analyze
            
        Returns:
            True if the prompt should be pre-filtered
        """
        prompt_lower = prompt.lower().strip()
        
        # Simple artifact management commands
        pre_filter_patterns = [
            # Artifact listing
            "list artifacts",
            "show artifacts", 
            "what artifacts",
            "list files",
            "show files",
            
            # Simple artifact opening (when specific)
            "open ",
            "show ",
            
            # Thread management
            "list threads",
            "switch thread",
            
            # System commands
            "help",
            "status",
            "stats"
        ]
        
        return any(pattern in prompt_lower for pattern in pre_filter_patterns)
    
    def _handle_pre_filtered_command(self, prompt: str) -> TaskOutput:
        """
        Handle pre-filterable commands directly.
        
        Args:
            prompt: User prompt
            
        Returns:
            TaskOutput with command result
        """
        self.session_stats["commands_pre_filtered"] += 1
        prompt_lower = prompt.lower().strip()
        
        try:
            # List artifacts
            if any(pattern in prompt_lower for pattern in ["list artifacts", "show artifacts", "what artifacts", "list files", "show files"]):
                return self._list_artifacts()
            
            # System status/stats
            elif prompt_lower in ["status", "stats"]:
                return self._show_status()
            
            # Help
            elif prompt_lower == "help":
                return self._show_help()
            
            # TODO: Add more pre-filtered commands
            # - Specific artifact opening
            # - Thread management
            
            else:
                # Fall back to agent system
                return self._execute_with_retry(prompt)
        
        except Exception as e:
            return TaskOutput(
                content=f"Error handling command: {str(e)}",
                success=False,
                error=str(e),
                conversation=self.current_thread.get_conversation_history() if self.current_thread else []
            )
    
    def _list_artifacts(self) -> TaskOutput:
        """List artifacts in the current thread."""
        if not self.current_thread or not self.current_thread.artifacts:
            content = "No artifacts found in the current thread."
        else:
            artifact_lines = ["Available artifacts:"]
            for i, artifact in enumerate(self.current_thread.artifacts, 1):
                artifact_lines.append(f"  {i}. {Path(artifact.file_path).name} ({artifact.artifact_type.value}) - {artifact.description}")
            content = "\n".join(artifact_lines)
        
        # Add to conversation
        if self.current_thread:
            self.current_thread.add_message("user", "list artifacts")
            self.current_thread.add_message("assistant", content)
        
        return TaskOutput(
            content=content,
            success=True,
            conversation=self.current_thread.get_conversation_history() if self.current_thread else [],
            metadata={"pre_filtered": True, "command_type": "list_artifacts"}
        )
    
    def _show_status(self) -> TaskOutput:
        """Show application status and statistics."""
        status_lines = [
            "=== Hedwig Application Status ===",
            f"Current Thread: {self.current_thread.thread_id if self.current_thread else 'None'}",
            f"Session Stats:",
            f"  - Threads Created: {self.session_stats['threads_created']}",
            f"  - Threads Loaded: {self.session_stats['threads_loaded']}",
            f"  - Tasks Executed: {self.session_stats['tasks_executed']}",
            f"  - Commands Pre-filtered: {self.session_stats['commands_pre_filtered']}",
            f"  - Artifacts Generated: {self.session_stats['artifacts_generated']}",
            f"  - Task Rejections Handled: {self.session_stats['rejections_handled']}",
            "",
            f"Available Tools: {len(self.tool_registry.list_tools())}",
            f"Data Directory: {self.config.get_data_dir()}",
        ]
        
        content = "\n".join(status_lines)
        
        # Add to conversation
        if self.current_thread:
            self.current_thread.add_message("user", "status")
            self.current_thread.add_message("assistant", content)
        
        return TaskOutput(
            content=content,
            success=True,
            conversation=self.current_thread.get_conversation_history() if self.current_thread else [],
            metadata={"pre_filtered": True, "command_type": "status"}
        )
    
    def _show_help(self) -> TaskOutput:
        """Show help information."""
        help_content = """
=== Hedwig Multi-Agent System ===

I'm Hedwig, your personal multi-agent assistant. I can help you with:

🔧 **Code & Development**
- Write code in multiple languages
- Execute Python scripts
- Run terminal commands
- Read and analyze files

📄 **Document Generation**
- Create PDF reports
- Generate Markdown documents
- Format and structure content

🔍 **Research & Analysis**
- Web research and summarization
- Data extraction and analysis
- Information gathering

📁 **File & Artifact Management**
- Create and manage files
- Track generated artifacts
- Auto-open relevant files

**Simple Commands:**
- `list artifacts` - Show all generated files
- `status` - Show system status
- `help` - Show this help message

**Examples:**
- "Write a Python script to calculate fibonacci numbers"
- "Create a PDF report about renewable energy"  
- "Research the latest AI developments and summarize"
- "List all artifacts generated in this conversation"

Just describe what you'd like me to do in natural language!
        """.strip()
        
        # Add to conversation
        if self.current_thread:
            self.current_thread.add_message("user", "help")
            self.current_thread.add_message("assistant", help_content)
        
        return TaskOutput(
            content=help_content,
            success=True,
            conversation=self.current_thread.get_conversation_history() if self.current_thread else [],
            metadata={"pre_filtered": True, "command_type": "help"}
        )
    
    def _execute_with_retry(self, prompt: str, max_retries: int = 3) -> TaskOutput:
        """
        Execute a task through the agent system with retry logic for rejections.
        
        Args:
            prompt: User prompt
            max_retries: Maximum number of retry attempts
            
        Returns:
            TaskOutput from successful execution or final failure
        """
        rejected_agents = []
        
        for attempt in range(max_retries):
            try:
                # Add user message to thread
                if self.current_thread:
                    self.current_thread.add_message("user", prompt)
                
                # Create task input with context
                task_input = TaskInput(
                    prompt=prompt,
                    conversation=self.current_thread.get_conversation_history() if self.current_thread else [],
                    thread_id=self.current_thread.thread_id if self.current_thread else None,
                    parameters={
                        "rejected_agents": rejected_agents,
                        "attempt": attempt + 1,
                        "max_retries": max_retries
                    }
                )
                
                # Route through dispatcher
                selected_agent = self.dispatcher.route_task(task_input)
                
                # Execute task
                result = selected_agent.run(task_input)
                
                # Check for rejection
                if not result.success and result.error_code == ErrorCode.TASK_REJECTED_AS_INAPPROPRIATE:
                    # Track rejection
                    rejected_agents.append(selected_agent.name)
                    self.session_stats["rejections_handled"] += 1
                    
                    self.logger.info(f"Task rejected by {selected_agent.name}, attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        # Update prompt context for retry
                        context_msg = f"Previous agent ({selected_agent.name}) rejected the task. Please choose a different, more suitable agent."
                        prompt = f"{prompt}\n\nContext: {context_msg}"
                        continue
                    else:
                        # Final failure after max retries
                        error_msg = f"Unable to complete task after {max_retries} attempts. Last rejection: {result.error}"
                        self.logger.warning(error_msg)
                        
                        final_result = TaskOutput(
                            content=f"I'm sorry, I was unable to complete the task. The specialist agent reported: {result.error}",
                            success=False,
                            error=error_msg,
                            error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                            conversation=result.conversation,
                            metadata={
                                "final_failure": True,
                                "attempts": max_retries,
                                "rejected_agents": rejected_agents,
                                "last_error": result.error
                            }
                        )
                        
                        # Add assistant response to thread
                        if self.current_thread:
                            self.current_thread.add_message("assistant", final_result.content)
                        
                        return final_result
                else:
                    # Successful execution or non-rejection error
                    # Add assistant response to thread
                    if self.current_thread and result.content:
                        self.current_thread.add_message("assistant", result.content)
                    
                    return result
                    
            except Exception as e:
                error_msg = f"Error in task execution attempt {attempt + 1}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                
                if attempt < max_retries - 1:
                    continue
                else:
                    # Final failure due to exception
                    final_result = TaskOutput(
                        content=f"I'm sorry, an unexpected error occurred: {str(e)}",
                        success=False,
                        error=error_msg,
                        error_code=ErrorCode.AGENT_EXECUTION_FAILED,
                        conversation=self.current_thread.get_conversation_history() if self.current_thread else [],
                        metadata={
                            "final_failure": True,
                            "attempts": max_retries,
                            "error_type": "exception"
                        }
                    )
                    
                    # Add assistant response to thread
                    if self.current_thread:
                        self.current_thread.add_message("assistant", final_result.content)
                    
                    return final_result
        
        # Should never reach here, but safety fallback
        return TaskOutput(
            content="Unexpected error in retry logic",
            success=False,
            error="Retry logic failure",
            error_code=ErrorCode.AGENT_EXECUTION_FAILED,
            conversation=self.current_thread.get_conversation_history() if self.current_thread else []
        )
    
    def _process_execution_result(self, result: TaskOutput) -> None:
        """
        Process the execution result, handling artifacts and auto-opening.
        
        Args:
            result: TaskOutput from agent execution
        """
        if not result.success or not result.artifacts:
            return
        
        # Register new artifacts with current thread
        new_artifacts = []
        if self.current_thread:
            for artifact in result.artifacts:
                self.current_thread.add_artifact(artifact)
                new_artifacts.append(artifact)
                self.session_stats["artifacts_generated"] += 1
        
        # Apply auto-opening rules to new artifacts
        self._apply_auto_opening_rules(new_artifacts)
        
        self.logger.info(f"Processed {len(new_artifacts)} new artifacts")
    
    def _apply_auto_opening_rules(self, artifacts: List[Artifact]) -> None:
        """
        Apply auto-opening rules to newly generated artifacts.
        
        Rules from PRD:
        - If exactly one PDF was generated, auto-open it
        - If one or more code files were generated, auto-open the first one
        - PDF rule takes precedence over code rule
        
        Args:
            artifacts: List of newly generated artifacts
        """
        if not artifacts:
            return
        
        # Check for exactly one PDF
        pdf_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.PDF]
        if len(pdf_artifacts) == 1:
            self._auto_open_artifact(pdf_artifacts[0], "PDF")
            return
        
        # Check for code files (if no single PDF)
        code_artifacts = [a for a in artifacts if a.artifact_type == ArtifactType.CODE]
        if code_artifacts:
            self._auto_open_artifact(code_artifacts[0], "code")
            return
        
        self.logger.debug(f"No auto-opening rules matched for {len(artifacts)} artifacts")
    
    def _auto_open_artifact(self, artifact: Artifact, reason: str) -> None:
        """
        Auto-open an artifact based on the rules.
        
        Args:
            artifact: Artifact to open
            reason: Reason for auto-opening (for logging)
        """
        try:
            # TODO: Implement actual auto-opening logic
            # This would integrate with the GUI to open files in internal viewers
            self.logger.info(f"Auto-opening {reason} artifact: {artifact.file_path}")
            
            # For now, just log that we would open it
            # In Phase 5 (GUI), this would call GUI methods to open viewers
            
        except Exception as e:
            self.logger.error(f"Failed to auto-open artifact {artifact.file_path}: {str(e)}")
    
    def get_current_thread(self) -> Optional[ChatThread]:
        """Get the current active chat thread."""
        return self.current_thread
    
    def list_threads(self) -> List[Dict[str, Any]]:
        """
        List all available threads.
        
        Returns:
            List of thread metadata dictionaries
        """
        threads = []
        
        if not self.threads_dir.exists():
            return threads
        
        for thread_dir in self.threads_dir.iterdir():
            if thread_dir.is_dir():
                thread_file = thread_dir / "thread.json"
                if thread_file.exists():
                    try:
                        with open(thread_file, 'r', encoding='utf-8') as f:
                            thread_data = json.load(f)
                        
                        threads.append({
                            "thread_id": thread_data["thread_id"],
                            "created_at": thread_data["created_at"],
                            "updated_at": thread_data["updated_at"],
                            "message_count": len(thread_data.get("messages", [])),
                            "artifact_count": len(thread_data.get("artifacts", [])),
                            "metadata": thread_data.get("metadata", {})
                        })
                    except Exception as e:
                        self.logger.warning(f"Failed to read thread metadata from {thread_file}: {str(e)}")
        
        # Sort by last update time
        threads.sort(key=lambda x: x["updated_at"], reverse=True)
        return threads
    
    def switch_thread(self, thread_id: UUID) -> bool:
        """
        Switch to a different thread.
        
        Args:
            thread_id: ID of thread to switch to
            
        Returns:
            True if switch was successful, False otherwise
        """
        try:
            # Persist current thread first
            if self.current_thread:
                self._persist_current_thread()
            
            # Load new thread
            thread = self._load_thread(thread_id)
            return thread is not None
            
        except Exception as e:
            self.logger.error(f"Failed to switch to thread {thread_id}: {str(e)}")
            return False
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return {
            **self.session_stats,
            "current_thread_id": str(self.current_thread.thread_id) if self.current_thread else None,
            "total_threads_available": len(self.list_threads()),
            "agent_statistics": self.dispatcher.get_routing_statistics() if hasattr(self.dispatcher, 'get_routing_statistics') else {}
        }
    
    def shutdown(self) -> None:
        """Clean shutdown of the application."""
        try:
            # Persist current thread
            if self.current_thread:
                self._persist_current_thread()
            
            # Log final statistics
            stats = self.get_session_statistics()
            self.logger.info(f"HedwigApp shutting down. Final stats: {stats}")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")