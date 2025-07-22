"""
Tests for Phase 5 tools: PDFGeneratorTool, MarkdownGeneratorTool, 
CodeGeneratorTool, PythonExecuteTool, and BashTool.
"""

import tempfile
import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.tools.pdf_generator import PDFGeneratorTool
from hedwig.tools.markdown_generator import MarkdownGeneratorTool
from hedwig.tools.code_generator import CodeGeneratorTool
from hedwig.tools.python_execute import PythonExecuteTool
from hedwig.tools.bash_tool import BashTool


class TestPDFGeneratorTool:
    """Test cases for the PDFGeneratorTool."""
    
    def test_pdf_generator_properties(self):
        """Test PDFGeneratorTool properties."""
        tool = PDFGeneratorTool()
        
        assert tool.risk_tier == RiskTier.WRITE
        assert "Generate formatted PDF documents" in tool.description
        assert tool.args_schema.__name__ == "PDFGeneratorArgs"
    
    @patch('hedwig.core.config.get_config')
    def test_generate_simple_pdf(self, mock_config):
        """Test generating a simple PDF document."""
        # Mock config to use temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = PDFGeneratorTool()
            result = tool.run(
                title="Test Document",
                content="This is a test PDF document with some content."
            )
            
            assert result.success is True
            assert "Successfully generated PDF document" in result.text_summary
            assert len(result.artifacts) == 1
            
            artifact = result.artifacts[0]
            assert artifact.artifact_type == "pdf"
            assert artifact.description == "PDF document: Test Document"
            assert Path(artifact.file_path).exists()
            assert Path(artifact.file_path).suffix == ".pdf"
    
    @patch('hedwig.core.config.get_config')
    def test_generate_pdf_with_tables(self, mock_config):
        """Test generating PDF with tables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = PDFGeneratorTool()
            tables = [
                {
                    "title": "Sample Data",
                    "data": [
                        ["Name", "Age", "City"],
                        ["Alice", "30", "New York"],
                        ["Bob", "25", "Los Angeles"]
                    ]
                }
            ]
            
            result = tool.run(
                title="Report with Tables",
                content="# Introduction\n\nThis report contains tables.",
                tables=tables,
                author="Test Author"
            )
            
            assert result.success is True
            assert len(result.artifacts) == 1
            assert result.artifacts[0].metadata["author"] == "Test Author"
    
    @patch('hedwig.core.config.get_config')
    def test_generate_pdf_custom_filename(self, mock_config):
        """Test generating PDF with custom filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = PDFGeneratorTool()
            result = tool.run(
                title="Custom Document",
                content="Content here.",
                filename="my_custom_report"
            )
            
            assert result.success is True
            artifact_path = Path(result.artifacts[0].file_path)
            assert "my_custom_report" in artifact_path.name
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        tool = PDFGeneratorTool()
        
        # Test sanitization
        safe_name = tool._sanitize_filename("Test/File\\With:Bad?Chars")
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert ":" not in safe_name
        assert "?" not in safe_name
        
        # Test extension removal
        safe_name = tool._sanitize_filename("test.pdf")
        assert not safe_name.endswith(".pdf")


class TestMarkdownGeneratorTool:
    """Test cases for the MarkdownGeneratorTool."""
    
    def test_markdown_generator_properties(self):
        """Test MarkdownGeneratorTool properties."""
        tool = MarkdownGeneratorTool()
        
        assert tool.risk_tier == RiskTier.WRITE
        assert "Generate formatted Markdown documents" in tool.description
        assert tool.args_schema.__name__ == "MarkdownGeneratorArgs"
    
    @patch('hedwig.core.config.get_config')
    def test_generate_simple_markdown(self, mock_config):
        """Test generating a simple Markdown document."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = MarkdownGeneratorTool()
            result = tool.run(
                title="Test Document",
                content="This is a test markdown document.\n\n## Section 1\n\nSome content here."
            )
            
            assert result.success is True
            assert "Successfully generated Markdown document" in result.text_summary
            assert len(result.artifacts) == 1
            
            artifact = result.artifacts[0]
            assert artifact.artifact_type == "markdown"
            assert Path(artifact.file_path).exists()
            assert Path(artifact.file_path).suffix == ".md"
            
            # Check content
            with open(artifact.file_path, 'r') as f:
                content = f.read()
            assert "# Test Document" in content
            assert "## Section 1" in content
    
    @patch('hedwig.core.config.get_config')
    def test_generate_markdown_with_metadata(self, mock_config):
        """Test generating Markdown with metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = MarkdownGeneratorTool()
            result = tool.run(
                title="Test with Metadata",
                content="Content here.",
                author="Test Author",
                tags=["test", "documentation"],
                include_metadata=True,
                include_toc=True
            )
            
            assert result.success is True
            
            # Check metadata in file
            with open(result.artifacts[0].file_path, 'r') as f:
                content = f.read()
            
            assert "---" in content  # YAML frontmatter
            assert "author: Test Author" in content
            assert "tags: [test, documentation]" in content
    
    @patch('hedwig.core.config.get_config')
    def test_generate_markdown_with_tables(self, mock_config):
        """Test generating Markdown with tables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = MarkdownGeneratorTool()
            tables = [
                {
                    "title": "Test Table",
                    "data": [
                        ["Column 1", "Column 2"],
                        ["Value 1", "Value 2"],
                        ["Value 3", "Value 4"]
                    ]
                }
            ]
            
            result = tool.run(
                title="Document with Tables",
                content="Main content.",
                tables=tables
            )
            
            assert result.success is True
            
            with open(result.artifacts[0].file_path, 'r') as f:
                content = f.read()
            
            assert "## Tables" in content
            assert "### Test Table" in content
            assert "| Column 1 | Column 2 |" in content
            assert "|---|---|" in content
    
    def test_table_of_contents_generation(self):
        """Test TOC generation from content headers."""
        tool = MarkdownGeneratorTool()
        
        content = """# Main Title
