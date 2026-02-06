"""
Tests for the Character Traits API endpoints.

This module contains tests for the API endpoints to verify correct behavior.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.api.api import create_application
from src.models.character_traits import CharacterTrait


@pytest.fixture
def test_app():
    """Create a test client for the FastAPI app."""
    app = create_application()
    client = TestClient(app)
    return client


@pytest.fixture
def mock_extractor():
    """Create a mock TraitsExtractor for API tests."""
    mock = MagicMock()
    mock.extract_traits.return_value = [
        CharacterTrait(trait="Courageous", score=0.9, category="Personality"),
        CharacterTrait(trait="Intelligent", score=0.8, category="Personality"),
    ]
    mock.generate_summary.return_value = "This character is primarily characterized by Courageous (Personality) and Intelligent (Personality)."
    return mock


@patch("src.api.traits_endpoints.get_extractor")
def test_extract_traits_endpoint(mock_get_extractor, mock_extractor, test_app):
    """Test the traits extraction endpoint."""
    # Arrange
    mock_get_extractor.return_value = mock_extractor
    
    # Act
    response = test_app.post(
        "/api/v1/traits/extract",
        json={"text": "Harry Potter is a brave young wizard."}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["traits"]) == 2
    assert data["traits"][0]["trait"] == "Courageous"
    assert data["traits"][0]["score"] == 0.9
    assert data["summary"] is not None
    assert "Courageous" in data["summary"]


@patch("src.api.traits_endpoints.get_extractor")
def test_extract_traits_with_short_text(mock_get_extractor, mock_extractor, test_app):
    """Test the traits extraction endpoint with text that's too short."""
    # Arrange
    mock_get_extractor.return_value = mock_extractor
    
    # Act
    response = test_app.post(
        "/api/v1/traits/extract",
        json={"text": "Too short"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_health_endpoint(test_app):
    """Test the health check endpoint."""
    # Act
    response = test_app.get("/health")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data