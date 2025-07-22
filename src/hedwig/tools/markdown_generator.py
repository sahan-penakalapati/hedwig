"""
Markdown Generator Tool for creating formatted Markdown documents.

This tool handles Markdown document generation with support for
structured content, tables, and automatic file organization.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class MarkdownGeneratorArgs(BaseModel):
    """Arguments for Markdown generation."""
    
    title: str = Field(
        description="Title of the Markdown document"
    )
    
    content: str = Field(
        description="Main content of the Markdown document"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Custom filename for the Markdown file (without extension). If not provided, generates from title"
    )
    
    author: Optional[str] = Field(
        default=None,
        description="Author name to include in document metadata"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="List of tags to include in document metadata"
    )
    
    include_toc: bool = Field(
        default=False,
        description="Whether to include a table of contents"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Whether to include YAML frontmatter with metadata"
    )
    
    tables: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of table data to include. Each dict should have 'title' and 'data' keys"
    )


class MarkdownGeneratorTool(Tool):
    """
    Tool for generating formatted Markdown documents.
    
    Supports structured content, tables, metadata, and automatic file organization.
    Generated Markdown files are stored in the artifacts directory.
    """
    
    @property
    def args_schema(self):
        return MarkdownGeneratorArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.WRITE
    
    @property
    def description(self) -> str:
        return "Generate formatted Markdown documents with tables, metadata, and structured content"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Generate a Markdown document.
        
        Returns:
            ToolOutput with Markdown artifact information
        """
        args = MarkdownGeneratorArgs(**kwargs)
        
        try:
            # Generate filename if not provided
            if not args.filename:
                filename = self._generate_filename(args.title)
            else:
                filename = self._sanitize_filename(args.filename)
            
            # Ensure artifacts directory exists
            config = get_config()
            artifacts_dir = Path(config.data_dir) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Full file path
            file_path = artifacts_dir / f"{filename}.md"
            
            # Generate Markdown content
            markdown_content = self._create_markdown(args)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Count approximate elements
            stats = self._analyze_content(markdown_content)
            
            # Create artifact
            artifact = Artifact(
                file_path=str(file_path),
                artifact_type="markdown",
                description=f"Markdown document: {args.title}",
                metadata={
                    "title": args.title,
                    "author": args.author,
                    "tags": args.tags,
                    "word_count": stats["word_count"],
                    "line_count": stats["line_count"],
                    "file_size": os.path.getsize(file_path)
                }
            )
            
            return ToolOutput(
                text_summary=f"Successfully generated Markdown document '{args.title}' at {file_path}",
                artifacts=[artifact],
                success=True,
                metadata={
                    "tool": self.name,
                    "file_path": str(file_path),
                    "file_size": os.path.getsize(file_path),
                    "stats": stats
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate Markdown: {str(e)}")
            return ToolOutput(
                text_summary=f"Failed to generate Markdown: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _create_markdown(self, args: MarkdownGeneratorArgs) -> str:
        """Create the Markdown document content."""
        lines = []
        
        # Add YAML frontmatter if requested
        if args.include_metadata:
            lines.append("---")
            lines.append(f"title: {args.title}")
            
            if args.author:
                lines.append(f"author: {args.author}")
            
            lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
            lines.append(f"created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if args.tags:
                tags_str = ", ".join(args.tags)
                lines.append(f"tags: [{tags_str}]")
            
            lines.append("generator: Hedwig AI Assistant")
            lines.append("---")
            lines.append("")
        
        # Add title as H1
        lines.append(f"# {args.title}")
        lines.append("")
        
        # Add metadata section if author or tags provided
        if args.author or args.tags:
            metadata_lines = []
            if args.author:
                metadata_lines.append(f"**Author:** {args.author}")
            if args.tags:
                tags_formatted = ", ".join([f"`{tag}`" for tag in args.tags])
                metadata_lines.append(f"**Tags:** {tags_formatted}")
            
            metadata_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            for meta_line in metadata_lines:
                lines.append(meta_line)
            lines.append("")
        
        # Add table of contents if requested
        if args.include_toc:
            toc = self._generate_toc(args.content)
            if toc:
                lines.append("## Table of Contents")
                lines.append("")
                lines.extend(toc)
                lines.append("")
                lines.append("---")
                lines.append("")
        
        # Add main content
        lines.append(args.content)
        
        # Add tables if provided
        if args.tables:
            lines.append("")
            lines.append("## Tables")
            lines.append("")
            
            for table_data in args.tables:
                table_markdown = self._create_table_markdown(table_data)
                lines.extend(table_markdown)
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_toc(self, content: str) -> List[str]:
        """Generate a table of contents from content headers."""
        toc_lines = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                # Count header level
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                # Extract header text
                header_text = line[level:].strip()
                if header_text:
                    # Create anchor link
                    anchor = header_text.lower().replace(' ', '-').replace('?', '').replace('!', '')
                    anchor = ''.join(c for c in anchor if c.isalnum() or c in '-_')
                    
                    # Create TOC entry with proper indentation
                    indent = "  " * (level - 1)
                    toc_lines.append(f"{indent}- [{header_text}](#{anchor})")
        
        return toc_lines
    
    def _create_table_markdown(self, table_data: Dict[str, Any]) -> List[str]:
        """Create Markdown table from data."""
        title = table_data.get('title', 'Table')
        data = table_data.get('data', [])
        
        if not data:
            return [f"### {title}", "", "*No data provided*", ""]
        
        lines = [f"### {title}", ""]
        
        # Assume first row is headers
        if len(data) > 0:
            headers = data[0]
            lines.append("| " + " | ".join(str(cell) for cell in headers) + " |")
            lines.append("|" + "---|" * len(headers))
            
            # Add data rows
            for row in data[1:]:
                row_str = "| " + " | ".join(str(cell) for cell in row) + " |"
                lines.append(row_str)
        
        return lines
    
    def _analyze_content(self, content: str) -> Dict[str, int]:
        """Analyze the generated content for statistics."""
        lines = content.split('\n')
        words = content.split()
        
        return {
            "line_count": len(lines),
            "word_count": len(words),
            "character_count": len(content),
            "header_count": len([line for line in lines if line.strip().startswith('#')]),
            "table_count": len([line for line in lines if '|' in line and line.strip().startswith('|')])
        }
    
    def _generate_filename(self, title: str) -> str:
        """Generate a safe filename from the title."""
        filename = title.lower()
        filename = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in filename)
        filename = '_'.join(filename.split())
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{filename}_{timestamp}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a user-provided filename."""
        # Remove file extension if provided
        if filename.endswith('.md'):
            filename = filename[:-3]
        
        # Keep only safe characters
        filename = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in filename)
        filename = '_'.join(filename.split())
        
        return filename or "document"