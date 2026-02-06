"""
Tests for the TraitsExtractor service.

This module contains unit tests for the TraitsExtractor service functionality.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.traits_extractor import TraitsExtractor
from src.models.character_traits import CharacterTrait


@pytest.fixture
def mock_classifier():
    """Create a mock classifier for testing."""
    mock = MagicMock()
    mock.return_value = {
        "labels": ["Courageous", "Intelligent", "Loyal"],
        "scores": [0.9, 0.8, 0.7],
    }
    return mock


@pytest.fixture
def sample_text():
    """Provide a sample character description for tests."""
    return """
    Harry Potter is a brave and loyal young wizard who consistently shows courage
    in the face of danger. Despite his difficult upbringing with the Dursleys, he
    maintains a strong moral compass and values friendship above all else.
    """


@patch("transformers.AutoTokenizer.from_pretrained")
@patch("transformers.AutoModelForSequenceClassification.from_pretrained")
@patch("transformers.pipeline")
def test_traits_extractor_initialization(
    mock_pipeline, mock_model, mock_tokenizer
):
    """Test that TraitsExtractor initializes correctly with the right model."""
    # Arrange
    model_name = "test-model"
    mock_pipeline.return_value = MagicMock()
    
    # Act
    extractor = TraitsExtractor(model_name)
    
    # Assert
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
    """Test the trait extraction functionality."""
    # Arrange
    model_name = "test-model"
    mock_pipeline.return_value = mock_classifier
    extractor = TraitsExtractor(model_name)
    
    # Act
    traits = extractor.extract_traits(sample_text)
    
    # Assert
    assert len(traits) > 0
    assert isinstance(traits[0], CharacterTrait)
    assert traits[0].trait == "Courageous"
    assert traits[0].score == 0.9
    assert "Personality" in [t.category for t in traits]


@patch("transformers.AutoTokenizer.from_pretrained")
@patch("transformers.AutoModelForSequenceClassification.from_pretrained")
@patch("transformers.pipeline")
def test_generate_summary(
    mock_pipeline, mock_model, mock_tokenizer
):
    """Test the summary generation from traits."""
    # Arrange
    model_name = "test-model"
    mock_pipeline.return_value = MagicMock()
    extractor = TraitsExtractor(model_name)
    
    traits = [
        CharacterTrait(trait="Courageous", score=0.9, category="Personality"),
        CharacterTrait(trait="Intelligent", score=0.8, category="Personality"),
        CharacterTrait(trait="Loyal", score=0.7, category="Personality"),
    ]
    
    # Act
    summary = extractor.generate_summary(traits)
    
    # Assert
    assert summary is not None
    assert "Courageous (Personality)" in summary
    assert "Intelligent (Personality)" in summary
    assert "Loyal (Personality)" in summary