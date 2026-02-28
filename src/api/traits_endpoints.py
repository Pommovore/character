
"""Points de terminaison API pour l'extraction de traits de caractère.

Ce module définit les points de terminaison FastAPI pour extraire les traits de caractère à partir de texte.
Les requêtes sont authentifiées par token API et soumises à une file d'attente FIFO.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.character_traits import (
    CharacterDescription,
    CharacterTraitsResponse,
    CharacterProcessingStatus,
)
from src.models.user import RequestLog
from src.services.auth_service import validate_api_token
from src.services.request_queue import RequestQueue, QueueItem
from src.utils.url_fetcher import is_url, fetch_text_content
from src.config import get_default_model

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du routeur avec préfixe versionné
router = APIRouter(prefix="/api/v1/traits", tags=["Traits de Caractère"])


@router.post("/extract", response_model=CharacterProcessingStatus, status_code=202)
async def extract_character_traits(
    request: Request,
    description: CharacterDescription,
    authorization: str = Header(None, alias="Authorization"),
    token: str = Header(None, alias="token"),
    webhook: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> CharacterProcessingStatus:
    """
    Lance l'extraction asynchrone des traits de caractère à partir du texte fourni.

    Requiert un token API valide dans le header 'token' ou 'Authorization: Bearer <token>'.
    Les requêtes sont soumises à une file d'attente FIFO et traitées dans l'ordre.
    Le header 'webhook' optionnel permet de définir une URL de rappel.

    Args:
        request: Requête HTTP FastApi
        description: Entrée de description du personnage avec identifiant
        authorization: Header Authorization avec le token API
        token: Header spécifique 'token' avec le token API
        webhook: Header contenant l'URL de notification (webhook)
        db: Session de base de données
    """
    # Priorité au header 'token' demandé par l'utilisateur
    auth_input = token or authorization
    
    # Valider le token API et vérifier le rate limit
    user, api_token = validate_api_token(auth_input, db)

    request_id = description.request_id
    logger.info(
        f"Requête d'extraction reçue — ID: {request_id}, "
        f"Utilisateur: {user.email}, Modèle: {description.model_name}"
    )

    # Si le texte est une URL, télécharger le contenu avant traitement
    text = description.text
    if is_url(text):
        logger.info(f"URL détectée dans le champ texte : {text}")
        try:
            text = await fetch_text_content(text)
            logger.info(f"Contenu téléchargé avec succès : {len(text)} caractères")
        except ValueError as e:
            logger.error(f"Échec du téléchargement du contenu de l'URL : {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    # Enregistrer le log de requête (rate limiting)
    request_log = RequestLog(
        user_id=user.id,
        token_id=api_token.id,
        request_id=request_id,
    )
    db.add(request_log)
    db.commit()

    # Gérer la surcharge si la requête est déjà connue
    queue = RequestQueue()
    existing = queue.get_request_status(request_id)
    if existing:
        if existing["status"] == "waiting":
            # Si elle est encore en attente, on la retire pour ne pas faire un double traitement inutile
            queue.remove_waiting_request(request_id)
            logger.info(f"Requête {request_id} existante en attente retirée pour surcharge.")
        else:
            # Si elle est en cours (processing) ou terminée (completed/failed),
            # le nouveau traitement écrasera l'ancien résultat une fois terminé.
            logger.info(f"Requête {request_id} va être surchargée (statut précédent: {existing['status']}).")

    # Détermination du modèle à utiliser
    # 1. Spécifié dans la requête API explicitement
    # 2. Modèle préféré de l'utilisateur en base
    # 3. Modèle par défaut de l'application
    model_name_to_use = description.model_name or user.preferred_model or get_default_model()
    
    # Construction de l'URL de résultat de façon robuste
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    root_path = request.scope.get("root_path", "")
    result_url = f"{scheme}://{host}{root_path}/api/v1/traits/get_character/{request_id}"
    
    if webhook:
        logger.info(f"Webhook configuré pour cette requête : {webhook}")
        
    # Ajouter à la file d'attente
    queue_item = QueueItem(
        request_id=request_id,
        user_id=user.id,
        user_email=user.email,
        text=text,
        directive=description.directive,
        model_name=model_name_to_use,
        webhook=webhook,
        result_url=result_url
    )
    position = queue.enqueue(queue_item)

    logger.info(f"Requête {request_id} ajoutée en file d'attente (position: {position})")

    return CharacterProcessingStatus(
        request_id=request_id,
        status="pending",
        message=f"Requête ajoutée en file d'attente (position: {position + 1})"
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

    queue = RequestQueue()
    status = queue.get_request_status(request_id)

    if not status:
        logger.warning(f"ID de requête inconnu: {request_id}")
        raise HTTPException(status_code=404, detail="inconnu")

    if status["status"] in ("waiting", "processing"):
        logger.info(f"Traitement en cours pour l'ID: {request_id}")
        raise HTTPException(status_code=202, detail="Traitement en cours")

    if status["status"] == "failed":
        logger.error(f"Traitement échoué pour l'ID: {request_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Le traitement a échoué : {status.get('error', 'erreur inconnue')}"
        )

    # Construire la réponse à partir du résultat
    result = status.get("result")
    if result is None:
        raise HTTPException(status_code=500, detail="Résultat introuvable")

    from src.models.character_traits import CharacterTrait

    traits = [CharacterTrait(**t) for t in result["traits"]]
    return CharacterTraitsResponse(
        traits=traits,
        summary=result.get("summary"),
        model_used=result.get("model_used"),
        validated_model=result.get("validated_model", True),
        request_id=request_id,
        status="completed",
    )