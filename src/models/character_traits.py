"""
Pydantic models for character traits extraction API.

This module defines the data models used for input validation and response formatting
in the character traits extraction API.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CharacterDescription(BaseModel):
    """Input model for character description text."""

    text: str = Field(..., min_length=10, description="Character description text to analyze")
    model_name: Optional[str] = Field(
        "distilbert-base-uncased",
        description="Hugging Face model to use for trait extraction"
    )


class CharacterTrait(BaseModel):
    """Model representing a single character trait with confidence score."""

    trait: str = Field(..., description="Name of the character trait")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this trait")
    category: Optional[str] = Field(None, description="Category of the trait (e.g., 'Personality', 'Values')")


class CharacterTraitsResponse(BaseModel):
    """Response model containing extracted character traits."""

    traits: List[CharacterTrait] = Field(..., description="List of extracted character traits")
    summary: Optional[str] = Field(None, description="Summary of the character's main traits")
    model_used: str = Field(..., description="Name of the model used for extraction")