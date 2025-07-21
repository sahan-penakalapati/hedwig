"""
Unit tests for Hedwig core data models.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from hedwig.core.models import (
    Artifact, ArtifactType, ChatThread, ConversationMessage,
    ErrorCode, TaskInput, TaskOutput, ToolOutput, AgentDescription
)


class TestArtifact:
    """Tests for Artifact model."""
    
    def test_artifact_creation(self):
        """Test creating an artifact."""
        artifact = Artifact(
            file_path="test/file.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test file"
        )
        
        assert artifact.file_path == "test/file.txt"
        assert artifact.artifact_type == ArtifactType.OTHER
        assert artifact.description == "Test file"
        assert isinstance(artifact.artifact_id, UUID)
        assert isinstance(artifact.created_at, datetime)
    
    def test_artifact_to_dict(self):
        """Test artifact serialization."""
        artifact = Artifact(
            file_path="test/file.py",
            artifact_type=ArtifactType.CODE,
            description="Python script"
        )
        
        data = artifact.to_dict()
        
        assert data["file_path"] == "test/file.py"
        assert data["artifact_type"] == "code"
        assert data["description"] == "Python script"
        assert "created_at" in data
        assert "artifact_id" in data
    
    def test_artifact_from_dict(self):
        """Test artifact deserialization."""
        artifact_id = uuid4()
        created_at = datetime.now()
        
        data = {
            "file_path": "test/file.pdf",
            "artifact_type": "pdf",
            "description": "Test document",
            "created_at": created_at.isoformat(),
            "artifact_id": str(artifact_id),
            "metadata": {"size": 1024}
        }
        
        artifact = Artifact.from_dict(data)
        
        assert artifact.file_path == "test/file.pdf"
        assert artifact.artifact_type == ArtifactType.PDF
        assert artifact.description == "Test document"
        assert artifact.artifact_id == artifact_id
        assert artifact.metadata == {"size": 1024}


class TestToolOutput:
    """Tests for ToolOutput model."""
    
    def test_tool_output_creation(self):
        """Test creating a tool output."""
        output = ToolOutput(
            text_summary="Operation completed successfully",
            success=True
        )
        
        assert output.text_summary == "Operation completed successfully"
        assert output.success is True
        assert output.artifacts == []
        assert output.error is None
    
    def test_tool_output_with_artifacts(self):
        """Test tool output with artifacts."""
        artifact = Artifact(
            file_path="output.txt",
            artifact_type=ArtifactType.OTHER,
            description="Generated text"
        )
        
        output = ToolOutput(
            text_summary="Created text file",
            artifacts=[artifact]
        )
        
        assert output.has_artifacts()
        assert len(output.artifacts) == 1
        assert output.artifacts[0] == artifact
    
    def test_add_artifact(self):
        """Test adding artifact to tool output."""
        output = ToolOutput(text_summary="Test")
        artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test"
        )
        
        output.add_artifact(artifact)
        
        assert output.has_artifacts()
        assert len(output.artifacts) == 1


class TestTaskInput:
    """Tests for TaskInput model."""
    
    def test_task_input_creation(self):
        """Test creating task input."""
        task_input = TaskInput(
            prompt="Write a hello world program",
            parameters={"language": "python"}
        )
        
        assert task_input.prompt == "Write a hello world program"
        assert task_input.parameters == {"language": "python"}
        assert task_input.tools is None
        assert task_input.conversation == []
    
    def test_task_input_validation(self):
        """Test task input validation."""
        with pytest.raises(ValueError):
            TaskInput(prompt="")  # Empty prompt should fail
        
        with pytest.raises(ValueError):
            TaskInput(prompt="   ")  # Whitespace-only prompt should fail
    
    def test_prompt_stripping(self):
        """Test prompt whitespace stripping."""
        task_input = TaskInput(prompt="  hello world  ")
        assert task_input.prompt == "hello world"


class TestTaskOutput:
    """Tests for TaskOutput model."""
    
    def test_task_output_creation(self):
        """Test creating task output."""
        output = TaskOutput(
            content="Task completed successfully",
            success=True
        )
        
        assert output.content == "Task completed successfully"
        assert output.success is True
        assert output.error is None
        assert output.artifacts == []
    
    def test_task_output_with_error(self):
        """Test task output with error."""
        output = TaskOutput(
            content="Task failed",
            success=False,
            error="Something went wrong",
            error_code=ErrorCode.TOOL_EXECUTION_FAILED
        )
        
        assert output.success is False
        assert output.error == "Something went wrong"
        assert output.error_code == ErrorCode.TOOL_EXECUTION_FAILED
    
    def test_get_artifacts_by_type(self):
        """Test filtering artifacts by type."""
        pdf_artifact = Artifact(
            file_path="doc.pdf",
            artifact_type=ArtifactType.PDF,
            description="PDF document"
        )
        code_artifact = Artifact(
            file_path="script.py",
            artifact_type=ArtifactType.CODE,
            description="Python script"
        )
        
        output = TaskOutput(
            content="Generated files",
            artifacts=[pdf_artifact, code_artifact]
        )
        
        pdf_artifacts = output.get_artifacts_by_type(ArtifactType.PDF)
        code_artifacts = output.get_artifacts_by_type(ArtifactType.CODE)
        
        assert len(pdf_artifacts) == 1
        assert len(code_artifacts) == 1
        assert pdf_artifacts[0] == pdf_artifact
        assert code_artifacts[0] == code_artifact


class TestChatThread:
    """Tests for ChatThread model."""
    
    def test_chat_thread_creation(self):
        """Test creating a chat thread."""
        thread = ChatThread()
        
        assert isinstance(thread.thread_id, UUID)
        assert isinstance(thread.created_at, datetime)
        assert thread.messages == []
        assert thread.artifacts == []
    
    def test_add_message(self):
        """Test adding message to thread."""
        thread = ChatThread()
        message = thread.add_message("user", "Hello world")
        
        assert len(thread.messages) == 1
        assert message.role == "user"
        assert message.content == "Hello world"
        assert isinstance(message.message_id, UUID)
    
    def test_add_artifact(self):
        """Test adding artifact to thread."""
        thread = ChatThread()
        artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test file"
        )
        
        thread.add_artifact(artifact)
        
        assert len(thread.artifacts) == 1
        assert thread.artifacts[0] == artifact
    
    def test_get_conversation_history(self):
        """Test getting conversation history."""
        thread = ChatThread()
        thread.add_message("user", "Hello")
        thread.add_message("assistant", "Hi there!")
        
        history = thread.get_conversation_history()
        
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}


class TestAgentDescription:
    """Tests for AgentDescription model."""
    
    def test_agent_description_creation(self):
        """Test creating agent description."""
        description = AgentDescription(
            agent_name="TestAgent",
            purpose="Tests things",
            capabilities=["testing", "validation"],
            example_tasks=["Run tests", "Validate code"]
        )
        
        assert description.agent_name == "TestAgent"
        assert description.purpose == "Tests things"
        assert description.capabilities == ["testing", "validation"]
        assert description.example_tasks == ["Run tests", "Validate code"]
    
    def test_agent_description_validation(self):
        """Test agent description validation."""
        with pytest.raises(ValueError):
            AgentDescription(
                agent_name="TestAgent",
                purpose="Tests things",
                capabilities=[],  # Empty capabilities should fail
                example_tasks=["Test task"]
            )
        
        with pytest.raises(ValueError):
            AgentDescription(
                agent_name="TestAgent", 
                purpose="Tests things",
                capabilities=["testing"],
                example_tasks=[]  # Empty example_tasks should fail
            )