## Section 1
### Subsection 1.1
## Section 2
### Subsection 2.1
#### Deep Section"""
        
        toc = tool._generate_toc(content)
        
        assert len(toc) == 5  # Should find 5 headers (excluding main title)
        assert "- [Section 1](#section-1)" in toc
        assert "  - [Subsection 1.1](#subsection-11)" in toc
        assert "- [Section 2](#section-2)" in toc


class TestCodeGeneratorTool:
    """Test cases for the CodeGeneratorTool."""
    
    def test_code_generator_properties(self):
        """Test CodeGeneratorTool properties."""
        tool = CodeGeneratorTool()
        
        assert tool.risk_tier == RiskTier.WRITE
        assert "Generate source code files" in tool.description
        assert tool.args_schema.__name__ == "CodeGeneratorArgs"
    
    @patch('hedwig.core.config.get_config')
    def test_generate_python_code(self, mock_config):
        """Test generating a Python code file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = CodeGeneratorTool()
            code = """def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()"""
            
            result = tool.run(
                code=code,
                filename="hello.py",
                description="A simple hello world script"
            )
            
            assert result.success is True
            assert "Successfully generated python code file" in result.text_summary
            assert len(result.artifacts) == 1
            
            artifact = result.artifacts[0]
            assert artifact.artifact_type == "code"
            assert Path(artifact.file_path).exists()
            assert artifact.metadata["language"] == "python"
            
            # Check content
            with open(artifact.file_path, 'r') as f:
                content = f.read()
            assert "def hello_world():" in content
            assert "Generated by: Hedwig AI Assistant" in content  # Header comment
    
    @patch('hedwig.core.config.get_config')
    def test_generate_javascript_code(self, mock_config):
        """Test generating JavaScript code."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = CodeGeneratorTool()
            code = """function greet(name) {
    console.log(`Hello, ${name}!`);
}

greet('World');"""
            
            result = tool.run(
                code=code,
                filename="greet.js",
                language="javascript",
                add_header=True
            )
            
            assert result.success is True
            artifact = result.artifacts[0]
            assert artifact.metadata["language"] == "javascript"
            
            with open(artifact.file_path, 'r') as f:
                content = f.read()
            assert "function greet(name)" in content
            assert "// greet.js" in content  # Header comment
    
    def test_language_detection(self):
        """Test automatic language detection from filename."""
        tool = CodeGeneratorTool()
        
        assert tool._detect_language("script.py") == "python"
        assert tool._detect_language("app.js") == "javascript"
        assert tool._detect_language("main.cpp") == "cpp"
        assert tool._detect_language("style.css") == "css"
        assert tool._detect_language("index.html") == "html"
        assert tool._detect_language("unknown.xyz") == "text"
    
    @patch('subprocess.run')
    def test_syntax_validation_success(self, mock_run):
        """Test successful syntax validation."""
        tool = CodeGeneratorTool()
        
        # Mock successful syntax check
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        valid, error = tool._validate_syntax(Path("test.py"), "python")
        
        assert valid is True
        assert error is None
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_syntax_validation_failure(self, mock_run):
        """Test syntax validation failure."""
        tool = CodeGeneratorTool()
        
        # Mock syntax error
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "SyntaxError: invalid syntax"
        
        valid, error = tool._validate_syntax(Path("test.py"), "python")
        
        assert valid is False
        assert "SyntaxError" in error
    
    def test_code_analysis(self):
        """Test code analysis for statistics."""
        tool = CodeGeneratorTool()
        
        code = """# This is a comment
def function():
    pass

# Another comment

print("Hello")"""
        
        stats = tool._analyze_code(code, "python")
        
        assert stats["total_lines"] == 7
        assert stats["comment_lines"] == 2
        assert stats["blank_lines"] == 2
        assert stats["code_lines"] == 3
        assert stats["language"] == "python"


