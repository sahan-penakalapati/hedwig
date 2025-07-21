"""
Hedwig: Multi-Agent Task Execution System

A local desktop application that orchestrates specialist agents to handle
various tasks including document generation, web research, code creation,
and terminal command automation.
"""

__version__ = "0.1.0"
__author__ = "Hedwig Development Team"

from hedwig.core.models import TaskInput, TaskOutput, ToolOutput, Artifact
from hedwig.core.artifact_registry import ArtifactRegistry

__all__ = [
    "TaskInput",
    "TaskOutput", 
    "ToolOutput",
    "Artifact",
    "ArtifactRegistry",
]