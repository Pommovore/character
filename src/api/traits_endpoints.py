"""
API endpoints for character traits extraction.

This module defines the FastAPI endpoints for extracting character traits from text.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.models.character_traits import (
    CharacterDescription, 
    CharacterTraitsResponse
)
from src.services.traits_extractor import TraitsExtractor

# Configure logging
logger = logging.getLogger(__name__)

# Create router with versioned prefix
router = APIRouter(prefix="/api/v1/traits", tags=["Character Traits"])

# Cache for TraitsExtractor instances to avoid reloading models
extractors = {}


def get_extractor(model_name: str = "distilbert-base-uncased") -> TraitsExtractor:
    """
    Factory function to get or create a TraitsExtractor instance.
    
    Args:
        model_name: Name of the Hugging Face model to use
        
    Returns:
        TraitsExtractor instance for the specified model
    """
    if model_name not in extractors:
        logger.info(f"Creating new extractor for model: {model_name}")
        try:
            extractors[model_name] = TraitsExtractor(model_name)
        except Exception as e:
            logger.error(f"Failed to create extractor for {model_name}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to load model {model_name}: {str(e)}"
            )
    
    return extractors[model_name]


@router.post("/extract", response_model=CharacterTraitsResponse)
async def extract_character_traits(
    description: CharacterDescription,
    extractor: TraitsExtractor = Depends(get_extractor)
) -> CharacterTraitsResponse:
    """
    Extract character traits from provided description text.
    
    Args:
        description: Character description input
        extractor: TraitsExtractor instance (injected by dependency)
        
    Returns:
        CharacterTraitsResponse with extracted traits and summary
    """
    logger.info(f"Received trait extraction request with model: {description.model_name}")
    
    try:
        # Extract traits from the description
        traits = extractor.extract_traits(description.text)
        
        # Generate a summary based on the extracted traits
        summary = extractor.generate_summary(traits)
        
        # Return the response
        return CharacterTraitsResponse(
            traits=traits,
            summary=summary,
            model_used=description.model_name
        )
        
    except Exception as e:
        logger.error(f"Error processing trait extraction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting character traits: {str(e)}"
        )