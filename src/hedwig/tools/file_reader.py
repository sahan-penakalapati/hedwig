"""
FileReaderTool: Basic file reading capability for the Hedwig system.

This tool provides safe file reading functionality with proper error handling
and security considerations. It's essential for agents to access the contents
of artifacts and other files.
"""

from pathlib import Path
from typing import Any, Dict, Type
from pydantic import BaseModel, Field

from hedwig.core.models import ToolOutput, RiskTier, ArtifactType
from hedwig.tools.base import Tool


class FileReaderArgs(BaseModel):
    """Arguments for the FileReaderTool."""
    
    file_path: str = Field(
        ..., 
        description="Path to the file to read"
    )
    max_lines: int = Field(
        default=1000,
        description="Maximum number of lines to read (for large files)"
    )


class FileReaderTool(Tool):
    """
    Tool for reading file contents safely.
    
    This tool provides essential file reading capability for agents
    to access artifact contents and other files in the system.
    """
    
    name = "file_reader"
    description = "Read the contents of a text file safely"
    args_schema = FileReaderArgs
    risk_tier = RiskTier.READ_ONLY
    
    def _run(self, file_path: str, max_lines: int = 1000) -> ToolOutput:
        """
        Read the contents of a file.
        
        Args:
            file_path: Path to the file to read
            max_lines: Maximum number of lines to read
            
        Returns:
            ToolOutput containing the file contents
        """
        try:
            path = Path(file_path)
            
            # Basic security check - ensure file exists and is readable
            if not path.exists():
                return ToolOutput(
                    text_summary=f"File not found: {file_path}",
                    success=False,
                    error=f"File does not exist: {file_path}"
                )
            
            if not path.is_file():
                return ToolOutput(
                    text_summary=f"Path is not a file: {file_path}",
                    success=False,
                    error=f"Path is not a regular file: {file_path}"
                )
            
            # Read file contents
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    if max_lines > 0:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= max_lines:
                                break
                            lines.append(line.rstrip('\n\r'))
                        content = '\n'.join(lines)
                        
                        # Check if there are more lines
                        truncated = (i >= max_lines - 1)
                    else:
                        content = f.read()
                        truncated = False
                
            except UnicodeDecodeError:
                return ToolOutput(
                    text_summary=f"Cannot read file as text: {file_path}",
                    success=False,
                    error=f"File appears to be binary or has encoding issues: {file_path}"
                )
            
            # Get file stats
            file_size = path.stat().st_size
            line_count = len(content.split('\n'))
            
            # Create summary
            if truncated:
                text_summary = f"Read first {max_lines} lines of {file_path} ({file_size} bytes total)"
            else:
                text_summary = f"Read {file_path} ({file_size} bytes, {line_count} lines)"
            
            return ToolOutput(
                text_summary=text_summary,
                artifacts=[],  # Reading doesn't create new artifacts
                success=True,
                raw_content=content,  # Include full content for agent use
                metadata={
                    "file_path": str(path.resolve()),
                    "file_size_bytes": file_size,
                    "line_count": line_count,
                    "truncated": truncated,
                    "max_lines": max_lines
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to read file {file_path}: {str(e)}"
            return ToolOutput(
                text_summary=error_msg,
                success=False,
                error=error_msg
            )