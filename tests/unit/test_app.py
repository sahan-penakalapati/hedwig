"""
Tests for HedwigApp main application class.

Tests cover all major functionality including thread management,
task execution, pre-filtering, re-routing, and artifact processing.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

from hedwig.app import HedwigApp
from hedwig.core.config import HedwigConfig
from hedwig.core.models import (
    TaskInput, TaskOutput, ChatThread, ConversationMessage,
    Artifact, ArtifactType, ErrorCode
)
from hedwig.agents.general import GeneralAgent


class TestHedwigApp(unittest.TestCase):
    """Test suite for HedwigApp functionality."""
    
    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test config
        self.config = HedwigConfig(
            data_dir=self.temp_path / "hedwig_test",
            debug_mode=True
        )
        
        # Mock the tool registry to avoid dependency issues
        with patch('hedwig.app.ToolRegistry'), \
             patch('hedwig.app.AgentExecutor'), \
             patch('hedwig.agents.dispatcher.DispatcherAgent'):
            self.app = HedwigApp(config=self.config)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_app_initialization(self):
        """Test that HedwigApp initializes correctly."""
        self.assertIsNotNone(self.app.config)
        self.assertIsNotNone(self.app.dispatcher)
        self.assertIsNotNone(self.app.tool_registry)
        self.assertIsNone(self.app.current_thread)
        self.assertEqual(self.app.session_stats["threads_created"], 0)
        self.assertTrue(self.app.threads_dir.exists())
    
    def test_create_new_thread(self):
        """Test creating a new chat thread."""
        thread = self.app._create_new_thread()
        
        self.assertIsInstance(thread, ChatThread)
        self.assertEqual(self.app.current_thread, thread)
        self.assertEqual(self.app.session_stats["threads_created"], 1)
        self.assertEqual(len(thread.messages), 0)
        self.assertEqual(len(thread.artifacts), 0)
    
    def test_thread_persistence(self):
        """Test thread persistence to disk."""
        # Create and populate a thread
        thread = self.app._create_new_thread()
        thread.add_message("user", "Hello")
        thread.add_message("assistant", "Hi there!")
        
        test_artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test artifact"
        )
        thread.add_artifact(test_artifact)
        
        # Persist thread
        self.app._persist_current_thread()
        
        # Verify files were created
        thread_dir = self.app.threads_dir / str(thread.thread_id)
        thread_file = thread_dir / "thread.json"
        
        self.assertTrue(thread_file.exists())
        
        # Verify content
        with open(thread_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["thread_id"], str(thread.thread_id))
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(len(data["artifacts"]), 1)
        self.assertEqual(data["messages"][0]["content"], "Hello")
        self.assertEqual(data["artifacts"][0]["file_path"], "test.txt")
    
    def test_thread_loading(self):
        """Test loading an existing thread from disk."""
        # Create and persist a thread
        original_thread = self.app._create_new_thread()
        original_thread.add_message("user", "Test message")
        original_thread.add_message("assistant", "Test response")
        self.app._persist_current_thread()
        
        original_id = original_thread.thread_id
        
        # Clear current thread
        self.app.current_thread = None
        
        # Load the thread
        loaded_thread = self.app._load_thread(original_id)
        
        self.assertIsNotNone(loaded_thread)
        self.assertEqual(loaded_thread.thread_id, original_id)
        self.assertEqual(len(loaded_thread.messages), 2)
        self.assertEqual(loaded_thread.messages[0].content, "Test message")
        self.assertEqual(loaded_thread.messages[1].content, "Test response")
        self.assertEqual(self.app.session_stats["threads_loaded"], 1)
    
    def test_pre_filter_detection(self):
        """Test detection of pre-filterable commands."""
        test_cases = [
            ("list artifacts", True),
            ("show artifacts", True),
            ("what artifacts", True),
            ("status", True),
            ("help", True),
            ("open report.pdf", True),
            ("Write a Python script", False),
            ("Create a PDF document", False),
            ("Research the latest AI trends", False)
        ]
        
        for prompt, expected in test_cases:
            with self.subTest(prompt=prompt):
                result = self.app._should_pre_filter(prompt)
                self.assertEqual(result, expected, f"Failed for prompt: {prompt}")
    
    def test_list_artifacts_command(self):
        """Test the list artifacts pre-filtered command."""
        # Create thread with artifacts
        thread = self.app._create_new_thread()
        
        artifact1 = Artifact(
            file_path="test1.pdf",
            artifact_type=ArtifactType.PDF,
            description="Test PDF"
        )
        artifact2 = Artifact(
            file_path="test2.py",
            artifact_type=ArtifactType.CODE,
            description="Test Python code"
        )
        
        thread.add_artifact(artifact1)
        thread.add_artifact(artifact2)
        
        # Test list artifacts command
        result = self.app._list_artifacts()
        
        self.assertTrue(result.success)
        self.assertIn("Available artifacts:", result.content)
        self.assertIn("test1.pdf", result.content)
        self.assertIn("test2.py", result.content)
        self.assertIn("pdf", result.content)
        self.assertIn("code", result.content)
    
    def test_status_command(self):
        """Test the status pre-filtered command."""
        result = self.app._show_status()
        
        self.assertTrue(result.success)
        self.assertIn("Hedwig Application Status", result.content)
        self.assertIn("Session Stats", result.content)
        self.assertIn("Threads Created:", result.content)
        self.assertIn("Tasks Executed:", result.content)
    
    def test_help_command(self):
        """Test the help pre-filtered command."""
        result = self.app._show_help()
        
        self.assertTrue(result.success)
        self.assertIn("Hedwig Multi-Agent System", result.content)
        self.assertIn("Code & Development", result.content)
        self.assertIn("Document Generation", result.content)
        self.assertIn("Simple Commands", result.content)
    
    @patch('hedwig.app.HedwigApp._execute_with_retry')
    def test_run_with_pre_filter(self, mock_execute):
        """Test run method with pre-filterable command."""
        result = self.app.run("help")
        
        # Should not call execute_with_retry for pre-filtered commands
        mock_execute.assert_not_called()
        self.assertTrue(result.success)
        self.assertIn("Hedwig Multi-Agent System", result.content)
    
    @patch('hedwig.app.HedwigApp._execute_with_retry')
    def test_run_with_complex_task(self, mock_execute):
        """Test run method with complex task that requires agent execution."""
        mock_result = TaskOutput(
            content="Task completed successfully",
            success=True,
            conversation=[]
        )
        mock_execute.return_value = mock_result
        
        result = self.app.run("Write a Python script")
        
        # Should call execute_with_retry for complex tasks
        mock_execute.assert_called_once()
        self.assertEqual(result, mock_result)
    
    def test_task_rejection_and_retry(self):
        """Test task rejection handling and retry logic."""
        # Mock dispatcher and agents
        mock_agent1 = Mock()
        mock_agent1.name = "TestAgent1"
        mock_agent1.run.return_value = TaskOutput(
            content="Cannot handle this task",
            success=False,
            error="Task not suitable for this agent",
            error_code=ErrorCode.TASK_REJECTED_AS_INAPPROPRIATE,
            conversation=[]
        )
        
        mock_agent2 = Mock()
        mock_agent2.name = "TestAgent2"
        mock_agent2.run.return_value = TaskOutput(
            content="Task completed successfully",
            success=True,
            conversation=[]
        )
        
        # Mock dispatcher to return different agents on subsequent calls
        self.app.dispatcher.route_task.side_effect = [mock_agent1, mock_agent2]
        
        # Execute task
        result = self.app._execute_with_retry("Complex task")
        
        # Should succeed after retry
        self.assertTrue(result.success)
        self.assertEqual(result.content, "Task completed successfully")
        self.assertEqual(self.app.session_stats["rejections_handled"], 1)
        
        # Verify both agents were called
        self.assertEqual(self.app.dispatcher.route_task.call_count, 2)
        mock_agent1.run.assert_called_once()
        mock_agent2.run.assert_called_once()
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        # Mock agent that always rejects
        mock_agent = Mock()
        mock_agent.name = "RejectingAgent"
        mock_agent.run.return_value = TaskOutput(
            content="Cannot handle this task",
            success=False,
            error="Task not suitable",
            error_code=ErrorCode.TASK_REJECTED_AS_INAPPROPRIATE,
            conversation=[]
        )
        
        self.app.dispatcher.route_task.return_value = mock_agent
        
        # Execute task
        result = self.app._execute_with_retry("Complex task", max_retries=2)
        
        # Should fail after max retries
        self.assertFalse(result.success)
        self.assertIn("Unable to complete task after 2 attempts", result.error)
        self.assertEqual(self.app.session_stats["rejections_handled"], 2)
        
        # Verify agent was called max_retries times
        self.assertEqual(mock_agent.run.call_count, 2)
    
    def test_artifact_processing(self):
        """Test artifact processing and registration."""
        thread = self.app._create_new_thread()
        
        # Mock result with artifacts
        test_artifacts = [
            Artifact(
                file_path="test1.pdf",
                artifact_type=ArtifactType.PDF,
                description="Test PDF"
            ),
            Artifact(
                file_path="test2.py",
                artifact_type=ArtifactType.CODE,
                description="Test Python code"
            )
        ]
        
        result = TaskOutput(
            content="Generated files successfully",
            success=True,
            artifacts=test_artifacts,
            conversation=[]
        )
        
        # Process result
        initial_count = self.app.session_stats["artifacts_generated"]
        self.app._process_execution_result(result)
        
        # Verify artifacts were registered
        self.assertEqual(len(thread.artifacts), 2)
        self.assertEqual(self.app.session_stats["artifacts_generated"], initial_count + 2)
        
        # Verify artifacts are in thread
        thread_artifact_paths = [a.file_path for a in thread.artifacts]
        self.assertIn("test1.pdf", thread_artifact_paths)
        self.assertIn("test2.py", thread_artifact_paths)
    
    def test_auto_opening_rules_single_pdf(self):
        """Test auto-opening rules for single PDF."""
        with patch.object(self.app, '_auto_open_artifact') as mock_open:
            pdf_artifact = Artifact(
                file_path="report.pdf",
                artifact_type=ArtifactType.PDF,
                description="Test report"
            )
            
            self.app._apply_auto_opening_rules([pdf_artifact])
            
            mock_open.assert_called_once_with(pdf_artifact, "PDF")
    
    def test_auto_opening_rules_code_files(self):
        """Test auto-opening rules for code files."""
        with patch.object(self.app, '_auto_open_artifact') as mock_open:
            code_artifacts = [
                Artifact(
                    file_path="script1.py",
                    artifact_type=ArtifactType.CODE,
                    description="Python script 1"
                ),
                Artifact(
                    file_path="script2.py", 
                    artifact_type=ArtifactType.CODE,
                    description="Python script 2"
                )
            ]
            
            self.app._apply_auto_opening_rules(code_artifacts)
            
            # Should only open the first code file
            mock_open.assert_called_once_with(code_artifacts[0], "code")
    
    def test_auto_opening_rules_pdf_precedence(self):
        """Test that PDF auto-opening takes precedence over code files."""
        with patch.object(self.app, '_auto_open_artifact') as mock_open:
            mixed_artifacts = [
                Artifact(
                    file_path="script.py",
                    artifact_type=ArtifactType.CODE,
                    description="Python script"
                ),
                Artifact(
                    file_path="report.pdf",
                    artifact_type=ArtifactType.PDF,
                    description="Test report"
                )
            ]
            
            self.app._apply_auto_opening_rules(mixed_artifacts)
            
            # Should open PDF, not code file
            mock_open.assert_called_once()
            self.assertEqual(mock_open.call_args[0][0].file_path, "report.pdf")
            self.assertEqual(mock_open.call_args[0][1], "PDF")
    
    def test_no_auto_opening_multiple_pdfs(self):
        """Test no auto-opening when multiple PDFs are generated."""
        with patch.object(self.app, '_auto_open_artifact') as mock_open:
            pdf_artifacts = [
                Artifact(
                    file_path="report1.pdf",
                    artifact_type=ArtifactType.PDF,
                    description="Test report 1"
                ),
                Artifact(
                    file_path="report2.pdf",
                    artifact_type=ArtifactType.PDF,
                    description="Test report 2"
                )
            ]
            
            self.app._apply_auto_opening_rules(pdf_artifacts)
            
            # Should not auto-open when multiple PDFs
            mock_open.assert_not_called()
    
    def test_list_threads(self):
        """Test listing available threads."""
        # Create a few threads with different states
        thread1 = self.app._create_new_thread()
        thread1.add_message("user", "Hello 1")
        self.app._persist_current_thread()
        
        thread2 = self.app._create_new_thread()
        thread2.add_message("user", "Hello 2")
        thread2.add_message("assistant", "Hi 2")
        artifact = Artifact(
            file_path="test.pdf",
            artifact_type=ArtifactType.PDF,
            description="Test"
        )
        thread2.add_artifact(artifact)
        self.app._persist_current_thread()
        
        # List threads
        threads = self.app.list_threads()
        
        self.assertEqual(len(threads), 2)
        
        # Verify thread data
        thread_ids = [t["thread_id"] for t in threads]
        self.assertIn(str(thread1.thread_id), thread_ids)
        self.assertIn(str(thread2.thread_id), thread_ids)
        
        # Find thread2 data
        thread2_data = next(t for t in threads if t["thread_id"] == str(thread2.thread_id))
        self.assertEqual(thread2_data["message_count"], 2)
        self.assertEqual(thread2_data["artifact_count"], 1)
    
    def test_switch_thread(self):
        """Test switching between threads."""
        # Create two threads
        thread1 = self.app._create_new_thread()
        thread1.add_message("user", "Thread 1 message")
        thread1_id = thread1.thread_id
        
        thread2 = self.app._create_new_thread()
        thread2.add_message("user", "Thread 2 message")
        thread2_id = thread2.thread_id
        
        # Switch back to thread1
        success = self.app.switch_thread(thread1_id)
        
        self.assertTrue(success)
        self.assertEqual(self.app.current_thread.thread_id, thread1_id)
        self.assertEqual(len(self.app.current_thread.messages), 1)
        self.assertEqual(self.app.current_thread.messages[0].content, "Thread 1 message")
    
    def test_session_statistics(self):
        """Test session statistics collection."""
        # Perform various operations
        self.app._create_new_thread()
        self.app._create_new_thread()
        self.app.session_stats["tasks_executed"] = 5
        self.app.session_stats["commands_pre_filtered"] = 3
        
        stats = self.app.get_session_statistics()
        
        self.assertEqual(stats["threads_created"], 2)
        self.assertEqual(stats["tasks_executed"], 5)
        self.assertEqual(stats["commands_pre_filtered"], 3)
        self.assertIsNotNone(stats["current_thread_id"])
    
    def test_error_handling_in_run(self):
        """Test error handling in the main run method."""
        # Mock an exception in _execute_with_retry
        with patch.object(self.app, '_execute_with_retry', side_effect=Exception("Test error")):
            result = self.app.run("Test prompt")
            
            self.assertFalse(result.success)
            self.assertIn("something went wrong", result.content)
            self.assertEqual(result.error_code, ErrorCode.AGENT_EXECUTION_FAILED)
    
    def test_shutdown(self):
        """Test application shutdown."""
        # Create thread with some data
        thread = self.app._create_new_thread()
        thread.add_message("user", "Test message")
        
        # Mock the logger to capture shutdown message
        with patch.object(self.app.logger, 'info') as mock_log:
            self.app.shutdown()
            
            # Verify thread was persisted and shutdown was logged
            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            self.assertIn("shutting down", call_args)


class TestHedwigAppIntegration(unittest.TestCase):
    """Integration tests for HedwigApp with real components."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        self.config = HedwigConfig(
            data_dir=self.temp_path / "hedwig_integration",
            debug_mode=True
        )
    
    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('hedwig.tools.registry.ToolRegistry')
    @patch('hedwig.agents.executor.AgentExecutor')
    def test_full_app_initialization(self, mock_executor, mock_registry):
        """Test full app initialization with mocked dependencies."""
        app = HedwigApp(config=self.config)
        
        self.assertIsNotNone(app)
        self.assertIsNotNone(app.config)
        self.assertIsNotNone(app.dispatcher)
        self.assertTrue(app.threads_dir.exists())
    
    def test_thread_persistence_roundtrip(self):
        """Test complete thread persistence and loading cycle."""
        with patch('hedwig.app.ToolRegistry'), \
             patch('hedwig.app.AgentExecutor'), \
             patch('hedwig.agents.dispatcher.DispatcherAgent'):
            
            app = HedwigApp(config=self.config)
            
            # Create thread with complex data
            thread = app._create_new_thread()
            original_id = thread.thread_id
            
            # Add various message types
            thread.add_message("user", "Hello, I need help with a Python script")
            thread.add_message("assistant", "I'll help you create a Python script")
            thread.add_message("user", "Great, make it calculate fibonacci numbers")
            
            # Add artifacts
            code_artifact = Artifact(
                file_path="fibonacci.py",
                artifact_type=ArtifactType.CODE,
                description="Fibonacci calculator script"
            )
            pdf_artifact = Artifact(
                file_path="documentation.pdf", 
                artifact_type=ArtifactType.PDF,
                description="Script documentation"
            )
            
            thread.add_artifact(code_artifact)
            thread.add_artifact(pdf_artifact)
            
            # Persist thread
            app._persist_current_thread()
            
            # Create new app instance (simulating app restart)
            app2 = HedwigApp(config=self.config)
            
            # Load the persisted thread
            loaded_thread = app2._load_thread(original_id)
            
            # Verify all data was preserved
            self.assertIsNotNone(loaded_thread)
            self.assertEqual(loaded_thread.thread_id, original_id)
            self.assertEqual(len(loaded_thread.messages), 3)
            self.assertEqual(len(loaded_thread.artifacts), 2)
            
            # Verify message content
            messages = loaded_thread.messages
            self.assertEqual(messages[0].content, "Hello, I need help with a Python script")
            self.assertEqual(messages[1].role, "assistant")
            self.assertEqual(messages[2].content, "Great, make it calculate fibonacci numbers")
            
            # Verify artifacts
            artifact_paths = [a.file_path for a in loaded_thread.artifacts]
            self.assertIn("fibonacci.py", artifact_paths)
            self.assertIn("documentation.pdf", artifact_paths)
            
            # Verify artifact types
            code_artifacts = [a for a in loaded_thread.artifacts if a.artifact_type == ArtifactType.CODE]
            pdf_artifacts = [a for a in loaded_thread.artifacts if a.artifact_type == ArtifactType.PDF]
            
            self.assertEqual(len(code_artifacts), 1)
            self.assertEqual(len(pdf_artifacts), 1)


if __name__ == '__main__':
    unittest.main()