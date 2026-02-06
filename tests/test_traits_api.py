"""Tests pour les points de terminaison de l'API de traits de caractère.

Ce module contient des tests pour les points de terminaison de l'API afin de vérifier leur bon comportement.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.api.api import create_application
from src.models.character_traits import CharacterTrait


@pytest.fixture
def test_app():
    """Crée un client de test pour l'application FastAPI."""
    app = create_application()
    client = TestClient(app)
    return client


@pytest.fixture
def mock_extractor():
    """Crée un mock TraitsExtractor pour les tests API."""
    mock = MagicMock()
    mock.extract_traits.return_value = [
        CharacterTrait(trait="Courageux", score=0.9, category="Personnalité"),
        CharacterTrait(trait="Intelligent", score=0.8, category="Personnalité"),
    ]
    mock.generate_summary.return_value = "Ce personnage est principalement caractérisé par Courageux (Personnalité) et Intelligent (Personnalité)."
    return mock


@patch("src.api.traits_endpoints.get_extractor")
def test_extract_traits_endpoint(mock_get_extractor, mock_extractor, test_app):
    """Teste le point de terminaison d'extraction de traits."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    
    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={"text": "Harry Potter est un jeune sorcier courageux."}
    )
    
    # Vérification
    assert response.status_code == 200
    data = response.json()
    assert len(data["traits"]) == 2
    assert data["traits"][0]["trait"] == "Courageux"
    assert data["traits"][0]["score"] == 0.9
    assert data["summary"] is not None
    assert "Courageux" in data["summary"]


@patch("src.api.traits_endpoints.get_extractor")
def test_extract_traits_with_short_text(mock_get_extractor, mock_extractor, test_app):
    """Teste le point de terminaison d'extraction de traits avec un texte trop court."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    
    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={"text": "Trop court"}
    )
    
    # Vérification
    assert response.status_code == 422  # Erreur de validation


def test_health_endpoint(test_app):
    """Teste le point de terminaison de vérification de santé."""
    # Action
    response = test_app.get("/health")
    
    # Vérification
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "en bonne santé"
    assert "version" in data