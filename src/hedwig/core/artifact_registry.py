"""
Artifact Registry for thread-scoped artifact tracking.

The ArtifactRegistry maintains a complete inventory of all artifacts
generated within a chat thread, providing auto-opening logic and
persistence functionality.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID

from hedwig.core.models import Artifact, ArtifactType


class ArtifactRegistry:
    """
    Thread-scoped registry for tracking artifacts generated during task execution.
    
    Each chat thread has its own ArtifactRegistry instance that manages
    artifacts created within that thread's context.
    """
    
    def __init__(self, thread_id: UUID):
        """
        Initialize artifact registry for a specific thread.
        
        Args:
            thread_id: Unique identifier for the chat thread
        """
        self.thread_id = thread_id
        self._artifacts: Dict[str, Artifact] = {}  # artifact_id -> Artifact
        self._by_type: Dict[ArtifactType, List[Artifact]] = {
            artifact_type: [] for artifact_type in ArtifactType
        }
        self._by_path: Dict[str, Artifact] = {}  # file_path -> Artifact
        self.logger = logging.getLogger(f"{__name__}.{thread_id}")
    
    def register(self, artifact: Artifact) -> bool:
        """
        Register a new artifact with the registry.
        
        Args:
            artifact: The artifact to register
            
        Returns:
            True if registered successfully, False if already exists
        """
        artifact_id = str(artifact.artifact_id)
        
        if artifact_id in self._artifacts:
            self.logger.warning(f"Artifact {artifact_id} already registered")
            return False
        
        # Add to all tracking structures
        self._artifacts[artifact_id] = artifact
        self._by_type[artifact.artifact_type].append(artifact)
        self._by_path[artifact.file_path] = artifact
        
        self.logger.info(f"Registered artifact: {artifact.description} ({artifact.artifact_type.value})")
        return True
    
    def get_by_id(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by its unique ID."""
        return self._artifacts.get(artifact_id)
    
    def get_by_path(self, file_path: str) -> Optional[Artifact]:
        """Get artifact by its file path."""
        return self._by_path.get(file_path)
    
    def get_by_type(self, artifact_type: ArtifactType) -> List[Artifact]:
        """Get all artifacts of a specific type."""
        return self._by_type[artifact_type].copy()
    
    def list_all(self) -> List[Artifact]:
        """Get all registered artifacts."""
        return list(self._artifacts.values())
    
    def count(self) -> int:
        """Get total number of registered artifacts."""
        return len(self._artifacts)
    
    def count_by_type(self, artifact_type: ArtifactType) -> int:
        """Get count of artifacts by type."""
        return len(self._by_type[artifact_type])
    
    def has_artifacts(self) -> bool:
        """Check if any artifacts are registered."""
        return len(self._artifacts) > 0
    
    def get_auto_open_artifacts(self, new_artifacts: List[Artifact]) -> List[Artifact]:
        """
        Determine which artifacts should be auto-opened based on Hedwig's rules.
        
        Auto-opening Rules:
        - If exactly one new PDF artifact: auto-open that PDF
        - If one or more new code artifacts: auto-open the first code artifact
        - PDF rule takes precedence over code rule
        - No other artifact types are auto-opened
        
        Args:
            new_artifacts: List of newly generated artifacts from the current turn
            
        Returns:
            List of artifacts that should be auto-opened
        """
        if not new_artifacts:
            return []
        
        # Separate artifacts by type
        new_pdfs = [a for a in new_artifacts if a.artifact_type == ArtifactType.PDF]
        new_code = [a for a in new_artifacts if a.artifact_type == ArtifactType.CODE]
        
        to_open = []
        
        # Rule 1: If exactly one new PDF, auto-open it
        if len(new_pdfs) == 1:
            to_open.append(new_pdfs[0])
            self.logger.info(f"Auto-opening PDF: {new_pdfs[0].file_path}")
        
        # Rule 2: If one or more code artifacts and no PDF rule applied
        elif len(new_code) >= 1:
            to_open.append(new_code[0])  # First code artifact
            self.logger.info(f"Auto-opening code file: {new_code[0].file_path}")
        
        return to_open
    
    def get_artifacts_summary(self) -> str:
        """
        Generate a formatted string summary of all artifacts.
        
        Used by ListArtifactsTool to provide agents with artifact information.
        """
        if not self.has_artifacts():
            return "No artifacts available in this thread."
        
        lines = ["Available artifacts:"]
        for i, artifact in enumerate(self.list_all(), 1):
            artifact_desc = f"[{i}] {Path(artifact.file_path).name} ({artifact.artifact_type.value.upper()})"
            if artifact.description:
                artifact_desc += f" - {artifact.description}"
            lines.append(artifact_desc)
        
        return "\n".join(lines)
    
    def remove_artifact(self, artifact_id: str) -> bool:
        """
        Remove an artifact from the registry.
        
        Args:
            artifact_id: ID of the artifact to remove
            
        Returns:
            True if removed successfully, False if not found
        """
        if artifact_id not in self._artifacts:
            return False
        
        artifact = self._artifacts[artifact_id]
        
        # Remove from all tracking structures
        del self._artifacts[artifact_id]
        self._by_type[artifact.artifact_type].remove(artifact)
        del self._by_path[artifact.file_path]
        
        self.logger.info(f"Removed artifact: {artifact.description}")
        return True
    
    def clear(self) -> None:
        """Clear all artifacts from the registry."""
        count = len(self._artifacts)
        self._artifacts.clear()
        for artifact_list in self._by_type.values():
            artifact_list.clear()
        self._by_path.clear()
        
        self.logger.info(f"Cleared {count} artifacts from registry")
    
    def to_dict(self) -> Dict:
        """
        Convert registry to dictionary for serialization.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "thread_id": str(self.thread_id),
            "artifacts": [artifact.to_dict() for artifact in self._artifacts.values()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict, thread_id: UUID) -> "ArtifactRegistry":
        """
        Create registry from dictionary data.
        
        Args:
            data: Dictionary containing registry data
            thread_id: Thread ID for the registry
            
        Returns:
            New ArtifactRegistry instance
        """
        registry = cls(thread_id)
        
        for artifact_data in data.get("artifacts", []):
            artifact = Artifact.from_dict(artifact_data)
            registry.register(artifact)
        
        return registry
    
    def save_to_file(self, file_path: Path) -> None:
        """
        Save registry to JSON file.
        
        Args:
            file_path: Path to save the registry data
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved artifact registry to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save artifact registry: {e}")
            raise
    
    @classmethod
    def load_from_file(cls, file_path: Path, thread_id: UUID) -> "ArtifactRegistry":
        """
        Load registry from JSON file.
        
        Args:
            file_path: Path to load the registry data from
            thread_id: Thread ID for the registry
            
        Returns:
            Loaded ArtifactRegistry instance
        """
        try:
            if not file_path.exists():
                return cls(thread_id)  # Return empty registry if file doesn't exist
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            registry = cls.from_dict(data, thread_id)
            registry.logger.info(f"Loaded artifact registry from {file_path}")
            return registry
            
        except Exception as e:
            logging.error(f"Failed to load artifact registry from {file_path}: {e}")
            # Return empty registry on error
            return cls(thread_id)
    
    def __len__(self) -> int:
        """Return number of artifacts in registry."""
        return len(self._artifacts)
    
    def __contains__(self, artifact_id: str) -> bool:
        """Check if artifact ID exists in registry."""
        return artifact_id in self._artifacts
    
    def __iter__(self):
        """Iterate over artifacts in registry."""
        return iter(self._artifacts.values())