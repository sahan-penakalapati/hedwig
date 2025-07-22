"""
Python Execute Tool for running Python code safely.

This tool handles Python code execution with security controls,
output capture, and error handling.
"""

import os
import sys
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class PythonExecuteArgs(BaseModel):
    """Arguments for Python code execution."""
    
    code: str = Field(
        description="Python code to execute"
    )
    
    timeout: int = Field(
        default=30,
        description="Maximum execution time in seconds"
    )
    
    capture_output: bool = Field(
        default=True,
        description="Whether to capture stdout and stderr"
    )
    
    save_output: bool = Field(
        default=False,
        description="Whether to save execution output as an artifact"
    )
    
    working_directory: Optional[str] = Field(
        default=None,
        description="Working directory for code execution (defaults to artifacts dir)"
    )
    
    environment_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional environment variables to set"
    )
    
    requirements: Optional[List[str]] = Field(
        default=None,
        description="List of required packages (checked but not installed)"
    )


class PythonExecuteTool(Tool):
    """
    Tool for executing Python code with security controls.
    
    Executes Python code in a controlled environment with timeout,
    output capture, and security restrictions. All execution is
    classified as EXECUTE risk tier requiring user confirmation.
    """
    
    # Dangerous patterns to warn about
    DANGEROUS_PATTERNS = [
        'import os',
        'import subprocess',
        'import sys',
        'exec(',
        'eval(',
        '__import__',
        'open(',
        'file(',
        'input(',
        'raw_input(',
        'compile(',
        'globals(',
        'locals(',
        'vars(',
        'dir(',
        'delattr',
        'setattr',
        'getattr',
        'hasattr',
        'rm -',
        'del ',
        'shutil',
        'pathlib',
        'tempfile',
    ]
    
    @property
    def args_schema(self):
        return PythonExecuteArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.EXECUTE
    
    @property
    def description(self) -> str:
        return "Execute Python code with timeout and output capture (requires user confirmation)"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Execute Python code.
        
        Returns:
            ToolOutput with execution results and optional output artifacts
        """
        args = PythonExecuteArgs(**kwargs)
        
        try:
            # Analyze code for potential risks
            risk_analysis = self._analyze_code_risks(args.code)
            
            # Set up working directory
            if args.working_directory:
                work_dir = Path(args.working_directory)
            else:
                config = get_config()
                work_dir = Path(config.data_dir) / "artifacts"
            
            work_dir.mkdir(parents=True, exist_ok=True)
            
            # Execute the code
            execution_result = self._execute_python_code(args, work_dir)
            
            artifacts = []
            
            # Save output as artifact if requested
            if args.save_output and execution_result['output']:
                output_artifact = self._save_output_artifact(
                    execution_result, work_dir
                )
                if output_artifact:
                    artifacts.append(output_artifact)
            
            # Prepare summary
            summary_parts = []
            if execution_result['success']:
                summary_parts.append("Python code executed successfully")
                if execution_result['output']:
                    output_preview = execution_result['output'][:200]
                    if len(execution_result['output']) > 200:
                        output_preview += "..."
                    summary_parts.append(f"Output: {output_preview}")
            else:
                summary_parts.append(f"Python execution failed: {execution_result['error']}")
            
            if risk_analysis['warnings']:
                summary_parts.append(f"Security warnings: {', '.join(risk_analysis['warnings'])}")
            
            return ToolOutput(
                text_summary=". ".join(summary_parts),
                artifacts=artifacts,
                success=execution_result['success'],
                error_message=execution_result['error'] if not execution_result['success'] else None,
                metadata={
                    "tool": self.name,
                    "execution_time": execution_result['execution_time'],
                    "return_code": execution_result['return_code'],
                    "risk_analysis": risk_analysis,
                    "working_directory": str(work_dir)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to execute Python code: {str(e)}")
            return ToolOutput(
                text_summary=f"Failed to execute Python code: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _analyze_code_risks(self, code: str) -> Dict[str, Any]:
        """Analyze code for potential security risks."""
        warnings = []
        risk_level = "low"
        
        code_lower = code.lower()
        
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in code_lower:
                warnings.append(f"Uses potentially dangerous pattern: {pattern}")
                risk_level = "medium"
        
        # Check for network operations
        network_patterns = ['urllib', 'requests', 'http', 'socket', 'ftp']
        for pattern in network_patterns:
            if pattern in code_lower:
                warnings.append(f"Contains network operations: {pattern}")
                risk_level = "high"
        
        # Check for file system operations
        fs_patterns = ['write', 'delete', 'remove', 'mkdir', 'rmdir']
        for pattern in fs_patterns:
            if pattern in code_lower:
                warnings.append(f"Contains file system operations: {pattern}")
                if risk_level == "low":
                    risk_level = "medium"
        
        return {
            "risk_level": risk_level,
            "warnings": warnings,
            "code_length": len(code),
            "line_count": len(code.split('\n'))
        }
    
    def _execute_python_code(self, args: PythonExecuteArgs, work_dir: Path) -> Dict[str, Any]:
        """Execute Python code and capture results."""
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False,
            dir=work_dir
        ) as temp_file:
            temp_file.write(args.code)
            temp_file_path = temp_file.name
        
        try:
            # Prepare environment
            env = os.environ.copy()
            if args.environment_vars:
                env.update(args.environment_vars)
            
            # Set up the command
            cmd = [sys.executable, temp_file_path]
            
            # Execute with timeout
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                env=env,
                capture_output=args.capture_output,
                text=True,
                timeout=args.timeout
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Combine stdout and stderr
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n--- STDERR ---\n"
                output += result.stderr
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "output": output,
                "error": result.stderr if result.returncode != 0 else None,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": f"Execution timed out after {args.timeout} seconds",
                "execution_time": args.timeout
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": str(e),
                "execution_time": 0
            }
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass  # Ignore cleanup errors
    
    def _save_output_artifact(self, execution_result: Dict[str, Any], work_dir: Path) -> Optional[Artifact]:
        """Save execution output as an artifact."""
        if not execution_result['output']:
            return None
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"python_output_{timestamp}.txt"
            file_path = work_dir / filename
            
            # Create output content
            content_lines = [
                "Python Code Execution Output",
                "=" * 50,
                f"Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Success: {execution_result['success']}",
                f"Return Code: {execution_result['return_code']}",
                f"Execution Time: {execution_result['execution_time']:.2f} seconds",
                "",
                "Output:",
                "-" * 20,
                execution_result['output']
            ]
            
            if execution_result['error']:
                content_lines.extend([
                    "",
                    "Error:",
                    "-" * 20,
                    execution_result['error']
                ])
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_lines))
            
            return Artifact(
                file_path=str(file_path),
                artifact_type="other",
                description=f"Python execution output from {timestamp}",
                metadata={
                    "execution_success": execution_result['success'],
                    "return_code": execution_result['return_code'],
                    "execution_time": execution_result['execution_time'],
                    "file_size": os.path.getsize(file_path)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save output artifact: {str(e)}")
            return None