class TestPythonExecuteTool:
    """Test cases for the PythonExecuteTool."""
    
    def test_python_execute_properties(self):
        """Test PythonExecuteTool properties."""
        tool = PythonExecuteTool()
        
        assert tool.risk_tier == RiskTier.EXECUTE
        assert "Execute Python code" in tool.description
        assert tool.args_schema.__name__ == "PythonExecuteArgs"
    
    @patch('hedwig.core.config.get_config')
    @patch('subprocess.run')
    def test_execute_simple_python_code(self, mock_run, mock_config):
        """Test executing simple Python code."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            # Mock successful execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Hello, World!\n"
            mock_run.return_value.stderr = ""
            
            tool = PythonExecuteTool()
            result = tool.run(code='print("Hello, World!")')
            
            assert result.success is True
            assert "Python code executed successfully" in result.text_summary
            assert "Hello, World!" in result.text_summary
            mock_run.assert_called_once()
    
    @patch('hedwig.core.config.get_config')
    @patch('subprocess.run')
    def test_execute_python_with_error(self, mock_run, mock_config):
        """Test executing Python code that fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            # Mock execution failure
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "NameError: name 'undefined_var' is not defined"
            
            tool = PythonExecuteTool()
            result = tool.run(code='print(undefined_var)')
            
            assert result.success is False
            assert "Python execution failed" in result.text_summary
            assert result.metadata["return_code"] == 1
    
    @patch('hedwig.core.config.get_config')
    @patch('subprocess.run')
    def test_execute_with_timeout(self, mock_run, mock_config):
        """Test Python execution with timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            # Mock timeout
            mock_run.side_effect = subprocess.TimeoutExpired("python", 5)
            
            tool = PythonExecuteTool()
            result = tool.run(
                code='import time; time.sleep(10)',
                timeout=5
            )
            
            assert result.success is False
            assert "timed out after 5 seconds" in result.metadata["execution_time"] or \
                   "timed out" in str(result.error_message)
    
    def test_code_risk_analysis(self):
        """Test risk analysis of Python code."""
        tool = PythonExecuteTool()
        
        # Safe code
        safe_analysis = tool._analyze_code_risks("print('hello')")
        assert safe_analysis["risk_level"] == "low"
        assert len(safe_analysis["warnings"]) == 0
        
        # Code with imports
        risky_analysis = tool._analyze_code_risks("import os; os.system('ls')")
        assert risky_analysis["risk_level"] in ["medium", "high"]
        assert len(risky_analysis["warnings"]) > 0
        
        # Code with network operations
        network_analysis = tool._analyze_code_risks("import requests; requests.get('http://example.com')")
        assert network_analysis["risk_level"] == "high"
        assert any("network" in warning.lower() for warning in network_analysis["warnings"])
    
    @patch('hedwig.core.config.get_config')
    def test_save_output_artifact(self, mock_config):
        """Test saving execution output as artifact."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = PythonExecuteTool()
            execution_result = {
                "success": True,
                "return_code": 0,
                "output": "Test output\nLine 2",
                "error": None,
                "execution_time": 0.5
            }
            
            artifact = tool._save_output_artifact(execution_result, Path(temp_dir))
            
            assert artifact is not None
            assert artifact.artifact_type == "other"
            assert Path(artifact.file_path).exists()
            
            with open(artifact.file_path, 'r') as f:
                content = f.read()
            assert "Test output" in content
            assert "Line 2" in content
            assert "Execution Time: 0.50 seconds" in content


