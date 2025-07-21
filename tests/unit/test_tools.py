"""
Tests for the Hedwig tool system.

Tests cover the base Tool class, ToolRegistry, SecurityGateway,
and basic tool implementations like FileReaderTool and ListArtifactsTool.
"""

import tempfile
import pytest
from pathlib import Path
from typing import Type
from unittest.mock import Mock, patch

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput, Artifact, ArtifactType
from hedwig.core.artifact_registry import ArtifactRegistry
from hedwig.core.exceptions import ToolExecutionError, SecurityGatewayError
from hedwig.tools.base import Tool
from hedwig.tools.registry import ToolRegistry
from hedwig.tools.security import SecurityGateway
from hedwig.tools.file_reader import FileReaderTool
from hedwig.tools.list_artifacts import ListArtifactsTool


class MockToolInput(BaseModel):
    """Test input schema for mock tools."""
    message: str = Field(description="Test message")
    count: int = Field(default=1, description="Number of times to repeat")


class MockTool(Tool):
    """Mock tool for testing base Tool functionality."""
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        return MockToolInput
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.READ_ONLY
    
    @property
    def description(self) -> str:
        return "A mock tool for testing purposes"
    
    def _run(self, message: str, count: int = 1) -> ToolOutput:
        result = " ".join([message] * count)
        return ToolOutput(
            text_summary=f"Mock tool executed: {result}",
            artifacts=[],
            success=True,
            raw_content=result
        )


class FailingMockTool(Tool):
    """Mock tool that always fails for testing error handling."""
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        return MockToolInput
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.EXECUTE
    
    @property
    def description(self) -> str:
        return "A mock tool that always fails"
    
    def _run(self, message: str, count: int = 1) -> ToolOutput:
        raise Exception("Simulated tool failure")


class TestToolBase:
    """Test cases for the base Tool class."""
    
    def test_tool_initialization(self):
        """Test tool initialization with default and custom names."""
        # Default name generation
        tool1 = MockTool()
        assert tool1.name == "mock"
        
        # Custom name
        tool2 = MockTool(name="custom_mock")
        assert tool2.name == "custom_mock"
    
    def test_tool_name_generation(self):
        """Test automatic tool name generation from class names."""
        tool = MockTool()
        assert tool.name == "mock"  # MockTool -> mock
        
        # Test with "Tool" suffix
        class TestReaderTool(MockTool):
            pass
        
        reader_tool = TestReaderTool()
        assert reader_tool.name == "test_reader"  # TestReaderTool -> test_reader
    
    def test_tool_execution_success(self):
        """Test successful tool execution."""
        tool = MockTool()
        result = tool.run(message="hello", count=2)
        
        assert result.success is True
        assert result.text_summary == "Mock tool executed: hello hello"
        assert result.raw_content == "hello hello"
        assert result.artifacts == []
    
    def test_tool_execution_with_validation_error(self):
        """Test tool execution with invalid arguments."""
        tool = MockTool()
        
        # Missing required argument should cause validation error
        result = tool.run(count=2)  # Missing 'message'
        
        assert result.success is False
        assert "Tool execution failed" in result.text_summary
        assert result.error_message is not None
    
    def test_tool_execution_with_runtime_error(self):
        """Test tool execution with runtime errors."""
        tool = FailingMockTool()
        result = tool.run(message="test")
        
        assert result.success is False
        assert "Tool execution failed" in result.text_summary
        assert "Simulated tool failure" in result.error_message
    
    def test_tool_schema_description(self):
        """Test tool schema description generation."""
        tool = MockTool()
        description = tool.get_schema_description()
        
        assert "Input parameters:" in description
        assert "message (string) (required): Test message" in description
        assert "count (integer) (optional): Number of times to repeat" in description
    
    def test_tool_string_representation(self):
        """Test tool string representations."""
        tool = MockTool(name="test_tool")
        
        str_repr = str(tool)
        assert "MockTool" in str_repr
        assert "name='test_tool'" in str_repr
        assert "risk=read_only" in str_repr


