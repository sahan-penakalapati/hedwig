"""
Security Gateway for mediating tool execution in the Hedwig system.

The SecurityGateway sits between the AgentExecutor and Tools, providing
critical security guardrails through risk assessment and user confirmation.
"""

import re
from typing import Dict, List, Optional, Any
from pathlib import Path

from hedwig.core.models import RiskTier
from hedwig.core.logging_config import get_logger
from hedwig.core.exceptions import SecurityGatewayError
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class SecurityGateway:
    """
    Security mediation layer for tool execution.
    
    All tool calls must pass through this gateway, which assesses risk
    and requires user confirmation for potentially dangerous operations.
    """
    
    def __init__(self, user_confirmation_callback=None):
        """
        Initialize the SecurityGateway.
        
        Args:
            user_confirmation_callback: Function to call for user confirmation.
                                      Should accept (message: str, timeout: int) -> bool
        """
        self.logger = get_logger("hedwig.tools.security")
        self.user_confirmation_callback = user_confirmation_callback
        self.config = get_config()
        
        # Load high-risk command patterns for dynamic assessment
        self._high_risk_patterns = self._load_risk_patterns()
        
        # Track denied operations for logging/analysis
        self._denied_operations: List[Dict] = []
    
    def _load_risk_patterns(self) -> List[str]:
        """
        Load high-risk command patterns for dynamic risk assessment.
        
        These patterns are used to escalate risk for certain command arguments,
        particularly for BashTool and similar execution tools.
        
        Returns:
            List of regex patterns for high-risk commands
        """
        # Initial implementation: hardcoded patterns
        # TODO: Externalize to risk_patterns.json for maintainability
        return [
            # File deletion and movement
            r'\brm\b.*-[rf]',  # rm -r, rm -f, rm -rf
            r'\bmv\b.*/',      # mv to overwrite directories
            
            # Disk operations
            r'\bdd\b',         # disk dump
            r'\bmkfs\b',       # make filesystem
            r'\bfdisk\b',      # disk partitioning
            
            # System modification
            r'\bchmod\b.*777', # make world-writable
            r'\bchown\b.*root', # change ownership to root
            
            # Output redirection that might overwrite system files
            r'>.*/(etc|bin|usr|sys)/',
            r'>>.*/(etc|bin|usr|sys)/',
            
            # Network operations that could be harmful
            r'\bcurl\b.*-X\s+(DELETE|PUT)',
            r'\bwget\b.*--post-data',
            
            # Process manipulation
            r'\bkillall\b',
            r'\bkill\b.*-9',
            
            # Archive extraction to system dirs
            r'\btar\b.*-C\s*/',
            r'\bunzip\b.*/',
        ]
    
    def assess_risk(self, tool: Tool, **kwargs) -> RiskTier:
        """
        Assess the risk level of a specific tool call.
        
        Considers both the tool's static risk tier and dynamic analysis
        of the specific arguments provided.
        
        Args:
            tool: Tool instance being called
            **kwargs: Arguments being passed to the tool
            
        Returns:
            Final risk tier for this specific call
        """
        base_risk = tool.risk_tier
        
        # Dynamic risk escalation based on arguments
        escalated_risk = self._analyze_arguments(tool, **kwargs)
        
        # Return the highest risk level
        risk_hierarchy = [RiskTier.READ_ONLY, RiskTier.WRITE, RiskTier.EXECUTE, RiskTier.DESTRUCTIVE]
        
        base_index = risk_hierarchy.index(base_risk)
        escalated_index = risk_hierarchy.index(escalated_risk) if escalated_risk else 0
        
        final_risk = risk_hierarchy[max(base_index, escalated_index)]
        
        if final_risk != base_risk:
            self.logger.warning(
                f"Risk escalated for {tool.name}: {base_risk.value} -> {final_risk.value} "
                f"based on arguments: {kwargs}"
            )
        
        return final_risk
    
    def _analyze_arguments(self, tool: Tool, **kwargs) -> Optional[RiskTier]:
        """
        Analyze tool arguments for dynamic risk escalation.
        
        Args:
            tool: Tool being called
            **kwargs: Tool arguments
            
        Returns:
            Escalated risk tier if warranted, None otherwise
        """
        tool_name = tool.name.lower()
        
        # Special handling for BashTool
        if 'bash' in tool_name and 'command' in kwargs:
            command = str(kwargs['command']).strip()
            
            # Check against high-risk patterns
            for pattern in self._high_risk_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    self.logger.warning(f"High-risk pattern detected in command: {command}")
                    return RiskTier.DESTRUCTIVE
        
        # Special handling for file operations
        if 'file' in tool_name:
            # Check for system file paths
            for arg_name, arg_value in kwargs.items():
                if 'path' in arg_name.lower():
                    path_str = str(arg_value)
                    if self._is_system_path(path_str):
                        self.logger.warning(f"System path access detected: {path_str}")
                        return RiskTier.EXECUTE
        
        # Python execution is always EXECUTE risk by default
        if 'python' in tool_name and 'execute' in tool_name:
            return RiskTier.EXECUTE
        
        return None
    
    def _is_system_path(self, path_str: str) -> bool:
        """
        Check if a path points to system directories.
        
        Args:
            path_str: Path string to check
            
        Returns:
            True if the path points to system directories
        """
        try:
            path = Path(path_str).resolve()
            system_dirs = ['/etc', '/bin', '/usr', '/sys', '/proc', '/dev', '/root']
            
            for sys_dir in system_dirs:
                if str(path).startswith(sys_dir):
                    return True
        except Exception:
            # If path resolution fails, err on the side of caution
            return True
        
        return False
    
    def check_authorization(self, tool: Tool, risk_tier: RiskTier, **kwargs) -> bool:
        """
        Check if a tool call is authorized to proceed.
        
        For high-risk operations, requests user confirmation.
        
        Args:
            tool: Tool being called
            risk_tier: Assessed risk tier
            **kwargs: Tool arguments
            
        Returns:
            True if authorized, False if denied
            
        Raises:
            SecurityGatewayError: If authorization fails
        """
        # READ_ONLY operations are always allowed
        if risk_tier == RiskTier.READ_ONLY:
            self.logger.debug(f"Authorized READ_ONLY tool: {tool.name}")
            return True
        
        # WRITE operations are allowed but logged
        if risk_tier == RiskTier.WRITE:
            self.logger.info(f"Authorized WRITE tool: {tool.name} with args: {kwargs}")
            return True
        
        # EXECUTE and DESTRUCTIVE operations require user confirmation
        if risk_tier in [RiskTier.EXECUTE, RiskTier.DESTRUCTIVE]:
            return self._request_user_confirmation(tool, risk_tier, **kwargs)
        
        # Fallback: deny unknown risk levels
        self.logger.error(f"Unknown risk tier: {risk_tier}")
        return False
    
    def _request_user_confirmation(self, tool: Tool, risk_tier: RiskTier, **kwargs) -> bool:
        """
        Request user confirmation for high-risk operations.
        
        Args:
            tool: Tool being called
            risk_tier: Risk tier requiring confirmation
            **kwargs: Tool arguments
            
        Returns:
            True if user approves, False otherwise
        """
        # If no confirmation callback is set, default to DENY for safety
        if not self.user_confirmation_callback:
            self.logger.error("No user confirmation callback set - denying high-risk operation")
            self._record_denial(tool, risk_tier, "No confirmation callback", **kwargs)
            return False
        
        # Prepare confirmation message
        message = self._build_confirmation_message(tool, risk_tier, **kwargs)
        timeout = self.config.security.confirmation_timeout_seconds
        
        try:
            # Request user confirmation
            approved = self.user_confirmation_callback(message, timeout)
            
            if approved:
                self.logger.info(f"User approved {risk_tier.value} operation: {tool.name}")
                return True
            else:
                self.logger.warning(f"User denied {risk_tier.value} operation: {tool.name}")
                self._record_denial(tool, risk_tier, "User denied", **kwargs)
                return False
                
        except Exception as e:
            self.logger.error(f"Confirmation callback failed: {e}")
            self._record_denial(tool, risk_tier, f"Callback error: {e}", **kwargs)
            return False
    
    def _build_confirmation_message(self, tool: Tool, risk_tier: RiskTier, **kwargs) -> str:
        """
        Build a confirmation message for the user.
        
        Args:
            tool: Tool requiring confirmation
            risk_tier: Risk tier
            **kwargs: Tool arguments
            
        Returns:
            Formatted confirmation message
        """
        if risk_tier == RiskTier.DESTRUCTIVE:
            prefix = "⚠️  DESTRUCTIVE OPERATION WARNING ⚠️"
            warning = "This operation could cause permanent damage to your system."
        else:
            prefix = "🔒 EXECUTION CONFIRMATION REQUIRED"
            warning = "This operation will execute code or system commands."
        
        # Format arguments for display
        args_display = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        if len(args_display) > 100:
            args_display = args_display[:97] + "..."
        
        message = f"""{prefix}

Tool: {tool.name} ({tool.__class__.__name__})
Risk Level: {risk_tier.value.upper()}
Arguments: {args_display}

{warning}

Do you want to proceed with this operation?"""
        
        return message
    
    def _record_denial(self, tool: Tool, risk_tier: RiskTier, reason: str, **kwargs) -> None:
        """
        Record a denied operation for logging and analysis.
        
        Args:
            tool: Tool that was denied
            risk_tier: Risk tier
            reason: Reason for denial
            **kwargs: Tool arguments
        """
        import time
        
        denial_record = {
            "timestamp": time.time(),
            "tool_name": tool.name,
            "tool_class": tool.__class__.__name__,
            "risk_tier": risk_tier.value,
            "reason": reason,
            "arguments": kwargs
        }
        
        self._denied_operations.append(denial_record)
        
        # Keep only last 100 denials to prevent memory growth
        if len(self._denied_operations) > 100:
            self._denied_operations.pop(0)
    
    def execute_tool(self, tool: Tool, **kwargs):
        """
        Execute a tool through the security gateway.
        
        This is the main public interface that agents should use
        to execute tools with proper security mediation.
        
        Args:
            tool: Tool to execute
            **kwargs: Arguments for the tool
            
        Returns:
            ToolOutput from the tool execution
            
        Raises:
            SecurityGatewayError: If execution is denied or fails
        """
        try:
            # Assess risk for this specific call
            risk_tier = self.assess_risk(tool, **kwargs)
            
            # Check authorization
            if not self.check_authorization(tool, risk_tier, **kwargs):
                raise SecurityGatewayError(
                    f"Tool execution denied: {tool.name} (risk: {risk_tier.value})",
                    "SecurityGateway"
                )
            
            # Execute the tool
            self.logger.info(f"Executing authorized tool: {tool.name}")
            return tool.run(**kwargs)
            
        except SecurityGatewayError:
            raise
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            raise SecurityGatewayError(
                f"Tool execution failed: {str(e)}",
                "SecurityGateway",
                cause=e
            )
    
    def get_denial_history(self) -> List[Dict]:
        """
        Get the history of denied operations.
        
        Returns:
            List of denial records
        """
        return self._denied_operations.copy()
    
    def get_security_stats(self) -> Dict[str, Any]:
        """
        Get statistics about security gateway operations.
        
        Returns:
            Dictionary with security statistics
        """
        from collections import Counter
        
        if not self._denied_operations:
            return {
                "total_denials": 0,
                "denials_by_tool": {},
                "denials_by_risk": {},
                "denials_by_reason": {}
            }
        
        tools = [op["tool_name"] for op in self._denied_operations]
        risks = [op["risk_tier"] for op in self._denied_operations]
        reasons = [op["reason"] for op in self._denied_operations]
        
        return {
            "total_denials": len(self._denied_operations),
            "denials_by_tool": dict(Counter(tools)),
            "denials_by_risk": dict(Counter(risks)),
            "denials_by_reason": dict(Counter(reasons))
        }