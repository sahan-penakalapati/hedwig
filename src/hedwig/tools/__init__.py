"""Tool implementations for the Hedwig system."""

from hedwig.tools.base import Tool
from hedwig.tools.registry import ToolRegistry, get_global_registry, register_tool, get_tool
from hedwig.tools.security import SecurityGateway
from hedwig.tools.file_reader import FileReaderTool
from hedwig.tools.list_artifacts import ListArtifactsTool
from hedwig.tools.pdf_generator import PDFGeneratorTool
from hedwig.tools.markdown_generator import MarkdownGeneratorTool
from hedwig.tools.code_generator import CodeGeneratorTool
from hedwig.tools.python_execute import PythonExecuteTool
from hedwig.tools.bash_tool import BashTool
from hedwig.tools.firecrawl_research import FirecrawlResearchTool
from hedwig.tools.browser_tool import BrowserTool

__all__ = [
    # Core tool infrastructure
    "Tool",
    "ToolRegistry", 
    "SecurityGateway",
    "get_global_registry",
    "register_tool",
    "get_tool",
    
    # Basic tools
    "FileReaderTool",
    "ListArtifactsTool",
    
    # Document generation tools
    "PDFGeneratorTool",
    "MarkdownGeneratorTool",
    
    # Code tools
    "CodeGeneratorTool",
    "PythonExecuteTool",
    
    # System tools
    "BashTool",
    
    # Research tools
    "FirecrawlResearchTool",
    "BrowserTool",
]


def register_all_tools():
    """
    Register all available tools in the global registry.
    
    This function should be called during application startup
    to make all tools available to agents.
    """
    # Register basic tools
    register_tool(FileReaderTool())
    register_tool(ListArtifactsTool())
    
    # Register document generation tools
    register_tool(PDFGeneratorTool())
    register_tool(MarkdownGeneratorTool())
    
    # Register code tools
    register_tool(CodeGeneratorTool())
    register_tool(PythonExecuteTool())
    
    # Register system tools
    register_tool(BashTool())
    
    # Register research tools
    register_tool(FirecrawlResearchTool())
    register_tool(BrowserTool())