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
    # Désactiver le worker pour les tests
    app = create_application(start_worker=False)
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


@patch("src.api.traits_endpoints.validate_api_token")
def test_extract_traits_endpoint(mock_validate, test_app):
    """Teste le point de terminaison d'extraction de traits."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    mock_validate.return_value = (MagicMock(email="test@example.com", id=1), MagicMock(id=1))
    
    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={
            "text": "Harry Potter est un jeune sorcier courageux.",
            "request_id": "test-req-001"
        },
        headers={"token": "test-token"}
    )
    
    # Vérification
    assert response.status_code == 202
    data = response.json()
    assert data["request_id"] == "test-req-001"
    assert data["status"] == "pending"


def test_extract_traits_unauthorized(test_app):
    """Teste le point de terminaison sans token d'autorisation."""
    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={
            "text": "Harry Potter est un jeune sorcier courageux.",
            "request_id": "test-req-unauth"
        }
    )
    
    # Vérification
    assert response.status_code == 401


@patch("src.api.traits_endpoints.validate_api_token")
def test_extract_traits_with_short_text(mock_validate, test_app):
    """Teste le point de terminaison d'extraction de traits avec un texte trop court."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    mock_validate.return_value = (MagicMock(email="test@example.com", id=1), MagicMock(id=1))
    
    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={"text": "Trop court"},
        headers={"token": "test-token"}
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


@patch("src.api.traits_endpoints.validate_api_token")
@patch("src.api.traits_endpoints.fetch_text_content")
@patch("src.api.traits_endpoints.is_url")
def test_extract_traits_with_url(mock_is_url, mock_fetch, mock_validate, test_app):
    """Teste l'extraction de traits lorsque le texte est une URL."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    mock_is_url.return_value = True
    mock_fetch.return_value = "Harry Potter est un jeune sorcier courageux et loyal."
    mock_validate.return_value = (MagicMock(email="test@example.com", id=1), MagicMock(id=1))

    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={
            "text": "https://example.com/character.txt",
            "request_id": "url-test-001"
        },
        headers={"token": "test-token"}
    )

    # Vérification
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    mock_fetch.assert_called_once_with("https://example.com/character.txt")


@patch("src.api.traits_endpoints.validate_api_token")
@patch("src.api.traits_endpoints.fetch_text_content")
@patch("src.api.traits_endpoints.is_url")
def test_extract_traits_with_invalid_url(mock_is_url, mock_fetch, mock_validate, test_app):
    """Teste le comportement lorsque le téléchargement de l'URL échoue."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    mock_is_url.return_value = True
    mock_fetch.side_effect = ValueError("Erreur HTTP 404 lors du téléchargement de l'URL.")
    mock_validate.return_value = (MagicMock(email="test@example.com", id=1), MagicMock(id=1))

    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={
            "text": "https://example.com/not-found",
            "request_id": "url-test-002"
        },
        headers={"token": "test-token"}
    )

    # Vérification
    assert response.status_code == 400
    data = response.json()
    assert "404" in data["detail"]


@patch("src.api.traits_endpoints.validate_api_token")
@patch("src.api.traits_endpoints.fetch_text_content")
@patch("src.api.traits_endpoints.is_url")
def test_extract_traits_normal_text_not_affected(mock_is_url, mock_fetch, mock_validate, test_app):
    """Vérifie que le texte normal n'est pas affecté par la détection d'URL."""
    # Préparation
    mock_get_extractor.return_value = mock_extractor
    mock_is_url.return_value = False
    mock_validate.return_value = (MagicMock(email="test@example.com", id=1), MagicMock(id=1))

    # Action
    response = test_app.post(
        "/api/v1/traits/extract",
        json={
            "text": "Harry Potter est un jeune sorcier courageux.",
            "request_id": "normal-test-001"
        },
        headers={"token": "test-token"}
    )

    # Vérification
    assert response.status_code == 202
    mock_fetch.assert_not_called()