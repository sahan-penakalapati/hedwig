"""
Bash Tool for executing shell commands safely.

This tool handles shell command execution with security controls,
dynamic risk assessment, and output capture.
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class BashToolArgs(BaseModel):
    """Arguments for bash command execution."""
    
    command: str = Field(
        description="Shell command to execute"
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
        description="Whether to save command output as an artifact"
    )
    
    working_directory: Optional[str] = Field(
        default=None,
        description="Working directory for command execution (defaults to artifacts dir)"
    )
    
    environment_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional environment variables to set"
    )
    
    shell: str = Field(
        default="/bin/bash",
        description="Shell to use for command execution"
    )


class BashTool(Tool):
    """
    Tool for executing shell commands with security controls.
    
    Executes shell commands with dynamic risk assessment, timeout controls,
    and output capture. Risk level is determined by command content.
    """
    
    # Highly destructive command patterns (DESTRUCTIVE risk)
    DESTRUCTIVE_PATTERNS = [
        'rm -rf /',
        'rm -rf *',
        'rm -r /',
        'dd if=',
        'mkfs',
        'fdisk',
        'parted',
        'format ',
        'del /s',
        'deltree',
        'rmdir /s',
        'shutdown',
        'reboot',
        'halt',
        'poweroff',
        'kill -9 1',
        'killall -9',
        'pkill -9',
        'sudo rm -rf',
        'sudo dd',
        'sudo mkfs',
        'mv /etc/',
        'mv /usr/',
        'mv /bin/',
        'mv /sbin/',
        'chmod 000',
        '> /dev/',
        'cat > /dev/',
        'echo > /dev/',
        'truncate -s 0',
        'shred -v',
        'wipefs',
        'crontab -r',
        'systemctl stop',
        'systemctl disable',
        'service stop',
        'iptables -F',
        'ufw disable'
    ]
    
    # Risky command patterns (EXECUTE risk)
    RISKY_PATTERNS = [
        'rm ',
        'mv ',
        'cp ',
        'chmod ',
        'chown ',
        'chgrp ',
        'sudo ',
        'su ',
        'curl ',
        'wget ',
        'git clone',
        'pip install',
        'npm install',
        'apt install',
        'yum install',
        'brew install',
        'make install',
        'docker run',
        'docker exec',
        'ssh ',
        'scp ',
        'rsync ',
        'find / -name',
        'find . -name',
        'locate ',
        'which ',
        'whereis ',
        'ps aux',
        'netstat ',
        'lsof ',
        'mount ',
        'umount ',
        'crontab ',
        'systemctl ',
        'service ',
        'kill ',
        'killall ',
        'pkill ',
        'nohup ',
        'screen ',
        'tmux ',
        'bg ',
        'jobs ',
        'history -c',
        'alias ',
        'unalias ',
        'export ',
        'source ',
        '. /',
        'eval ',
        'exec ',
        'bash -c',
        'sh -c',
        'python -c',
        'perl -e',
        'awk ',
        'sed -i',
        'tr -d',
        'grep -r /',
        'tail -f',
        'head -',
        'sort ',
        'uniq ',
        'cut -',
        'paste ',
        'join ',
        'diff ',
        'patch ',
        'tar -x',
        'unzip ',
        'gunzip ',
        'bunzip2 ',
        'uncompress '
    ]
    
    # File modification patterns
    FILE_MODIFICATION_PATTERNS = [
        ' > ',
        ' >> ',
        'echo >',
        'echo >>',
        'cat >',
        'cat >>',
        'printf >',
        'printf >>',
        'tee ',
        'touch ',
        'mkdir ',
        'rmdir ',
        'ln -s',
        'ln ',
        'rename ',
        'basename ',
        'dirname '
    ]
    
    @property
    def args_schema(self):
        return BashToolArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        # Base risk tier - will be escalated by dynamic assessment
        return RiskTier.EXECUTE
    
    @property
    def description(self) -> str:
        return "Execute shell commands with dynamic risk assessment and security controls"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Execute a shell command.
        
        Returns:
            ToolOutput with execution results and optional output artifacts
        """
        args = BashToolArgs(**kwargs)
        
        try:
            # Analyze command for security risks
            risk_analysis = self._analyze_command_risks(args.command)
            
            # Log the risk assessment
            self.logger.info(f"Command risk analysis: {risk_analysis}")
            
            # Set up working directory
            if args.working_directory:
                work_dir = Path(args.working_directory)
            else:
                config = get_config()
                work_dir = Path(config.data_dir) / "artifacts"
            
            work_dir.mkdir(parents=True, exist_ok=True)
            
            # Execute the command
            execution_result = self._execute_command(args, work_dir)
            
            artifacts = []
            
            # Save output as artifact if requested
            if args.save_output and execution_result['output']:
                output_artifact = self._save_output_artifact(
                    execution_result, work_dir, args.command
                )
                if output_artifact:
                    artifacts.append(output_artifact)
            
            # Prepare summary
            summary_parts = []
            if execution_result['success']:
                summary_parts.append(f"Command executed successfully: {args.command}")
                if execution_result['output']:
                    output_preview = execution_result['output'][:200]
                    if len(execution_result['output']) > 200:
                        output_preview += "..."
                    summary_parts.append(f"Output: {output_preview}")
            else:
                summary_parts.append(f"Command failed: {args.command}")
                if execution_result['error']:
                    summary_parts.append(f"Error: {execution_result['error']}")
            
            if risk_analysis['warnings']:
                summary_parts.append(f"Security warnings: {', '.join(risk_analysis['warnings'])}")
            
            return ToolOutput(
                text_summary=". ".join(summary_parts),
                artifacts=artifacts,
                success=execution_result['success'],
                error_message=execution_result['error'] if not execution_result['success'] else None,
                metadata={
                    "tool": self.name,
                    "command": args.command,
                    "execution_time": execution_result['execution_time'],
                    "return_code": execution_result['return_code'],
                    "risk_analysis": risk_analysis,
                    "working_directory": str(work_dir)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to execute command: {str(e)}")
            return ToolOutput(
                text_summary=f"Failed to execute command: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _analyze_command_risks(self, command: str) -> Dict[str, Any]:
        """Analyze command for security risks and determine dynamic risk level."""
        warnings = []
        risk_level = "low"
        dynamic_risk_tier = RiskTier.EXECUTE  # Default for bash commands
        
        command_lower = command.lower().strip()
        
        # Check for destructive patterns
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if pattern in command_lower:
                warnings.append(f"HIGHLY DESTRUCTIVE: {pattern}")
                risk_level = "destructive"
                dynamic_risk_tier = RiskTier.DESTRUCTIVE
                break  # One destructive pattern is enough
        
        # If not destructive, check for risky patterns
        if risk_level != "destructive":
            for pattern in self.RISKY_PATTERNS:
                if pattern in command_lower:
                    warnings.append(f"Risky operation: {pattern}")
                    risk_level = "high"
                    dynamic_risk_tier = RiskTier.EXECUTE
        
        # Check for file modifications
        has_file_ops = False
        for pattern in self.FILE_MODIFICATION_PATTERNS:
            if pattern in command:  # Case sensitive for operators
                warnings.append(f"File modification: {pattern}")
                has_file_ops = True
                if risk_level == "low":
                    risk_level = "medium"
        
        # Check for network operations
        network_patterns = ['curl', 'wget', 'nc ', 'netcat', 'ssh', 'scp', 'rsync']
        for pattern in network_patterns:
            if pattern in command_lower:
                warnings.append(f"Network operation: {pattern}")
                if risk_level in ["low", "medium"]:
                    risk_level = "medium"
        
        # Check for package management
        package_patterns = ['apt install', 'yum install', 'pip install', 'npm install', 'brew install']
        for pattern in package_patterns:
            if pattern in command_lower:
                warnings.append(f"Package installation: {pattern}")
                if risk_level in ["low", "medium"]:
                    risk_level = "high"
        
        # Check for system modifications
        system_patterns = ['systemctl', 'service', 'crontab', 'mount', 'umount']
        for pattern in system_patterns:
            if pattern in command_lower:
                warnings.append(f"System modification: {pattern}")
                if risk_level in ["low", "medium"]:
                    risk_level = "high"
        
        # Safe read-only operations get WRITE risk
        readonly_patterns = ['ls', 'cat', 'head', 'tail', 'grep', 'find', 'ps', 'pwd', 'whoami', 'date', 'echo']
        is_readonly = any(command_lower.startswith(pattern) for pattern in readonly_patterns)
        
        if risk_level == "low" and is_readonly and not has_file_ops:
            dynamic_risk_tier = RiskTier.WRITE
            risk_level = "read_only"
        
        return {
            "risk_level": risk_level,
            "dynamic_risk_tier": dynamic_risk_tier,
            "warnings": warnings,
            "command_length": len(command),
            "has_sudo": 'sudo' in command_lower,
            "has_pipes": '|' in command,
            "has_redirects": any(op in command for op in ['>', '>>', '<']),
            "has_background": '&' in command,
            "has_variables": '$' in command
        }
    
    def _execute_command(self, args: BashToolArgs, work_dir: Path) -> Dict[str, Any]:
        """Execute shell command and capture results."""
        try:
            # Prepare environment
            env = os.environ.copy()
            if args.environment_vars:
                env.update(args.environment_vars)
            
            # Execute with timeout
            start_time = time.time()
            
            result = subprocess.run(
                args.command,
                cwd=work_dir,
                env=env,
                shell=True,
                executable=args.shell,
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
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "error": result.stderr if result.returncode != 0 else None,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "stdout": "",
                "stderr": "",
                "error": f"Command timed out after {args.timeout} seconds",
                "execution_time": args.timeout
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "stdout": "",
                "stderr": "",
                "error": str(e),
                "execution_time": 0
            }
    
    def _save_output_artifact(self, execution_result: Dict[str, Any], work_dir: Path, command: str) -> Optional[Artifact]:
        """Save command output as an artifact."""
        if not execution_result['output']:
            return None
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_command = ''.join(c if c.isalnum() or c in '-_' else '_' for c in command[:30])
            filename = f"bash_output_{safe_command}_{timestamp}.txt"
            file_path = work_dir / filename
            
            # Create output content
            content_lines = [
                "Bash Command Execution Output",
                "=" * 50,
                f"Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Command: {command}",
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
                description=f"Bash command output: {command[:50]}{'...' if len(command) > 50 else ''}",
                metadata={
                    "command": command,
                    "execution_success": execution_result['success'],
                    "return_code": execution_result['return_code'],
                    "execution_time": execution_result['execution_time'],
                    "file_size": os.path.getsize(file_path)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save output artifact: {str(e)}")
            return None
    
    def get_dynamic_risk_tier(self, command: str) -> RiskTier:
        """
        Get the dynamic risk tier for a specific command.
        
        This method is used by the SecurityGateway for dynamic risk assessment.
        """
        risk_analysis = self._analyze_command_risks(command)
        return risk_analysis['dynamic_risk_tier']