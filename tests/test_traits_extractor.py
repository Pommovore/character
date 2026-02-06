"""Tests pour le service TraitsExtractor.

Ce module contient des tests unitaires pour les fonctionnalités du service TraitsExtractor.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.traits_extractor import TraitsExtractor
from src.models.character_traits import CharacterTrait


@pytest.fixture
def mock_classifier():
    """Crée un classifier mock pour les tests."""
    mock = MagicMock()
    mock.return_value = {
        "labels": ["Courageux", "Intelligent", "Loyal"],
        "scores": [0.9, 0.8, 0.7],
    }
    return mock


@pytest.fixture
def sample_text():
    """Fournit un exemple de description de personnage pour les tests."""
    return """
    Harry Potter est un jeune sorcier brave et loyal qui fait constamment preuve de courage
    face au danger. Malgré son éducation difficile chez les Dursley, il
    maintient une forte boussole morale et valorise l'amitié par-dessus tout.
    """


@patch("transformers.AutoTokenizer.from_pretrained")
@patch("transformers.AutoModelForSequenceClassification.from_pretrained")
@patch("transformers.pipeline")
def test_traits_extractor_initialization(
    mock_pipeline, mock_model, mock_tokenizer
):
    """Teste que TraitsExtractor s'initialise correctement avec le bon modèle."""
    # Préparation
    model_name = "test-model"
    mock_pipeline.return_value = MagicMock()
    
    # Action
    extractor = TraitsExtractor(model_name)
    
    # Vérification
    mock_tokenizer.assert_called_once_with(model_name)
    mock_model.assert_called_once_with(model_name)
    mock_pipeline.assert_called_once()
    assert extractor.model_name == model_name


@patch("transformers.AutoTokenizer.from_pretrained")
@patch("transformers.AutoModelForSequenceClassification.from_pretrained")
@patch("transformers.pipeline")
def test_extract_traits(
    mock_pipeline, mock_model, mock_tokenizer, mock_classifier, sample_text
):
    """Teste la fonctionnalité d'extraction de traits."""
    # Préparation
    model_name = "test-model"
    mock_pipeline.return_value = mock_classifier
    extractor = TraitsExtractor(model_name)
    
    # Action
    traits = extractor.extract_traits(sample_text)
    
    # Vérification
    assert len(traits) > 0
    assert isinstance(traits[0], CharacterTrait)
    assert traits[0].trait == "Courageux"
    assert traits[0].score == 0.9
    assert "Personnalité" in [t.category for t in traits]


@patch("transformers.AutoTokenizer.from_pretrained")
@patch("transformers.AutoModelForSequenceClassification.from_pretrained")
@patch("transformers.pipeline")
def test_generate_summary(
    mock_pipeline, mock_model, mock_tokenizer
):
    """Teste la génération de résumé à partir des traits."""
    # Préparation
    model_name = "test-model"
    mock_pipeline.return_value = MagicMock()
    extractor = TraitsExtractor(model_name)
    
    traits = [
        CharacterTrait(trait="Courageux", score=0.9, category="Personnalité"),
        CharacterTrait(trait="Intelligent", score=0.8, category="Personnalité"),
        CharacterTrait(trait="Loyal", score=0.7, category="Personnalité"),
    ]
    
    # Action
    summary = extractor.generate_summary(traits)
    
    # Vérification
    assert summary is not None
    assert "Courageux (Personnalité)" in summary
    assert "Intelligent (Personnalité)" in summary
    assert "Loyal (Personnalité)" in summary