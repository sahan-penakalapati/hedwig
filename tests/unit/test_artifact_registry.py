"""
Unit tests for ArtifactRegistry.
"""

import pytest
from pathlib import Path
from uuid import uuid4
import tempfile
import json

from hedwig.core.artifact_registry import ArtifactRegistry
from hedwig.core.models import Artifact, ArtifactType


class TestArtifactRegistry:
    """Tests for ArtifactRegistry class."""
    
    def test_registry_creation(self):
        """Test creating an artifact registry."""
        thread_id = uuid4()
        registry = ArtifactRegistry(thread_id)
        
        assert registry.thread_id == thread_id
        assert not registry.has_artifacts()
        assert registry.count() == 0
    
    def test_register_artifact(self):
        """Test registering an artifact."""
        registry = ArtifactRegistry(uuid4())
        artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test file"
        )
        
        result = registry.register(artifact)
        
        assert result is True
        assert registry.has_artifacts()
        assert registry.count() == 1
        assert str(artifact.artifact_id) in registry
    
    def test_register_duplicate_artifact(self):
        """Test registering the same artifact twice."""
        registry = ArtifactRegistry(uuid4())
        artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test file"
        )
        
        first_result = registry.register(artifact)
        second_result = registry.register(artifact)
        
        assert first_result is True
        assert second_result is False  # Should fail on duplicate
        assert registry.count() == 1
    
    def test_get_by_id(self):
        """Test retrieving artifact by ID."""
        registry = ArtifactRegistry(uuid4())
        artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.CODE,
            description="Test code"
        )
        registry.register(artifact)
        
        retrieved = registry.get_by_id(str(artifact.artifact_id))
        
        assert retrieved == artifact
        assert retrieved.artifact_type == ArtifactType.CODE
    
    def test_get_by_path(self):
        """Test retrieving artifact by file path."""
        registry = ArtifactRegistry(uuid4())
        artifact = Artifact(
            file_path="test/script.py",
            artifact_type=ArtifactType.CODE,
            description="Python script"
        )
        registry.register(artifact)
        
        retrieved = registry.get_by_path("test/script.py")
        
        assert retrieved == artifact
    
    def test_get_by_type(self):
        """Test retrieving artifacts by type."""
        registry = ArtifactRegistry(uuid4())
        
        pdf_artifact = Artifact(
            file_path="doc.pdf",
            artifact_type=ArtifactType.PDF,
            description="PDF document"
        )
        code_artifact = Artifact(
            file_path="script.py",
            artifact_type=ArtifactType.CODE,
            description="Python script"
        )
        
        registry.register(pdf_artifact)
        registry.register(code_artifact)
        
        pdf_artifacts = registry.get_by_type(ArtifactType.PDF)
        code_artifacts = registry.get_by_type(ArtifactType.CODE)
        
        assert len(pdf_artifacts) == 1
        assert len(code_artifacts) == 1
        assert pdf_artifacts[0] == pdf_artifact
        assert code_artifacts[0] == code_artifact
    
    def test_auto_open_single_pdf(self):
        """Test auto-open logic for single PDF."""
        registry = ArtifactRegistry(uuid4())
        
        pdf_artifact = Artifact(
            file_path="report.pdf",
            artifact_type=ArtifactType.PDF,
            description="Report"
        )
        
        to_open = registry.get_auto_open_artifacts([pdf_artifact])
        
        assert len(to_open) == 1
        assert to_open[0] == pdf_artifact
    
    def test_auto_open_multiple_pdfs(self):
        """Test auto-open logic for multiple PDFs (should not auto-open)."""
        registry = ArtifactRegistry(uuid4())
        
        pdf1 = Artifact(
            file_path="report1.pdf",
            artifact_type=ArtifactType.PDF,
            description="Report 1"
        )
        pdf2 = Artifact(
            file_path="report2.pdf",
            artifact_type=ArtifactType.PDF,
            description="Report 2"
        )
        
        to_open = registry.get_auto_open_artifacts([pdf1, pdf2])
        
        assert len(to_open) == 0  # Multiple PDFs should not auto-open
    
    def test_auto_open_first_code(self):
        """Test auto-open logic for code files."""
        registry = ArtifactRegistry(uuid4())
        
        code1 = Artifact(
            file_path="script1.py",
            artifact_type=ArtifactType.CODE,
            description="First script"
        )
        code2 = Artifact(
            file_path="script2.py",
            artifact_type=ArtifactType.CODE,
            description="Second script"
        )
        
        to_open = registry.get_auto_open_artifacts([code1, code2])
        
        assert len(to_open) == 1
        assert to_open[0] == code1  # First code file should auto-open
    
    def test_auto_open_pdf_precedence(self):
        """Test that PDF auto-open takes precedence over code."""
        registry = ArtifactRegistry(uuid4())
        
        pdf_artifact = Artifact(
            file_path="report.pdf",
            artifact_type=ArtifactType.PDF,
            description="Report"
        )
        code_artifact = Artifact(
            file_path="script.py",
            artifact_type=ArtifactType.CODE,
            description="Script"
        )
        
        to_open = registry.get_auto_open_artifacts([pdf_artifact, code_artifact])
        
        assert len(to_open) == 1
        assert to_open[0] == pdf_artifact  # PDF should take precedence
    
    def test_artifacts_summary(self):
        """Test generating artifacts summary."""
        registry = ArtifactRegistry(uuid4())
        
        # Test empty registry
        summary = registry.get_artifacts_summary()
        assert "No artifacts available" in summary
        
        # Add artifacts
        pdf_artifact = Artifact(
            file_path="artifacts/report.pdf",
            artifact_type=ArtifactType.PDF,
            description="Test report"
        )
        code_artifact = Artifact(
            file_path="artifacts/script.py",
            artifact_type=ArtifactType.CODE,
            description="Python script"
        )
        
        registry.register(pdf_artifact)
        registry.register(code_artifact)
        
        summary = registry.get_artifacts_summary()
        
        assert "Available artifacts:" in summary
        assert "report.pdf" in summary
        assert "script.py" in summary
        assert "PDF" in summary
        assert "CODE" in summary
    
    def test_remove_artifact(self):
        """Test removing an artifact."""
        registry = ArtifactRegistry(uuid4())
        artifact = Artifact(
            file_path="test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Test file"
        )
        registry.register(artifact)
        
        # Verify it's there
        assert registry.count() == 1
        
        # Remove it
        result = registry.remove_artifact(str(artifact.artifact_id))
        
        assert result is True
        assert registry.count() == 0
        assert not registry.has_artifacts()
        assert str(artifact.artifact_id) not in registry
    
    def test_clear_registry(self):
        """Test clearing all artifacts."""
        registry = ArtifactRegistry(uuid4())
        
        # Add multiple artifacts
        for i in range(3):
            artifact = Artifact(
                file_path=f"test{i}.txt",
                artifact_type=ArtifactType.OTHER,
                description=f"Test file {i}"
            )
            registry.register(artifact)
        
        assert registry.count() == 3
        
        # Clear registry
        registry.clear()
        
        assert registry.count() == 0
        assert not registry.has_artifacts()
    
    def test_serialization(self):
        """Test registry serialization and deserialization."""
        thread_id = uuid4()
        registry = ArtifactRegistry(thread_id)
        
        # Add some artifacts
        artifact1 = Artifact(
            file_path="test1.txt",
            artifact_type=ArtifactType.CODE,
            description="Test code"
        )
        artifact2 = Artifact(
            file_path="test2.pdf",
            artifact_type=ArtifactType.PDF,
            description="Test document"
        )
        
        registry.register(artifact1)
        registry.register(artifact2)
        
        # Serialize to dict
        data = registry.to_dict()
        
        assert data["thread_id"] == str(thread_id)
        assert len(data["artifacts"]) == 2
        
        # Deserialize from dict
        new_registry = ArtifactRegistry.from_dict(data, thread_id)
        
        assert new_registry.thread_id == thread_id
        assert new_registry.count() == 2
        
        # Verify artifacts are correctly loaded
        loaded_artifact1 = new_registry.get_by_path("test1.txt")
        loaded_artifact2 = new_registry.get_by_path("test2.pdf")
        
        assert loaded_artifact1 is not None
        assert loaded_artifact2 is not None
        assert loaded_artifact1.artifact_type == ArtifactType.CODE
        assert loaded_artifact2.artifact_type == ArtifactType.PDF
    
    def test_file_persistence(self):
        """Test saving and loading registry from file."""
        thread_id = uuid4()
        registry = ArtifactRegistry(thread_id)
        
        # Add an artifact
        artifact = Artifact(
            file_path="persistent_test.txt",
            artifact_type=ArtifactType.OTHER,
            description="Persistence test"
        )
        registry.register(artifact)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = Path(f.name)
        
        try:
            registry.save_to_file(temp_file)
            
            # Load from file
            loaded_registry = ArtifactRegistry.load_from_file(temp_file, thread_id)
            
            assert loaded_registry.count() == 1
            loaded_artifact = loaded_registry.get_by_path("persistent_test.txt")
            assert loaded_artifact is not None
            assert loaded_artifact.description == "Persistence test"
            
        finally:
            temp_file.unlink()  # Clean up
    
    def test_iteration(self):
        """Test iterating over registry."""
        registry = ArtifactRegistry(uuid4())
        
        artifacts = []
        for i in range(3):
            artifact = Artifact(
                file_path=f"test{i}.txt",
                artifact_type=ArtifactType.OTHER,
                description=f"Test file {i}"
            )
            registry.register(artifact)
            artifacts.append(artifact)
        
        # Test iteration
        iterated_artifacts = list(registry)
        
        assert len(iterated_artifacts) == 3
        # Note: Order might not be preserved, so we check by ID
        iterated_ids = {str(a.artifact_id) for a in iterated_artifacts}
        expected_ids = {str(a.artifact_id) for a in artifacts}
        assert iterated_ids == expected_ids