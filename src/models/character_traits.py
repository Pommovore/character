"""Modèles Pydantic pour l'API d'extraction de traits de caractère.

Ce module définit les modèles de données utilisés pour la validation des entrées et le formatage des réponses
dans l'API d'extraction de traits de caractère.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CharacterDescription(BaseModel):
    """Modèle d'entrée pour le texte de description du personnage."""

    text: str = Field(..., min_length=10, description="Texte de description du personnage à analyser")
    directive: Optional[str] = Field(None, description="Directive ou recommandation pour guider l'analyse")
    request_id: str = Field(..., description="Identifiant unique de la demande")
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
    request_id: str = Field(..., description="Identifiant unique de la demande")
    directive: Optional[str] = Field(None, description="Directive utilisée pour l'analyse")
    status: str = Field("completed", description="État du traitement (pending/completed)")

class CharacterProcessingStatus(BaseModel):
    """Modèle pour indiquer l'état du traitement d'une demande d'extraction."""
    
    request_id: str = Field(..., description="Identifiant unique de la demande")
    status: str = Field("pending", description="État du traitement (pending/completed)")
    message: str = Field("Traitement en cours", description="Message sur l'état du traitement")

class CharacterRequestId(BaseModel):
    """Modèle pour demander l'état d'un traitement via son ID."""
    
    request_id: str = Field(..., description="Identifiant unique de la demande")