"""Tests pour le service TraitsExtractor.

Ce module contient des tests unitaires pour les fonctionnalités du service TraitsExtractor
utilisant le LLM (InferenceClient) au lieu des transformateurs locaux.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.traits_extractor import TraitsExtractor
from src.models.character_traits import CharacterTrait

@pytest.fixture
def mock_llm_response():
    """Fournit une fausse réponse JSON du LLM."""
    mock = MagicMock()
    mock.choices = [
        MagicMock(
            message=MagicMock(
                content='''
                {
                    "traits": [
                        {"trait": "Courageux", "score": 0.9, "category": "Personnalité"},
                        {"trait": "Loyal", "score": 0.8, "category": "Personnalité"}
                    ],
                    "summary": "Harry Potter est courageux et loyal."
                }
                '''
            )
        )
    ]
    return mock

@pytest.fixture
def sample_text():
    """Fournit un exemple de description de personnage pour les tests."""
    return "Harry Potter est un sorcier brave et loyal."

@patch("src.services.traits_extractor.InferenceClient")
def test_traits_extractor_initialization(mock_inference_client_class):
    """Teste que TraitsExtractor s'initialise correctement avec le bon modèle."""
    model_name = "test-llm-model"
    
    from unittest.mock import ANY
    extractor = TraitsExtractor(model_name)
    
    mock_inference_client_class.assert_called_once_with(model=model_name, token=ANY)
    assert extractor.model_name == model_name

@patch("src.services.traits_extractor.InferenceClient")
def test_extract_traits(mock_inference_client_class, mock_llm_response, sample_text):
    """Teste la fonctionnalité d'extraction de traits via LLM."""
    # Préparation
    mock_client_instance = mock_inference_client_class.return_value
    mock_client_instance.chat_completion.return_value = mock_llm_response
    
    extractor = TraitsExtractor("test-model")
    
    # Action
    traits, valid_model = extractor.extract_traits(sample_text)
    
    # Vérification
    assert valid_model is True
    assert len(traits) == 2
    assert traits[0].trait == "Courageux"
    assert traits[0].score == 0.9
    assert traits[0].category == "Personnalité"
    
    # Vérifie que chat_completion a été appelé
    mock_client_instance.chat_completion.assert_called_once()

@patch("src.services.traits_extractor.InferenceClient")
def test_generate_summary_from_llm(mock_inference_client_class, mock_llm_response, sample_text):
    """Teste la génération de résumé ou la récupération du résumé depuis les traits générés."""
    mock_client_instance = mock_inference_client_class.return_value
    mock_client_instance.chat_completion.return_value = mock_llm_response
    
    extractor = TraitsExtractor("test-model")
    
    # Extraire génèrera également le résumé en interne
    traits, _ = extractor.extract_traits(sample_text)
    
    # Le comportement de fallback generate_summary formaté
    summary = extractor.generate_summary(traits)
    assert "Courageux (Personnalité)" in summary
    assert "Loyal (Personnalité)" in summary