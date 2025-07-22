"""
PDF Generator Tool for creating formatted PDF documents.

This tool handles PDF document generation with support for tables,
data visualization, and automatic opening of generated files.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage
)
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class PDFGeneratorArgs(BaseModel):
    """Arguments for PDF generation."""
    
    title: str = Field(
        description="Title of the PDF document"
    )
    
    content: str = Field(
        description="Main content of the PDF document (supports basic markdown formatting)"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Custom filename for the PDF (without extension). If not provided, generates from title"
    )
    
    author: Optional[str] = Field(
        default="Hedwig AI Assistant",
        description="Author name to include in PDF metadata"
    )
    
    subject: Optional[str] = Field(
        default=None,
        description="Subject/topic of the document for PDF metadata"
    )
    
    tables: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of table data to include. Each dict should have 'title' and 'data' keys"
    )
    
    page_size: str = Field(
        default="letter",
        description="Page size for the PDF (letter, A4)"
    )


class PDFGeneratorTool(Tool):
    """
    Tool for generating formatted PDF documents.
    
    Supports rich text formatting, tables, and automatic file organization.
    Generated PDFs are stored in the artifacts directory and can be auto-opened.
    """
    
    @property
    def args_schema(self):
        return PDFGeneratorArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.WRITE
    
    @property
    def description(self) -> str:
        return "Generate formatted PDF documents with tables and data visualization support"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Generate a PDF document.
        
        Returns:
            ToolOutput with PDF artifact information
        """
        args = PDFGeneratorArgs(**kwargs)
        
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
            file_path = artifacts_dir / f"{filename}.pdf"
            
            # Generate PDF
            self._create_pdf(args, file_path)
            
            # Create artifact
            artifact = Artifact(
                file_path=str(file_path),
                artifact_type="pdf",
                description=f"PDF document: {args.title}",
                metadata={
                    "title": args.title,
                    "author": args.author,
                    "subject": args.subject,
                    "page_count": self._get_page_count(file_path),
                    "file_size": os.path.getsize(file_path)
                }
            )
            
            return ToolOutput(
                text_summary=f"Successfully generated PDF document '{args.title}' at {file_path}",
                artifacts=[artifact],
                success=True,
                metadata={
                    "tool": self.name,
                    "file_path": str(file_path),
                    "file_size": os.path.getsize(file_path)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF: {str(e)}")
            return ToolOutput(
                text_summary=f"Failed to generate PDF: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _create_pdf(self, args: PDFGeneratorArgs, file_path: Path) -> None:
        """Create the PDF document."""
        # Determine page size
        page_size = A4 if args.page_size.lower() == "a4" else letter
        
        # Create document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
            title=args.title,
            author=args.author,
            subject=args.subject
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        # Build story (content)
        story = []
        
        # Add title
        story.append(Paragraph(args.title, title_style))
        story.append(Spacer(1, 12))
        
        # Add metadata if available
        if args.author or args.subject:
            metadata_lines = []
            if args.author:
                metadata_lines.append(f"Author: {args.author}")
            if args.subject:
                metadata_lines.append(f"Subject: {args.subject}")
            metadata_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            metadata_text = "<br/>".join(metadata_lines)
            story.append(Paragraph(metadata_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Process and add main content
        content_paragraphs = self._format_content(args.content, styles)
        story.extend(content_paragraphs)
        
        # Add tables if provided
        if args.tables:
            for table_data in args.tables:
                story.append(Spacer(1, 20))
                table_element = self._create_table(table_data, styles)
                story.append(table_element)
        
        # Build PDF
        doc.build(story)
    
    def _format_content(self, content: str, styles) -> List:
        """Format text content with basic markdown support."""
        paragraphs = []
        
        # Split content into paragraphs
        for paragraph in content.split('\n\n'):
            if not paragraph.strip():
                continue
                
            # Handle headers
            if paragraph.startswith('# '):
                text = paragraph[2:].strip()
                paragraphs.append(Paragraph(text, styles['Heading1']))
            elif paragraph.startswith('## '):
                text = paragraph[3:].strip()
                paragraphs.append(Paragraph(text, styles['Heading2']))
            elif paragraph.startswith('### '):
                text = paragraph[4:].strip()
                paragraphs.append(Paragraph(text, styles['Heading3']))
            # Handle bullet points
            elif paragraph.startswith('- ') or paragraph.startswith('* '):
                lines = paragraph.split('\n')
                for line in lines:
                    if line.strip().startswith(('- ', '* ')):
                        text = line.strip()[2:]
                        paragraphs.append(Paragraph(f"• {text}", styles['Normal']))
            else:
                # Regular paragraph with basic formatting
                formatted_text = self._apply_basic_formatting(paragraph)
                paragraphs.append(Paragraph(formatted_text, styles['Normal']))
            
            # Add spacing
            paragraphs.append(Spacer(1, 12))
        
        return paragraphs
    
    def _apply_basic_formatting(self, text: str) -> str:
        """Apply basic markdown formatting to text."""
        # Bold text
        text = text.replace('**', '<b>').replace('**', '</b>')
        # Italic text
        text = text.replace('*', '<i>').replace('*', '</i>')
        # Code snippets
        text = text.replace('`', '<font name="Courier">').replace('`', '</font>')
        
        return text
    
    def _create_table(self, table_data: Dict[str, Any], styles) -> Table:
        """Create a formatted table from data."""
        title = table_data.get('title', 'Table')
        data = table_data.get('data', [])
        
        if not data:
            return Paragraph(f"<b>{title}</b>: No data provided", styles['Normal'])
        
        # Create table
        table = Table(data)
        
        # Style the table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Add title
        elements = [
            Paragraph(f"<b>{title}</b>", styles['Heading3']),
            Spacer(1, 12),
            table
        ]
        
        return table
    
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
        if filename.endswith('.pdf'):
            filename = filename[:-4]
        
        # Keep only safe characters
        filename = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in filename)
        filename = '_'.join(filename.split())
        
        return filename or "document"
    
    def _get_page_count(self, file_path: Path) -> int:
        """Get the number of pages in the generated PDF."""
        try:
            # Try using PyPDF2 if available
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    return len(reader.pages)
            except ImportError:
                # Fallback: estimate based on file size (rough approximation)
                file_size = os.path.getsize(file_path)
                # Very rough estimate: ~50KB per page
                estimated_pages = max(1, file_size // 50000)
                return estimated_pages
                
        except Exception:
            return 1  # Default to 1 page if unable to determine