class TestBashTool:
    """Test cases for the BashTool."""
    
    def test_bash_tool_properties(self):
        """Test BashTool properties."""
        tool = BashTool()
        
        assert tool.risk_tier == RiskTier.EXECUTE
        assert "Execute shell commands" in tool.description
        assert tool.args_schema.__name__ == "BashToolArgs"
    
    @patch('hedwig.core.config.get_config')
    @patch('subprocess.run')
    def test_execute_safe_command(self, mock_run, mock_config):
        """Test executing a safe shell command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            # Mock successful execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "file1.txt\nfile2.txt\n"
            mock_run.return_value.stderr = ""
            
            tool = BashTool()
            result = tool.run(command="ls")
            
            assert result.success is True
            assert "Command executed successfully: ls" in result.text_summary
            assert "file1.txt" in result.text_summary
            mock_run.assert_called_once()
    
    @patch('hedwig.core.config.get_config')
    @patch('subprocess.run')
    def test_execute_command_with_error(self, mock_run, mock_config):
        """Test executing command that fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            # Mock command failure
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "ls: cannot access 'nonexistent': No such file or directory"
            
            tool = BashTool()
            result = tool.run(command="ls nonexistent")
            
            assert result.success is False
            assert "Command failed: ls nonexistent" in result.text_summary
            assert result.metadata["return_code"] == 1
    
    def test_risk_analysis_safe_commands(self):
        """Test risk analysis for safe commands."""
        tool = BashTool()
        
        # Safe read-only commands
        safe_commands = ["ls", "cat file.txt", "pwd", "whoami", "date"]
        
        for cmd in safe_commands:
            analysis = tool._analyze_command_risks(cmd)
            assert analysis["risk_level"] in ["read_only", "low"]
            assert analysis["dynamic_risk_tier"] in [RiskTier.WRITE, RiskTier.EXECUTE]
    
    def test_risk_analysis_risky_commands(self):
        """Test risk analysis for risky commands."""
        tool = BashTool()
        
        # Risky commands
        risky_commands = ["rm file.txt", "mv old new", "chmod 755 file", "sudo apt install"]
        
        for cmd in risky_commands:
            analysis = tool._analyze_command_risks(cmd)
            assert analysis["risk_level"] in ["medium", "high"]
            assert analysis["dynamic_risk_tier"] == RiskTier.EXECUTE
    
    def test_risk_analysis_destructive_commands(self):
        """Test risk analysis for destructive commands."""
        tool = BashTool()
        
        # Destructive commands
        destructive_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "sudo rm -rf /etc"
        ]
        
        for cmd in destructive_commands:
            analysis = tool._analyze_command_risks(cmd)
            assert analysis["risk_level"] == "destructive"
            assert analysis["dynamic_risk_tier"] == RiskTier.DESTRUCTIVE
    
    def test_dynamic_risk_tier_method(self):
        """Test the get_dynamic_risk_tier method."""
        tool = BashTool()
        
        # Test different risk levels
        assert tool.get_dynamic_risk_tier("ls") == RiskTier.WRITE
        assert tool.get_dynamic_risk_tier("rm file.txt") == RiskTier.EXECUTE
        assert tool.get_dynamic_risk_tier("rm -rf /") == RiskTier.DESTRUCTIVE
    
    @patch('hedwig.core.config.get_config')
    @patch('subprocess.run')
    def test_execute_with_timeout(self, mock_run, mock_config):
        """Test command execution with timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            # Mock timeout
            mock_run.side_effect = subprocess.TimeoutExpired("sleep", 5)
            
            tool = BashTool()
            result = tool.run(command="sleep 10", timeout=5)
            
            assert result.success is False
            assert "timed out after 5 seconds" in result.metadata["execution_time"] or \
                   "timed out" in str(result.error_message)
    
    @patch('hedwig.core.config.get_config')
    def test_save_command_output_artifact(self, mock_config):
        """Test saving command output as artifact."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config.return_value.data_dir = temp_dir
            
            tool = BashTool()
            execution_result = {
                "success": True,
                "return_code": 0,
                "output": "Command output here\nSecond line",
                "error": None,
                "execution_time": 0.2
            }
            
            artifact = tool._save_output_artifact(
                execution_result, 
                Path(temp_dir), 
                "ls -la"
            )
            
            assert artifact is not None
            assert artifact.artifact_type == "other"
            assert Path(artifact.file_path).exists()
            
            with open(artifact.file_path, 'r') as f:
                content = f.read()
            assert "Command: ls -la" in content
            assert "Command output here" in content
            assert "Execution Time: 0.20 seconds" in content


# Integration tests for tool registration
class TestToolIntegration:
    """Integration tests for Phase 5 tools."""
    
    def test_all_tools_can_be_imported(self):
        """Test that all Phase 5 tools can be imported successfully."""
        from hedwig.tools import (
            PDFGeneratorTool, MarkdownGeneratorTool, CodeGeneratorTool,
            PythonExecuteTool, BashTool
        )
        
        # Instantiate all tools
        tools = [
            PDFGeneratorTool(),
            MarkdownGeneratorTool(),
            CodeGeneratorTool(),
            PythonExecuteTool(),
            BashTool()
        ]
        
        # Basic property checks
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'risk_tier')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'args_schema')
            assert callable(tool.run)
    
    def test_tool_registration(self):
        """Test registering all Phase 5 tools."""
        from hedwig.tools import register_all_tools, get_global_registry
        
        # Clear registry first
        registry = get_global_registry()
        registry.clear()
        
        # Register all tools
        register_all_tools()
        
        # Check that all Phase 5 tools are registered
        expected_tools = [
            "pdf_generator", "markdown_generator", "code_generator",
            "python_execute", "bash"
        ]
        
        registered_names = registry.get_tool_names()
        for expected in expected_tools:
            assert expected in registered_names
        
        # Test getting each tool
        for name in expected_tools:
            tool = registry.get(name)
            assert tool is not None
            assert tool.name == name