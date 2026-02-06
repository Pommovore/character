"""
Traits extraction service using Hugging Face models.

This module provides functionality to extract character traits from text descriptions
using pre-trained transformer models from Hugging Face.
"""

import logging
from typing import Dict, List, Optional, Tuple

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import numpy as np

from src.models.character_traits import CharacterTrait

# Configure logging
logger = logging.getLogger(__name__)

# Pre-defined character trait categories and related traits
TRAIT_CATEGORIES = {
    "Personality": [
        "Courageous", "Ambitious", "Intelligent", "Compassionate", "Curious",
        "Loyal", "Independent", "Creative", "Responsible", "Optimistic",
        "Pessimistic", "Cautious", "Adventurous", "Introverted", "Extroverted"
    ],
    "Values": [
        "Honest", "Reliable", "Just", "Honorable", "Respectful",
        "Generous", "Selfish", "Materialistic", "Spiritual", "Traditional"
    ],
    "Emotions": [
        "Joyful", "Fearful", "Angry", "Melancholic", "Serene",
        "Anxious", "Passionate", "Apathetic", "Enthusiastic", "Jealous"
    ]
}


class TraitsExtractor:
    """Service for extracting character traits from text descriptions."""

    def __init__(self, model_name: str = "distilbert-base-uncased"):
        """
        Initialize the traits extractor with a specific model.

        Args:
            model_name: Hugging Face model name to use for extraction
        """
        self.model_name = model_name
        logger.info(f"Initializing TraitsExtractor with model: {model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # For demonstration, we use a text classification pipeline
            # In a real application, you'd use a more specific model or fine-tune one
            self.classifier = pipeline(
                "zero-shot-classification", 
                model=self.model_name,
                tokenizer=self.tokenizer
            )
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise

    def extract_traits(self, text: str) -> List[CharacterTrait]:
        """
        Extract character traits from the provided text description.

        Args:
            text: Character description text

        Returns:
            List of CharacterTrait objects with trait names and confidence scores
        """
        logger.info(f"Extracting traits from text of length: {len(text)}")
        
        all_traits = []
        for category, traits in TRAIT_CATEGORIES.items():
            try:
                # Use zero-shot classification to identify traits in this category
                result = self.classifier(text, traits, multi_label=True)
                
                # Process the results
                for trait, score in zip(result["labels"], result["scores"]):
                    # Only include traits with scores above threshold
                    if score > 0.3:  
                        all_traits.append(CharacterTrait(
                            trait=trait,
                            score=score,
                            category=category
                        ))
            except Exception as e:
                logger.error(f"Error extracting traits for category {category}: {str(e)}")
        
        # Sort by score (highest first)
        all_traits.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Extracted {len(all_traits)} traits with scores above threshold")
        
        return all_traits
    
    def generate_summary(self, traits: List[CharacterTrait]) -> str:
        """
        Generate a summary of the character based on the extracted traits.

        Args:
            traits: List of CharacterTrait objects

        Returns:
            Textual summary of the character's main traits
        """
        if not traits:
            return "No significant character traits were identified."
            
        # Take the top 5 traits or all if fewer
        top_traits = traits[:min(5, len(traits))]
        
        # Create the summary
        trait_phrases = [f"{t.trait} ({t.category})" for t in top_traits]
        traits_text = ", ".join(trait_phrases[:-1])
        if len(trait_phrases) > 1:
            traits_text += f" and {trait_phrases[-1]}"
        else:
            traits_text = trait_phrases[0]
            
        summary = f"This character is primarily characterized by {traits_text}."
        return summary