"""Modèles Pydantic pour l'API d'extraction de traits de caractère.

Ce module définit les modèles de données utilisés pour la validation des entrées et le formatage des réponses
dans l'API d'extraction de traits de caractère.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CharacterDescription(BaseModel):
    """Modèle d'entrée pour le texte de description du personnage."""

    text: str = Field(..., min_length=10, description="Texte de description du personnage à analyser")
    model_name: Optional[str] = Field(
        "distilbert-base-uncased",
        description="Modèle Hugging Face à utiliser pour l'extraction de traits"
    )


class CharacterTrait(BaseModel):
    """Modèle représentant un seul trait de caractère avec score de confiance."""

    trait: str = Field(..., description="Nom du trait de caractère")
    score: float = Field(..., ge=0.0, le=1.0, description="Score de confiance pour ce trait")
    category: Optional[str] = Field(None, description="Catégorie du trait (ex: 'Personnalité', 'Valeurs')")


class CharacterTraitsResponse(BaseModel):
    """Modèle de réponse contenant les traits de caractère extraits."""

    traits: List[CharacterTrait] = Field(..., description="Liste des traits de caractère extraits")
    summary: Optional[str] = Field(None, description="Résumé des principaux traits du personnage")
    model_used: str = Field(..., description="Nom du modèle utilisé pour l'extraction")