class TestToolRegistry:
    """Test cases for the ToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        assert len(registry) == 0
        assert registry.get_tool_names() == []
    
    def test_tool_registration(self):
        """Test tool registration."""
        registry = ToolRegistry()
        tool = MockTool(name="test_tool")
        
        registry.register(tool)
        
        assert len(registry) == 1
        assert "test_tool" in registry
        assert registry.has_tool("test_tool")
        assert registry.get("test_tool") is tool
    
    def test_duplicate_registration_error(self):
        """Test error when registering duplicate tool names."""
        registry = ToolRegistry()
        tool1 = MockTool(name="duplicate")
        tool2 = MockTool(name="duplicate")
        
        registry.register(tool1)
        
        with pytest.raises(ToolExecutionError, match="already registered"):
            registry.register(tool2)
    
    def test_tool_retrieval_error(self):
        """Test error when retrieving non-existent tool."""
        registry = ToolRegistry()
        
        with pytest.raises(ToolExecutionError, match="Tool 'nonexistent' not found"):
            registry.get("nonexistent")
    
    def test_list_tools(self):
        """Test listing all registered tools."""
        registry = ToolRegistry()
        tool1 = MockTool(name="tool1")
        tool2 = MockTool(name="tool2")
        
        registry.register(tool1)
        registry.register(tool2)
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools
    
    def test_tool_descriptions(self):
        """Test generating tool descriptions."""
        registry = ToolRegistry()
        tool = MockTool(name="test_tool")
        registry.register(tool)
        
        descriptions = registry.get_tool_descriptions()
        
        assert "Available Tools:" in descriptions
        assert "test_tool" in descriptions
        assert "A mock tool for testing purposes" in descriptions
        assert "Risk Level: read_only" in descriptions
    
    def test_tools_by_risk_tier(self):
        """Test filtering tools by risk tier."""
        registry = ToolRegistry()
        
        read_tool = MockTool(name="read_tool")  # READ_ONLY
        exec_tool = FailingMockTool(name="exec_tool")  # EXECUTE
        
        registry.register(read_tool)
        registry.register(exec_tool)
        
        read_tools = registry.get_tools_by_risk_tier(RiskTier.READ_ONLY)
        exec_tools = registry.get_tools_by_risk_tier(RiskTier.EXECUTE)
        
        assert len(read_tools) == 1
        assert read_tools[0] is read_tool
        assert len(exec_tools) == 1
        assert exec_tools[0] is exec_tool
    
    def test_unregister_tool(self):
        """Test unregistering tools."""
        registry = ToolRegistry()
        tool = MockTool(name="removable")
        
        registry.register(tool)
        assert "removable" in registry
        
        removed = registry.unregister("removable")
        assert removed is tool
        assert "removable" not in registry
        
        # Unregistering non-existent tool should return None
        removed = registry.unregister("nonexistent")
        assert removed is None
    
    def test_clear_registry(self):
        """Test clearing all tools from registry."""
        registry = ToolRegistry()
        registry.register(MockTool(name="tool1"))
        registry.register(MockTool(name="tool2"))
        
        assert len(registry) == 2
        
        registry.clear()
        
        assert len(registry) == 0
        assert registry.get_tool_names() == []
    
    def test_registry_stats(self):
        """Test registry statistics."""
        registry = ToolRegistry()
        registry.register(MockTool(name="read_tool"))
        registry.register(FailingMockTool(name="exec_tool"))
        
        stats = registry.get_registry_stats()
        
        assert stats["total_tools"] == 2
        assert "read_tool" in stats["tool_names"]
        assert "exec_tool" in stats["tool_names"]
        assert stats["risk_tier_counts"][RiskTier.READ_ONLY] == 1
        assert stats["risk_tier_counts"][RiskTier.EXECUTE] == 1


class TestSecurityGateway:
    """Test cases for the SecurityGateway class."""
    
    def test_gateway_initialization(self):
        """Test security gateway initialization."""
        gateway = SecurityGateway()
        assert gateway.user_confirmation_callback is None
        
        callback = Mock(return_value=True)
        gateway_with_callback = SecurityGateway(user_confirmation_callback=callback)
        assert gateway_with_callback.user_confirmation_callback is callback
    
    def test_risk_assessment_base_tier(self):
        """Test basic risk assessment using tool's base tier."""
        gateway = SecurityGateway()
        tool = MockTool()  # READ_ONLY tier
        
        risk = gateway.assess_risk(tool, message="test")
        assert risk == RiskTier.READ_ONLY
    
    def test_authorization_read_only(self):
        """Test authorization for READ_ONLY operations."""
        gateway = SecurityGateway()
        tool = MockTool()
        
        authorized = gateway.check_authorization(tool, RiskTier.READ_ONLY, message="test")
        assert authorized is True
    
    def test_authorization_write(self):
        """Test authorization for WRITE operations."""
        gateway = SecurityGateway()
        tool = MockTool()
        
        authorized = gateway.check_authorization(tool, RiskTier.WRITE, message="test")
        assert authorized is True
    
    def test_authorization_execute_no_callback(self):
        """Test EXECUTE authorization without confirmation callback."""
        gateway = SecurityGateway()
        tool = FailingMockTool()  # EXECUTE tier
        
        authorized = gateway.check_authorization(tool, RiskTier.EXECUTE, message="test")
        assert authorized is False
    
    def test_authorization_execute_with_approval(self):
        """Test EXECUTE authorization with user approval."""
        callback = Mock(return_value=True)
        gateway = SecurityGateway(user_confirmation_callback=callback)
        tool = FailingMockTool()
        
        authorized = gateway.check_authorization(tool, RiskTier.EXECUTE, message="test")
        assert authorized is True
        callback.assert_called_once()
    
    def test_authorization_execute_with_denial(self):
        """Test EXECUTE authorization with user denial."""
        callback = Mock(return_value=False)
        gateway = SecurityGateway(user_confirmation_callback=callback)
        tool = FailingMockTool()
        
        authorized = gateway.check_authorization(tool, RiskTier.EXECUTE, message="test")
        assert authorized is False
        callback.assert_called_once()
    
    def test_execute_tool_success(self):
        """Test successful tool execution through gateway."""
        gateway = SecurityGateway()
        tool = MockTool()  # READ_ONLY - no confirmation needed
        
        result = gateway.execute_tool(tool, message="hello", count=2)
        
        assert result.success is True
        assert result.raw_content == "hello hello"
    
    def test_execute_tool_denied(self):
        """Test tool execution denied by security gateway."""
        gateway = SecurityGateway()  # No confirmation callback
        tool = FailingMockTool()  # EXECUTE tier - needs confirmation
        
        with pytest.raises(SecurityGatewayError, match="Tool execution denied"):
            gateway.execute_tool(tool, message="test")
    
    def test_denial_history(self):
        """Test tracking of denied operations."""
        gateway = SecurityGateway()
        tool = FailingMockTool()
        
        # Attempt denied operation
        try:
            gateway.execute_tool(tool, message="test")
        except SecurityGatewayError:
            pass
        
        history = gateway.get_denial_history()
        assert len(history) == 1
        assert history[0]["tool_name"] == tool.name
        assert history[0]["reason"] == "No confirmation callback"
    
    def test_security_stats(self):
        """Test security statistics."""
        gateway = SecurityGateway()
        
        # Initial stats should be empty
        stats = gateway.get_security_stats()
        assert stats["total_denials"] == 0
        
        # Create some denials
        tool = FailingMockTool()
        try:
            gateway.execute_tool(tool, message="test1")
        except SecurityGatewayError:
            pass
        
        try:
            gateway.execute_tool(tool, message="test2")  
        except SecurityGatewayError:
            pass
        
        stats = gateway.get_security_stats()
        assert stats["total_denials"] == 2
        assert stats["denials_by_tool"][tool.name] == 2


