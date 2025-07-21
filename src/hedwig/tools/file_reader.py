"""
File Reader Tool for reading artifact contents in the Hedwig system.

This tool allows agents to read the complete contents of text-based
artifacts beyond their text_summary for detailed analysis.
"""

from pathlib import Path
from typing import Type

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput
from hedwig.core.exceptions import ToolExecutionError
from hedwig.tools.base import Tool


class FileReaderInput(BaseModel):
    """Input schema for FileReaderTool."""
    
    file_path: str = Field(
        description="Path to the file to read (obtained from an Artifact object)"
    )
    encoding: str = Field(
        default="utf-8",
        description="Text encoding to use when reading the file"
    )
    max_size_mb: float = Field(
        default=10.0,
        description="Maximum file size in MB to prevent reading huge files"
    )


class FileReaderTool(Tool):
    """
    Tool for reading the full content of text-based artifacts.
    
    Primary use case: Allow agents to read the complete content of previously
    generated files for detailed analysis in subsequent steps (e.g., reading
    generated code to write documentation for it).
    
    Risk Tier: READ_ONLY - Safe operation that only reads data.
    """
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        """Input schema for the file reader tool."""
        return FileReaderInput
    
    @property
    def risk_tier(self) -> RiskTier:
        """File reading is a safe, read-only operation."""
        return RiskTier.READ_ONLY
    
    @property
    def description(self) -> str:
        """Tool description for agent discovery."""
        return (
            "Reads the complete content of text-based files from disk. "
            "Use this to access the full content of artifacts beyond their summary. "
            "Supports various text encodings and has size limits for safety."
        )
    
    def _run(self, file_path: str, encoding: str = "utf-8", max_size_mb: float = 10.0) -> ToolOutput:
        """
        Read the contents of a text file.
        
        Args:
            file_path: Path to the file to read
            encoding: Text encoding to use
            max_size_mb: Maximum file size in MB
            
        Returns:
            ToolOutput with file contents
            
        Raises:
            ToolExecutionError: If file cannot be read or is too large
        """
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                raise ToolExecutionError(
                    f"File not found: {file_path}",
                    "FileReaderTool"
                )
            
            # Check if it's a file (not a directory)
            if not path.is_file():
                raise ToolExecutionError(
                    f"Path is not a file: {file_path}",
                    "FileReaderTool"
                )
            
            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                raise ToolExecutionError(
                    f"File too large: {file_size_mb:.2f}MB > {max_size_mb}MB limit",
                    "FileReaderTool"
                )
            
            # Attempt to read the file
            try:
                content = path.read_text(encoding=encoding)
            except UnicodeDecodeError as e:
                # Try common alternative encodings
                alternative_encodings = ['latin1', 'cp1252', 'iso-8859-1']
                content = None
                
                for alt_encoding in alternative_encodings:
                    try:
                        content = path.read_text(encoding=alt_encoding)
                        self.logger.warning(
                            f"Successfully read {file_path} using {alt_encoding} "
                            f"encoding (original {encoding} failed)"
                        )
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    raise ToolExecutionError(
                        f"Could not decode file {file_path} with encoding {encoding} "
                        f"or alternatives {alternative_encodings}. Original error: {str(e)}",
                        "FileReaderTool",
                        cause=e
                    )
            
            # Check if file appears to be binary
            if self._appears_binary(content):
                raise ToolExecutionError(
                    f"File appears to be binary and cannot be read as text: {file_path}",
                    "FileReaderTool"
                )
            
            # Prepare summary info
            line_count = len(content.splitlines())
            char_count = len(content)
            file_size_kb = path.stat().st_size / 1024
            
            text_summary = (
                f"Successfully read file: {file_path}\n"
                f"File size: {file_size_kb:.1f}KB\n"
                f"Lines: {line_count:,}\n"
                f"Characters: {char_count:,}\n"
                f"Encoding: {encoding}"
            )
            
            return ToolOutput(
                text_summary=text_summary,
                artifacts=[],  # Reading doesn't create new artifacts
                success=True,
                raw_content=content,  # Include full content for agent use
                metadata={
                    "file_path": str(path.resolve()),
                    "file_size_bytes": path.stat().st_size,
                    "line_count": line_count,
                    "character_count": char_count,
                    "encoding_used": encoding
                }
            )
            
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"Failed to read file {file_path}: {str(e)}",
                "FileReaderTool",
                cause=e
            )
    
    def _appears_binary(self, content: str, sample_size: int = 8192) -> bool:
        """
        Check if content appears to be binary data.
        
        Args:
            content: File content to check
            sample_size: Number of characters to sample
            
        Returns:
            True if content appears binary, False if text
        """
        # Sample the beginning of the content
        sample = content[:sample_size]
        
        # Check for null bytes (strong indicator of binary data)
        if '\x00' in sample:
            return True
        
        # Check for high ratio of non-printable characters
        printable_chars = sum(1 for c in sample if c.isprintable() or c.isspace())
        ratio = printable_chars / len(sample) if sample else 1.0
        
        # If less than 95% of characters are printable, consider it binary
        return ratio < 0.95


def create_file_reader_tool() -> FileReaderTool:
    """
    Factory function to create a FileReaderTool instance.
    
    Returns:
        Configured FileReaderTool instance
    """
    return FileReaderTool()