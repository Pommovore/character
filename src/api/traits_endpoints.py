
"""Points de terminaison API pour l'extraction de traits de caractère.

Ce module définit les points de terminaison FastAPI pour extraire les traits de caractère à partir de texte.
"""

import logging
from typing import Optional, Dict
import asyncio

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from fastapi.responses import JSONResponse

from src.models.character_traits import (
    CharacterDescription,
    CharacterTraitsResponse,
    CharacterProcessingStatus,
    CharacterRequestId
)
from src.services.traits_extractor import TraitsExtractor
from src.services.character_store import CharacterStore

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du routeur avec préfixe versionné
router = APIRouter(prefix="/api/v1/traits", tags=["Traits de Caractère"])

# Cache pour les instances TraitsExtractor afin d'éviter de recharger les modèles
extractors = {}

# Service de stockage des résultats
character_store = CharacterStore()


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


@router.post("/extract", response_model=CharacterProcessingStatus, status_code=202)
async def extract_character_traits(
    description: CharacterDescription,
    extractor: TraitsExtractor = Depends(get_extractor)
) -> CharacterProcessingStatus:
    """
    Lance l'extraction asynchrone des traits de caractère à partir du texte fourni.
    
    Args:
        description: Entrée de description du personnage avec identifiant
        extractor: Instance de TraitsExtractor (injectée par dépendance)
        
    Returns:
        État du traitement avec identifiant de la demande (HTTP 202 Accepted)
    """
    request_id = description.request_id
    logger.info(f"Reçu une requête d'extraction de traits avec ID: {request_id}, Modèle: {description.model_name}")
    
    # Vérifier si cette demande est déjà en cours de traitement ou terminée
    if character_store.is_request_known(request_id):
        if character_store.is_request_pending(request_id):
            return CharacterProcessingStatus(
                request_id=request_id,
                status="pending",
                message="Traitement déjà en cours pour cet ID de requête"
            )
        else:
            return CharacterProcessingStatus(
                request_id=request_id,
                status="completed",
                message="Résultat déjà disponible pour cet ID de requête"
            )
    
    # Fonction de traitement à exécuter de manière asynchrone
    def process_extraction():
        try:
            # Extraire les traits de la description
            traits = extractor.extract_traits(description.text, description.directive)
            
            # Générer un résumé basé sur les traits extraits
            summary = extractor.generate_summary(traits)
            
            # Créer la réponse
            return CharacterTraitsResponse(
                traits=traits,
                summary=summary,
                model_used=description.model_name,
                request_id=request_id,
                directive=description.directive,
                status="completed"
            )
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'extraction de traits : {str(e)}")
            # Dans une implémentation complète, nous stockerions l'erreur
            raise
    
    # Lancer le traitement asynchrone
    character_store.process_async(request_id, process_extraction)
    
    # Retourner immédiatement un statut
    return CharacterProcessingStatus(
        request_id=request_id,
        status="pending",
        message="Traitement lancé avec succès"
    )

@router.get("/get_character/{request_id}", response_model=CharacterTraitsResponse)
async def get_character_result(request_id: str):
    """
    Récupère le résultat d'une extraction de traits de caractère précédemment demandée.
    
    Args:
        request_id: Identifiant unique de la demande
        
    Returns:
        Résultat de l'extraction avec les traits de caractère
        
    Raises:
        HTTPException: Si l'ID n'est pas connu ou si le traitement est en cours
    """
    logger.info(f"Demande de récupération des résultats pour l'ID: {request_id}")
    
    # Vérifier si l'ID est connu
    if not character_store.is_request_known(request_id):
        logger.warning(f"ID de requête inconnu: {request_id}")
        raise HTTPException(status_code=404, detail="inconnu")
    
    # Vérifier si le traitement est terminé
    if character_store.is_request_pending(request_id):
        logger.info(f"Traitement en cours pour l'ID: {request_id}")
        raise HTTPException(status_code=202, detail="Traitement en cours")
    
    # Récupérer le résultat
    result = character_store.get_result(request_id)
    if result is None:
        # Cas théoriquement impossible si la vérification précédente est correcte
        logger.error(f"Résultat introuvable pour l'ID: {request_id} alors que le traitement est marqué comme terminé")
        raise HTTPException(status_code=500, detail="Erreur interne: résultat introuvable")
    
    logger.info(f"Résultat trouvé pour l'ID: {request_id}")
    return result