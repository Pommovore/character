
"""Points de terminaison API pour l'extraction de traits de caractère.

Ce module définit les points de terminaison FastAPI pour extraire les traits de caractère à partir de texte.
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

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du routeur avec préfixe versionné
router = APIRouter(prefix="/api/v1/traits", tags=["Traits de Caractère"])

# Cache pour les instances TraitsExtractor afin d'éviter de recharger les modèles
extractors = {}


def get_extractor(model_name: str = "distilbert-base-uncased") -> TraitsExtractor:
    """
    Fonction factory pour obtenir ou créer une instance de TraitsExtractor.
    
    Args:
        model_name: Nom du modèle Hugging Face à utiliser
        
    Returns:
        Instance de TraitsExtractor pour le modèle spécifié
    """
    if model_name not in extractors:
        logger.info(f"Création d'un nouvel extracteur pour le modèle : {model_name}")
        try:
            extractors[model_name] = TraitsExtractor(model_name)
        except Exception as e:
            logger.error(f"Échec de création de l'extracteur pour {model_name} : {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Échec du chargement du modèle {model_name} : {str(e)}"
            )
    
    return extractors[model_name]


@router.post("/extract", response_model=CharacterTraitsResponse)
async def extract_character_traits(
    description: CharacterDescription,
    extractor: TraitsExtractor = Depends(get_extractor)
) -> CharacterTraitsResponse:
    """
    Extrait les traits de caractère à partir du texte de description fourni.
    
    Args:
        description: Entrée de description du personnage
        extractor: Instance de TraitsExtractor (injectée par dépendance)
        
    Returns:
        CharacterTraitsResponse avec traits extraits et résumé
    """
    logger.info(f"Reçu une requête d'extraction de traits avec le modèle : {description.model_name}")
    
    try:
        # Extraire les traits de la description
        traits = extractor.extract_traits(description.text)
        
        # Générer un résumé basé sur les traits extraits
        summary = extractor.generate_summary(traits)
        
        # Retourner la réponse
        return CharacterTraitsResponse(
            traits=traits,
            summary=summary,
            model_used=description.model_name
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'extraction de traits : {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'extraction des traits de caractère : {str(e)}"
        )