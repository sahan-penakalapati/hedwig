"""
ListArtifactsTool: Tool for discovering artifacts in the current chat thread.

This tool allows agents to discover what artifacts are available in the current
conversation context, which is essential for tasks like "open the PDF" or
"show me what files we've generated".
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from hedwig.core.models import ToolOutput, RiskTier, Artifact
from hedwig.tools.base import Tool


class ListArtifactsArgs(BaseModel):
    """Arguments for the ListArtifactsTool."""
    
    artifact_type: Optional[str] = Field(
        default=None,
        description="Optional filter by artifact type (pdf, code, markdown, etc.)"
    )
    limit: int = Field(
        default=50,
        description="Maximum number of artifacts to list"
    )


class ListArtifactsTool(Tool):
    """
    Tool for listing available artifacts in the current thread.
    
    This tool provides artifact discovery capability, allowing agents
    to see what files have been generated and are available for use.
    """
    
    name = "list_artifacts"
    description = "List all artifacts available in the current conversation thread"
    args_schema = ListArtifactsArgs
    risk_tier = RiskTier.READ_ONLY
    
    def __init__(self, artifact_provider=None):
        """
        Initialize the tool with an artifact provider.
        
        Args:
            artifact_provider: Callable that returns list of artifacts for current thread
        """
        super().__init__()
        self.artifact_provider = artifact_provider
    
    def set_artifact_provider(self, provider):
        """Set the artifact provider function."""
        self.artifact_provider = provider
    
    def _run(self, artifact_type: Optional[str] = None, limit: int = 50) -> ToolOutput:
        """
        List artifacts in the current thread.
        
        Args:
            artifact_type: Optional filter by artifact type
            limit: Maximum number of artifacts to list
            
        Returns:
            ToolOutput containing the artifact list
        """
        try:
            # Get artifacts from provider (e.g., current thread)
            if not self.artifact_provider:
                return ToolOutput(
                    text_summary="No artifact provider configured - cannot list artifacts",
                    success=False,
                    error="ListArtifactsTool not properly configured with artifact provider"
                )
            
            all_artifacts = self.artifact_provider()
            
            if not all_artifacts:
                return ToolOutput(
                    text_summary="No artifacts found in the current conversation",
                    success=True,
                    metadata={"artifact_count": 0}
                )
            
            # Filter by type if specified
            if artifact_type:
                filtered_artifacts = [
                    a for a in all_artifacts 
                    if a.artifact_type.value.lower() == artifact_type.lower()
                ]
                filter_msg = f" of type '{artifact_type}'"
            else:
                filtered_artifacts = all_artifacts
                filter_msg = ""
            
            # Apply limit
            if limit > 0:
                displayed_artifacts = filtered_artifacts[:limit]
                truncated = len(filtered_artifacts) > limit
            else:
                displayed_artifacts = filtered_artifacts
                truncated = False
            
            if not displayed_artifacts:
                return ToolOutput(
                    text_summary=f"No artifacts found{filter_msg} in the current conversation",
                    success=True,
                    metadata={
                        "artifact_count": 0,
                        "filter_type": artifact_type,
                        "total_artifacts": len(all_artifacts)
                    }
                )
            
            # Build artifact list
            artifact_lines = [f"Available artifacts{filter_msg}:"]
            
            for i, artifact in enumerate(displayed_artifacts, 1):
                # Get file name from path
                file_name = artifact.file_path.split('/')[-1] if '/' in artifact.file_path else artifact.file_path
                
                # Format entry
                type_display = artifact.artifact_type.value.upper()
                artifact_lines.append(f"  {i}. {file_name} ({type_display}) - {artifact.description}")
            
            if truncated:
                remaining = len(filtered_artifacts) - limit
                artifact_lines.append(f"\n... and {remaining} more artifacts")
            
            text_summary = "\n".join(artifact_lines)
            
            return ToolOutput(
                text_summary=text_summary,
                success=True,
                raw_content=displayed_artifacts,  # Provide artifacts for programmatic access
                metadata={
                    "artifact_count": len(displayed_artifacts),
                    "total_artifacts": len(all_artifacts),
                    "filtered_artifacts": len(filtered_artifacts),
                    "filter_type": artifact_type,
                    "truncated": truncated,
                    "limit": limit
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to list artifacts: {str(e)}"
            return ToolOutput(
                text_summary=error_msg,
                success=False,
                error=error_msg
            )