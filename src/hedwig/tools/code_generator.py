"""
Code Generator Tool for creating source code files.

This tool handles code generation across multiple programming languages
with syntax checking and automatic file organization.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class CodeGeneratorArgs(BaseModel):
    """Arguments for code generation."""
    
    code: str = Field(
        description="The source code content to generate"
    )
    
    filename: str = Field(
        description="Filename for the code file (with extension)"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Programming language (auto-detected from filename if not provided)"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Description of what this code does"
    )
    
    author: Optional[str] = Field(
        default="Hedwig AI Assistant",
        description="Author name to include in code comments"
    )
    
    add_header: bool = Field(
        default=True,
        description="Whether to add a header comment with metadata"
    )
    
    format_code: bool = Field(
        default=True,
        description="Whether to attempt basic code formatting"
    )
    
    validate_syntax: bool = Field(
        default=True,
        description="Whether to validate syntax (if possible for the language)"
    )


class CodeGeneratorTool(Tool):
    """
    Tool for generating source code files in multiple programming languages.
    
    Supports syntax validation, formatting, and automatic file organization.
    Generated code files are stored in the artifacts directory.
    """
    
    # Language configurations for syntax checking and formatting
    LANGUAGE_CONFIG = {
        'python': {
            'extensions': ['.py', '.pyw'],
            'syntax_check_cmd': ['python', '-m', 'py_compile'],
            'format_cmd': None,  # Could add black/autopep8 if available
            'comment_style': '#'
        },
        'javascript': {
            'extensions': ['.js', '.mjs'],
            'syntax_check_cmd': ['node', '--check'],
            'format_cmd': None,
            'comment_style': '//'
        },
        'typescript': {
            'extensions': ['.ts', '.tsx'],
            'syntax_check_cmd': ['tsc', '--noEmit'],
            'format_cmd': None,
            'comment_style': '//'
        },
        'java': {
            'extensions': ['.java'],
            'syntax_check_cmd': ['javac', '-cp', '.'],
            'format_cmd': None,
            'comment_style': '//'
        },
        'cpp': {
            'extensions': ['.cpp', '.cc', '.cxx'],
            'syntax_check_cmd': ['g++', '-fsyntax-only'],
            'format_cmd': None,
            'comment_style': '//'
        },
        'c': {
            'extensions': ['.c'],
            'syntax_check_cmd': ['gcc', '-fsyntax-only'],
            'format_cmd': None,
            'comment_style': '//'
        },
        'go': {
            'extensions': ['.go'],
            'syntax_check_cmd': ['go', 'fmt'],
            'format_cmd': ['go', 'fmt'],
            'comment_style': '//'
        },
        'rust': {
            'extensions': ['.rs'],
            'syntax_check_cmd': ['rustc', '--parse-only'],
            'format_cmd': ['rustfmt'],
            'comment_style': '//'
        },
        'html': {
            'extensions': ['.html', '.htm'],
            'syntax_check_cmd': None,
            'format_cmd': None,
            'comment_style': '<!--'
        },
        'css': {
            'extensions': ['.css'],
            'syntax_check_cmd': None,
            'format_cmd': None,
            'comment_style': '/*'
        },
        'bash': {
            'extensions': ['.sh', '.bash'],
            'syntax_check_cmd': ['bash', '-n'],
            'format_cmd': None,
            'comment_style': '#'
        },
        'sql': {
            'extensions': ['.sql'],
            'syntax_check_cmd': None,
            'format_cmd': None,
            'comment_style': '--'
        }
    }
    
    @property
    def args_schema(self):
        return CodeGeneratorArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.WRITE
    
    @property
    def description(self) -> str:
        return "Generate source code files with syntax checking and formatting support"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Generate a code file.
        
        Returns:
            ToolOutput with code artifact information
        """
        args = CodeGeneratorArgs(**kwargs)
        
        try:
            # Detect language from filename if not provided
            language = args.language or self._detect_language(args.filename)
            
            # Sanitize filename
            filename = self._sanitize_filename(args.filename)
            
            # Ensure artifacts directory exists
            config = get_config()
            artifacts_dir = Path(config.data_dir) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Full file path
            file_path = artifacts_dir / filename
            
            # Process the code
            final_code = self._process_code(args, language)
            
            # Write code to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_code)
            
            # Validate syntax if requested and possible
            syntax_valid = True
            syntax_error = None
            if args.validate_syntax:
                syntax_valid, syntax_error = self._validate_syntax(file_path, language)
            
            # Get code statistics
            stats = self._analyze_code(final_code, language)
            
            # Create artifact
            artifact = Artifact(
                file_path=str(file_path),
                artifact_type="code",
                description=args.description or f"{language} code file: {filename}",
                metadata={
                    "language": language,
                    "filename": filename,
                    "author": args.author,
                    "syntax_valid": syntax_valid,
                    "syntax_error": syntax_error,
                    "file_size": os.path.getsize(file_path),
                    "stats": stats
                }
            )
            
            # Prepare summary message
            summary_parts = [f"Successfully generated {language} code file '{filename}' at {file_path}"]
            
            if not syntax_valid and syntax_error:
                summary_parts.append(f"Warning: Syntax validation failed - {syntax_error}")
            
            return ToolOutput(
                text_summary=". ".join(summary_parts),
                artifacts=[artifact],
                success=True,
                metadata={
                    "tool": self.name,
                    "file_path": str(file_path),
                    "language": language,
                    "syntax_valid": syntax_valid,
                    "file_size": os.path.getsize(file_path)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate code: {str(e)}")
            return ToolOutput(
                text_summary=f"Failed to generate code: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename extension."""
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        for lang, config in self.LANGUAGE_CONFIG.items():
            if extension in config['extensions']:
                return lang
        
        # Default fallback
        return 'text'
    
    def _process_code(self, args: CodeGeneratorArgs, language: str) -> str:
        """Process the code with optional header and formatting."""
        code_lines = []
        
        # Add header if requested
        if args.add_header:
            header = self._generate_header(args, language)
            if header:
                code_lines.extend(header)
                code_lines.append("")  # Blank line after header
        
        # Add the main code
        code_lines.append(args.code)
        
        return "\n".join(code_lines)
    
    def _generate_header(self, args: CodeGeneratorArgs, language: str) -> list:
        """Generate a header comment for the code file."""
        if language not in self.LANGUAGE_CONFIG:
            return []
        
        comment_style = self.LANGUAGE_CONFIG[language]['comment_style']
        header_lines = []
        
        if comment_style == '#':
            # Python/Bash style comments
            header_lines.append(f"# {args.filename}")
            if args.description:
                header_lines.append(f"# {args.description}")
            header_lines.append(f"#")
            header_lines.append(f"# Generated by: {args.author}")
            header_lines.append(f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            header_lines.append(f"# Language: {language}")
            
        elif comment_style == '//':
            # C-style line comments
            header_lines.append(f"// {args.filename}")
            if args.description:
                header_lines.append(f"// {args.description}")
            header_lines.append(f"//")
            header_lines.append(f"// Generated by: {args.author}")
            header_lines.append(f"// Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            header_lines.append(f"// Language: {language}")
            
        elif comment_style == '/*':
            # CSS style comments
            header_lines.append(f"/*")
            header_lines.append(f" * {args.filename}")
            if args.description:
                header_lines.append(f" * {args.description}")
            header_lines.append(f" *")
            header_lines.append(f" * Generated by: {args.author}")
            header_lines.append(f" * Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            header_lines.append(f" * Language: {language}")
            header_lines.append(f" */")
            
        elif comment_style == '<!--':
            # HTML comments
            header_lines.append(f"<!--")
            header_lines.append(f"  {args.filename}")
            if args.description:
                header_lines.append(f"  {args.description}")
            header_lines.append(f"  ")
            header_lines.append(f"  Generated by: {args.author}")
            header_lines.append(f"  Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            header_lines.append(f"-->")
            
        elif comment_style == '--':
            # SQL comments
            header_lines.append(f"-- {args.filename}")
            if args.description:
                header_lines.append(f"-- {args.description}")
            header_lines.append(f"--")
            header_lines.append(f"-- Generated by: {args.author}")
            header_lines.append(f"-- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            header_lines.append(f"-- Language: {language}")
        
        return header_lines
    
    def _validate_syntax(self, file_path: Path, language: str) -> tuple[bool, Optional[str]]:
        """Validate code syntax if possible for the language."""
        if language not in self.LANGUAGE_CONFIG:
            return True, None
        
        config = self.LANGUAGE_CONFIG[language]
        check_cmd = config.get('syntax_check_cmd')
        
        if not check_cmd:
            return True, None  # No syntax checker available
        
        try:
            # Build the command
            cmd = check_cmd + [str(file_path)]
            
            # Run syntax check
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=file_path.parent
            )
            
            if result.returncode == 0:
                return True, None
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "Syntax check timed out"
        except FileNotFoundError:
            # Syntax checker not available
            return True, "Syntax checker not available"
        except Exception as e:
            return False, f"Syntax check failed: {str(e)}"
    
    def _analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze the generated code for statistics."""
        lines = code.split('\n')
        
        # Count different types of lines
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = 0
        
        if language in self.LANGUAGE_CONFIG:
            comment_style = self.LANGUAGE_CONFIG[language]['comment_style']
            if comment_style in ['#', '//', '--']:
                comment_lines = sum(1 for line in lines if line.strip().startswith(comment_style))
            elif comment_style == '/*':
                # Simple approximation for CSS/C-style block comments
                comment_lines = sum(1 for line in lines if '/*' in line or '*/' in line or line.strip().startswith('*'))
            elif comment_style == '<!--':
                comment_lines = sum(1 for line in lines if '<!--' in line or '-->' in line)
        
        code_lines = len(lines) - blank_lines - comment_lines
        
        return {
            "total_lines": len(lines),
            "code_lines": max(0, code_lines),
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "character_count": len(code),
            "word_count": len(code.split()),
            "language": language
        }
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to ensure it's safe for filesystem."""
        # Keep only safe characters
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in '.-_':
                safe_chars.append(char)
            elif char in ' /\\':
                safe_chars.append('_')
        
        filename = ''.join(safe_chars)
        
        # Ensure it has some content
        if not filename or filename.replace('.', '').replace('_', '').replace('-', '') == '':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"code_{timestamp}.txt"
        
        return filename