"""
Persistence system for chat threads and artifacts.

Handles saving and loading of thread state including conversation history,
artifacts, and metadata to ensure continuity across application restarts.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from hedwig.core.artifact_registry import ArtifactRegistry
from hedwig.core.exceptions import ErrorHandler, ValidationError
from hedwig.core.models import ChatThread, ConversationMessage


class ThreadPersistence:
    """
    Handles persistence of chat threads and their associated data.
    
    Each thread is stored in its own directory containing:
    - thread.json: Thread metadata and conversation history
    - artifacts.json: Artifact registry data  
    - artifacts/: Directory containing actual artifact files
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize thread persistence manager.
        
        Args:
            data_dir: Base directory for thread data (defaults to ~/.hedwig)
        """
        if data_dir is None:
            data_dir = Path.home() / '.hedwig'
        
        self.data_dir = Path(data_dir)
        self.threads_dir = self.data_dir / 'threads'
        self.threads_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler("ThreadPersistence")
    
    def get_thread_dir(self, thread_id: UUID) -> Path:
        """Get the directory path for a specific thread."""
        return self.threads_dir / str(thread_id)
    
    def get_thread_file(self, thread_id: UUID) -> Path:
        """Get the thread metadata file path."""
        return self.get_thread_dir(thread_id) / 'thread.json'
    
    def get_artifacts_file(self, thread_id: UUID) -> Path:
        """Get the artifacts registry file path."""
        return self.get_thread_dir(thread_id) / 'artifacts.json'
    
    def get_artifacts_dir(self, thread_id: UUID) -> Path:
        """Get the artifacts directory path."""
        return self.get_thread_dir(thread_id) / 'artifacts'
    
    def save_thread(self, thread: ChatThread, artifact_registry: ArtifactRegistry) -> None:
        """
        Save a complete chat thread and its artifacts.
        
        Args:
            thread: The chat thread to save
            artifact_registry: Associated artifact registry
        """
        try:
            thread_dir = self.get_thread_dir(thread.thread_id)
            thread_dir.mkdir(parents=True, exist_ok=True)
            
            # Create artifacts directory
            artifacts_dir = self.get_artifacts_dir(thread.thread_id)
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Save thread data
            thread_data = {
                "thread_id": str(thread.thread_id),
                "created_at": thread.created_at.isoformat(),
                "updated_at": thread.updated_at.isoformat(),
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "message_id": str(msg.message_id),
                        "metadata": msg.metadata
                    }
                    for msg in thread.messages
                ],
                "metadata": thread.metadata
            }
            
            thread_file = self.get_thread_file(thread.thread_id)
            with open(thread_file, 'w', encoding='utf-8') as f:
                json.dump(thread_data, f, indent=2, ensure_ascii=False)
            
            # Save artifact registry
            artifacts_file = self.get_artifacts_file(thread.thread_id)
            artifact_registry.save_to_file(artifacts_file)
            
            self.logger.info(f"Saved thread {thread.thread_id}")
            
        except Exception as e:
            error = self.error_handler.handle_exception(e, f"saving thread {thread.thread_id}")
            self.error_handler.log_and_raise(error)
    
    def load_thread(self, thread_id: UUID) -> tuple[ChatThread, ArtifactRegistry]:
        """
        Load a complete chat thread and its artifacts.
        
        Args:
            thread_id: ID of the thread to load
            
        Returns:
            Tuple of (ChatThread, ArtifactRegistry)
            
        Raises:
            ValidationError: If thread doesn't exist or data is invalid
        """
        try:
            thread_file = self.get_thread_file(thread_id)
            artifacts_file = self.get_artifacts_file(thread_id)
            
            if not thread_file.exists():
                raise ValidationError(f"Thread {thread_id} does not exist")
            
            # Load thread data
            with open(thread_file, 'r', encoding='utf-8') as f:
                thread_data = json.load(f)
            
            # Reconstruct thread
            thread = ChatThread(
                thread_id=UUID(thread_data["thread_id"]),
                created_at=datetime.fromisoformat(thread_data["created_at"]),
                updated_at=datetime.fromisoformat(thread_data["updated_at"]),
                metadata=thread_data.get("metadata", {})
            )
            
            # Reconstruct messages
            for msg_data in thread_data.get("messages", []):
                message = ConversationMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    message_id=UUID(msg_data["message_id"]),
                    metadata=msg_data.get("metadata", {})
                )
                thread.messages.append(message)
            
            # Load artifact registry
            artifact_registry = ArtifactRegistry.load_from_file(artifacts_file, thread_id)
            
            self.logger.info(f"Loaded thread {thread_id} with {len(thread.messages)} messages and {len(artifact_registry)} artifacts")
            return thread, artifact_registry
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            error = self.error_handler.handle_exception(e, f"loading thread {thread_id}")
            self.error_handler.log_and_raise(error)
    
    def thread_exists(self, thread_id: UUID) -> bool:
        """Check if a thread exists on disk."""
        return self.get_thread_file(thread_id).exists()
    
    def list_threads(self) -> List[Dict[str, str]]:
        """
        List all available threads with basic metadata.
        
        Returns:
            List of thread summaries with id, created_at, and message count
        """
        threads = []
        
        try:
            for thread_dir in self.threads_dir.iterdir():
                if not thread_dir.is_dir():
                    continue
                
                try:
                    thread_id = UUID(thread_dir.name)
                    thread_file = thread_dir / 'thread.json'
                    
                    if not thread_file.exists():
                        continue
                    
                    with open(thread_file, 'r', encoding='utf-8') as f:
                        thread_data = json.load(f)
                    
                    threads.append({
                        "thread_id": str(thread_id),
                        "created_at": thread_data.get("created_at", ""),
                        "updated_at": thread_data.get("updated_at", ""),
                        "message_count": len(thread_data.get("messages", [])),
                        "last_message": thread_data.get("messages", [{}])[-1].get("content", "")[:100] if thread_data.get("messages") else ""
                    })
                    
                except (ValueError, json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Skipping invalid thread directory {thread_dir}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error listing threads: {e}")
        
        # Sort by updated_at descending
        threads.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return threads
    
    def delete_thread(self, thread_id: UUID) -> bool:
        """
        Delete a thread and all its associated data.
        
        Args:
            thread_id: ID of the thread to delete
            
        Returns:
            True if deleted successfully, False if thread didn't exist
        """
        try:
            thread_dir = self.get_thread_dir(thread_id)
            
            if not thread_dir.exists():
                return False
            
            # Remove entire thread directory
            shutil.rmtree(thread_dir)
            self.logger.info(f"Deleted thread {thread_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting thread {thread_id}: {e}")
            return False
    
    def cleanup_old_threads(self, keep_days: int = 30) -> int:
        """
        Clean up threads older than specified days.
        
        Args:
            keep_days: Number of days to keep threads
            
        Returns:
            Number of threads deleted
        """
        if keep_days <= 0:
            return 0
        
        deleted_count = 0
        cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        try:
            for thread_dir in self.threads_dir.iterdir():
                if not thread_dir.is_dir():
                    continue
                
                try:
                    # Check modification time
                    if thread_dir.stat().st_mtime < cutoff_date:
                        thread_id = UUID(thread_dir.name)
                        if self.delete_thread(thread_id):
                            deleted_count += 1
                            
                except (ValueError, OSError) as e:
                    self.logger.warning(f"Error checking thread {thread_dir}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old threads")
        
        return deleted_count
    
    def export_thread(self, thread_id: UUID, export_path: Path) -> None:
        """
        Export a thread to a zip file.
        
        Args:
            thread_id: Thread to export
            export_path: Path for the export file
        """
        try:
            thread_dir = self.get_thread_dir(thread_id)
            
            if not thread_dir.exists():
                raise ValidationError(f"Thread {thread_id} does not exist")
            
            # Create zip archive
            shutil.make_archive(
                str(export_path.with_suffix('')),
                'zip',
                str(thread_dir.parent),
                str(thread_dir.name)
            )
            
            self.logger.info(f"Exported thread {thread_id} to {export_path}")
            
        except Exception as e:
            error = self.error_handler.handle_exception(e, f"exporting thread {thread_id}")
            self.error_handler.log_and_raise(error)