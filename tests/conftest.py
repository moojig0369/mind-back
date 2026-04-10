"""
Test configuration and fixtures for Journal and Graph tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, List, Any


@pytest.fixture
def mock_journal_data() -> Dict[str, Any]:
    """Sample journal data for testing."""
    return {
        "id": "test-journal-1",
        "title": "Test Journal Entry",
        "content": "This is a test entry",
        "status": "draft",
        "parent_id": None,
        "children": [],
        "metadata": {
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def mock_graph_structure() -> Dict[str, Any]:
    """Sample graph structure for testing."""
    return {
        "nodes": [
            {"id": "node-1", "label": "Root", "type": "journal"},
            {"id": "node-2", "label": "Child 1", "type": "journal"},
            {"id": "node-3", "label": "Child 2", "type": "journal"},
        ],
        "edges": [
            {"source": "node-1", "target": "node-2", "relation": "parent"},
            {"source": "node-1", "target": "node-3", "relation": "parent"},
        ]
    }


@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.save = AsyncMock()
    repo.delete = AsyncMock()
    repo.find_children = AsyncMock()
    repo.find_parent = AsyncMock()
    return repo


@pytest.fixture
def sample_journal_tree() -> Dict[str, Any]:
    """Sample journal tree structure."""
    return {
        "id": "root",
        "title": "Root Journal",
        "children": [
            {
                "id": "child-1",
                "title": "First Child",
                "children": [
                    {
                        "id": "grandchild-1",
                        "title": "Grandchild 1",
                        "children": []
                    }
                ]
            },
            {
                "id": "child-2",
                "title": "Second Child",
                "children": []
            }
        ]
    }
