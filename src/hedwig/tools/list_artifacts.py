"""
List Artifacts Tool for discovering available artifacts in the Hedwig system.

This tool allows agents to discover artifacts within the current chat thread
on-demand, handling user requests like "open the pdf" or "show me the files".
"""

from typing import Type, Optional, List
from pathlib import Path

from pydantic import BaseModel, Field

from hedwig.core.models import RiskTier, ToolOutput, ArtifactType
from hedwig.core.artifact_registry import ArtifactRegistry
from hedwig.core.exceptions import ToolExecutionError
from hedwig.tools.base import Tool


class ListArtifactsInput(BaseModel):
    """Input schema for ListArtifactsTool."""
    
    artifact_type: Optional[str] = Field(
        default=None,
        description="Optional filter by artifact type (pdf, code, markdown, research, other)"
    )
    include_metadata: bool = Field(
        default=False,
        description="Whether to include detailed metadata in the output"
    )


class ListArtifactsTool(Tool):
    """
    Tool for discovering available artifacts within the current chat thread.
    
    This tool provides agents with a list of all artifacts currently tracked
    in the active ArtifactRegistry, enabling requests like "open the pdf" or
    "show me all the code files".
    
    Risk Tier: READ_ONLY - Safe operation that only reads registry data.
    """
    
    def __init__(self, artifact_registry: ArtifactRegistry = None, name: str = None):
        """
        Initialize the ListArtifactsTool.
        
        Args:
            artifact_registry: ArtifactRegistry instance to query.
                              If None, must be set before use.
            name: Optional custom tool name
        """
        super().__init__(name)
        self.artifact_registry = artifact_registry
    
    def set_artifact_registry(self, artifact_registry: ArtifactRegistry) -> None:
        """
        Set the artifact registry to query.
        
        This method allows the registry to be updated for different chat threads.
        
        Args:
            artifact_registry: ArtifactRegistry instance to use
        """
        self.artifact_registry = artifact_registry
        self.logger.debug(f"Artifact registry set for thread: {artifact_registry.thread_id}")
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        """Input schema for the list artifacts tool."""
        return ListArtifactsInput
    
    @property
    def risk_tier(self) -> RiskTier:
        """Listing artifacts is a safe, read-only operation."""
        return RiskTier.READ_ONLY
    
    @property
    def description(self) -> str:
        """Tool description for agent discovery."""
        return (
            "Lists all artifacts available in the current chat thread. "
            "Use this to discover PDFs, code files, documents, and other generated content. "
            "Can filter by artifact type and include detailed metadata."
        )
    
    def _run(
        self, 
        artifact_type: Optional[str] = None,
        include_metadata: bool = False
    ) -> ToolOutput:
        """
        List artifacts from the current registry.
        
        Args:
            artifact_type: Optional filter by artifact type
            include_metadata: Whether to include detailed metadata
            
        Returns:
            ToolOutput with formatted artifact list
            
        Raises:
            ToolExecutionError: If registry is not set or operation fails
        """
        try:
            # Check if registry is available
            if self.artifact_registry is None:
                raise ToolExecutionError(
                    "No artifact registry available. Registry must be set before use.",
                    "ListArtifactsTool"
                )
            
            # Get artifacts, optionally filtered by type
            if artifact_type:
                # Validate artifact type
                try:
                    filter_type = ArtifactType(artifact_type.lower())
                    artifacts = self.artifact_registry.get_by_type(filter_type)
                except ValueError:
                    valid_types = [t.value for t in ArtifactType]
                    raise ToolExecutionError(
                        f"Invalid artifact type '{artifact_type}'. "
                        f"Valid types: {', '.join(valid_types)}",
                        "ListArtifactsTool"
                    )
            else:
                artifacts = self.artifact_registry.list_all()
            
            # Build the response
            if not artifacts:
                if artifact_type:
                    summary = f"No {artifact_type} artifacts found in the current thread."
                else:
                    summary = "No artifacts found in the current thread."
                
                return ToolOutput(
                    text_summary=summary,
                    artifacts=[],
                    success=True,
                    metadata={
                        "total_artifacts": 0,
                        "filtered_type": artifact_type,
                        "thread_id": str(self.artifact_registry.thread_id)
                    }
                )
            
            # Format the artifact list
            summary_lines = []
            
            if artifact_type:
                summary_lines.append(f"Found {len(artifacts)} {artifact_type} artifact(s):")
            else:
                summary_lines.append(f"Found {len(artifacts)} artifact(s) in current thread:")
            
            summary_lines.append("")  # Empty line for formatting
            
            # List each artifact
            for i, artifact in enumerate(artifacts, 1):
                # Basic info - handle both Path and string file_path
                if hasattr(artifact.file_path, 'name'):
                    file_name = artifact.file_path.name
                else:
                    file_name = Path(artifact.file_path).name
                    
                artifact_line = f"[{i}] {file_name}"
                
                # Add type information
                if hasattr(artifact, 'artifact_type'):
                    artifact_line += f" ({artifact.artifact_type.value.upper()})"
                
                # Add size information if available
                try:
                    file_path_obj = Path(artifact.file_path)
                    if file_path_obj.exists():
                        size_mb = file_path_obj.stat().st_size / (1024 * 1024)
                        if size_mb >= 1.0:
                            artifact_line += f" - {size_mb:.1f}MB"
                        else:
                            size_kb = file_path_obj.stat().st_size / 1024
                            artifact_line += f" - {size_kb:.1f}KB"
                except Exception:
                    artifact_line += " - Size unknown"
                
                summary_lines.append(artifact_line)
                
                # Add description if available
                if hasattr(artifact, 'description') and artifact.description:
                    summary_lines.append(f"    Description: {artifact.description}")
                
                # Add metadata if requested
                if include_metadata:
                    summary_lines.append(f"    Full path: {artifact.file_path}")
                    if hasattr(artifact, 'created_at'):
                        summary_lines.append(f"    Created: {artifact.created_at}")
                    if hasattr(artifact, 'artifact_id'):
                        summary_lines.append(f"    ID: {artifact.artifact_id}")
                
                summary_lines.append("")  # Empty line between artifacts
            
            # Add summary statistics
            if not artifact_type:
                type_counts = {}
                for artifact in artifacts:
                    if hasattr(artifact, 'artifact_type'):
                        artifact_type_val = artifact.artifact_type.value
                        type_counts[artifact_type_val] = type_counts.get(artifact_type_val, 0) + 1
                
                if type_counts:
                    summary_lines.append("Breakdown by type:")
                    for atype, count in sorted(type_counts.items()):
                        summary_lines.append(f"  - {atype}: {count}")
            
            text_summary = "\n".join(summary_lines)
            
            return ToolOutput(
                text_summary=text_summary,
                artifacts=[],  # This tool doesn't create new artifacts
                success=True,
                metadata={
                    "total_artifacts": len(artifacts),
                    "filtered_type": artifact_type,
                    "thread_id": str(self.artifact_registry.thread_id),
                    "artifact_ids": [
                        str(artifact.artifact_id) if hasattr(artifact, 'artifact_id') else None
                        for artifact in artifacts
                    ],
                    "artifact_paths": [str(artifact.file_path) for artifact in artifacts],
                    "include_metadata": include_metadata
                }
            )
            
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"Failed to list artifacts: {str(e)}",
                "ListArtifactsTool",
                cause=e
            )
    
    def get_artifacts_summary(self) -> str:
        """
        Get a quick summary of available artifacts.
        
        Returns:
            Brief summary string, or error message if registry not available
        """
        try:
            if self.artifact_registry is None:
                return "No artifact registry available"
            
            artifacts = self.artifact_registry.list_all()
            if not artifacts:
                return "No artifacts in current thread"
            
            # Count by type
            type_counts = {}
            for artifact in artifacts:
                if hasattr(artifact, 'artifact_type'):
                    artifact_type = artifact.artifact_type.value
                    type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
            
            if not type_counts:
                return f"{len(artifacts)} artifacts (types unknown)"
            
            parts = []
            for atype, count in sorted(type_counts.items()):
                parts.append(f"{count} {atype}")
            
            return f"{len(artifacts)} artifacts: {', '.join(parts)}"
            
        except Exception as e:
            return f"Error getting artifacts summary: {str(e)}"


def create_list_artifacts_tool(artifact_registry: ArtifactRegistry = None) -> ListArtifactsTool:
    """
    Factory function to create a ListArtifactsTool instance.
    
    Args:
        artifact_registry: Optional ArtifactRegistry instance
        
    Returns:
        Configured ListArtifactsTool instance
    """
    return ListArtifactsTool(artifact_registry=artifact_registry)