class TestFileReaderTool:
    """Test cases for the FileReaderTool."""
    
    def test_file_reader_properties(self):
        """Test FileReaderTool properties."""
        tool = FileReaderTool()
        
        assert tool.risk_tier == RiskTier.READ_ONLY
        assert "Reads the complete content" in tool.description
        assert tool.args_schema.__name__ == "FileReaderInput"
    
    def test_read_text_file_success(self):
        """Test successful text file reading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World!\nThis is a test file.")
            temp_path = f.name
        
        try:
            tool = FileReaderTool()
            result = tool.run(file_path=temp_path)
            
            assert result.success is True
            assert "Hello, World!" in result.raw_content
            assert "This is a test file." in result.raw_content
            assert "Successfully read file" in result.text_summary
            assert result.metadata["line_count"] == 2
        finally:
            Path(temp_path).unlink()
    
    def test_read_nonexistent_file(self):
        """Test reading non-existent file."""
        tool = FileReaderTool()
        result = tool.run(file_path="/nonexistent/file.txt")
        
        assert result.success is False
        assert "File not found" in result.error_message
    
    def test_read_directory(self):
        """Test reading a directory (should fail)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = FileReaderTool()
            result = tool.run(file_path=temp_dir)
            
            assert result.success is False
            assert "Path is not a file" in result.error_message
    
    def test_read_large_file(self):
        """Test reading file exceeding size limit."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Create a file larger than default 10MB limit
            large_content = "x" * (11 * 1024 * 1024)  # 11MB
            f.write(large_content)
            temp_path = f.name
        
        try:
            tool = FileReaderTool()
            result = tool.run(file_path=temp_path, max_size_mb=10.0)
            
            assert result.success is False
            assert "File too large" in result.error_message
        finally:
            Path(temp_path).unlink()
    
    def test_read_with_encoding_options(self):
        """Test reading file with different encodings."""
        content = "Hello with unicode: ñáéíóú"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', 
                                       encoding='utf-8', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            tool = FileReaderTool()
            result = tool.run(file_path=temp_path, encoding="utf-8")
            
            assert result.success is True
            assert content in result.raw_content
            assert result.metadata["encoding_used"] == "utf-8"
        finally:
            Path(temp_path).unlink()


class TestListArtifactsTool:
    """Test cases for the ListArtifactsTool."""
    
    def test_list_artifacts_properties(self):
        """Test ListArtifactsTool properties."""
        tool = ListArtifactsTool()
        
        assert tool.risk_tier == RiskTier.READ_ONLY
        assert "Lists all artifacts" in tool.description
        assert tool.args_schema.__name__ == "ListArtifactsInput"
    
    def test_list_artifacts_no_registry(self):
        """Test listing artifacts without registry set."""
        tool = ListArtifactsTool()
        result = tool.run()
        
        assert result.success is False
        assert "No artifact registry available" in result.error_message
    
    def test_list_empty_artifacts(self):
        """Test listing artifacts from empty registry."""
        from uuid import uuid4
        
        registry = ArtifactRegistry(thread_id=uuid4())
        tool = ListArtifactsTool(artifact_registry=registry)
        
        result = tool.run()
        
        assert result.success is True
        assert "No artifacts found" in result.text_summary
        assert result.metadata["total_artifacts"] == 0
    
    def test_list_artifacts_with_content(self):
        """Test listing artifacts from populated registry."""
        from uuid import uuid4
        
        registry = ArtifactRegistry(thread_id=uuid4())
        
        # Create test artifacts
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
            pdf_file.write(b"fake pdf content")
            pdf_path = Path(pdf_file.name)
        
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as code_file:
            code_file.write(b"print('hello')")
            code_path = Path(code_file.name)
        
        try:
            # Add artifacts to registry
            pdf_artifact = Artifact(
                file_path=pdf_path,
                artifact_type=ArtifactType.PDF,
                description="Test PDF document"
            )
            code_artifact = Artifact(
                file_path=code_path,
                artifact_type=ArtifactType.CODE,
                description="Test Python script"
            )
            
            registry.register_artifact(pdf_artifact)
            registry.register_artifact(code_artifact)
            
            # Test listing all artifacts
            tool = ListArtifactsTool(artifact_registry=registry)
            result = tool.run()
            
            assert result.success is True
            assert "Found 2 artifact(s)" in result.text_summary
            assert pdf_path.name in result.text_summary
            assert code_path.name in result.text_summary
            assert result.metadata["total_artifacts"] == 2
            
        finally:
            pdf_path.unlink()
            code_path.unlink()
    
    def test_list_artifacts_filtered_by_type(self):
        """Test listing artifacts filtered by type."""
        from uuid import uuid4
        
        registry = ArtifactRegistry(thread_id=uuid4())
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
            pdf_file.write(b"fake pdf content")
            pdf_path = Path(pdf_file.name)
        
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as code_file:
            code_file.write(b"print('hello')")
            code_path = Path(code_file.name)
        
        try:
            pdf_artifact = Artifact(
                file_path=pdf_path,
                artifact_type=ArtifactType.PDF,
                description="Test PDF"
            )
            code_artifact = Artifact(
                file_path=code_path,
                artifact_type=ArtifactType.CODE,
                description="Test code"
            )
            
            registry.register_artifact(pdf_artifact)
            registry.register_artifact(code_artifact)
            
            # Test filtering by PDF type
            tool = ListArtifactsTool(artifact_registry=registry)
            result = tool.run(artifact_type="pdf")
            
            assert result.success is True
            assert "Found 1 pdf artifact(s)" in result.text_summary
            assert pdf_path.name in result.text_summary
            assert code_path.name not in result.text_summary
            assert result.metadata["total_artifacts"] == 1
            assert result.metadata["filtered_type"] == "pdf"
            
        finally:
            pdf_path.unlink()
            code_path.unlink()
    
    def test_list_artifacts_invalid_type(self):
        """Test listing with invalid artifact type."""
        from uuid import uuid4
        
        registry = ArtifactRegistry(thread_id=uuid4())
        tool = ListArtifactsTool(artifact_registry=registry)
        
        result = tool.run(artifact_type="invalid_type")
        
        assert result.success is False
        assert "Invalid artifact type" in result.error_message
        assert "Valid types:" in result.error_message
    
    def test_artifacts_summary(self):
        """Test quick artifacts summary method."""
        from uuid import uuid4
        
        # Test with no registry
        tool = ListArtifactsTool()
        summary = tool.get_artifacts_summary()
        assert "No artifact registry available" in summary
        
        # Test with empty registry
        registry = ArtifactRegistry(thread_id=uuid4())
        tool.set_artifact_registry(registry)
        summary = tool.get_artifacts_summary()
        assert "No artifacts in current thread" in summary