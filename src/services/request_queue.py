"""Service de file d'attente globale FIFO pour le traitement des requêtes.

Ce module gère une file d'attente unique qui traite les requêtes
d'extraction de traits une par une, dans l'ordre d'arrivée.
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from enum import Enum

from src.utils.path_utils import sanitize_email

# Configuration du logging
logger = logging.getLogger(__name__)


class QueueItemStatus(str, Enum):
    """États possibles d'un élément dans la file d'attente."""
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueItem:
    """Représente un élément dans la file d'attente de traitement."""
    request_id: str
    user_id: int
    user_email: str
    text: str
    directive: Optional[str] = None
    model_name: str = "Qwen/Qwen2.5-72B-Instruct"
    status: QueueItemStatus = QueueItemStatus.WAITING
    position: int = 0
    result: Any = None
    error: Optional[str] = None
    webhook: Optional[str] = None
    result_url: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class RequestQueue:
    """File d'attente FIFO globale pour le traitement séquentiel des requêtes."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implémentation du pattern Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RequestQueue, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def _initialize(self):
        """Initialisation des attributs du singleton."""
        if self._initialized:
            return
        self._queue: List[QueueItem] = []
        self._processing: Optional[QueueItem] = None
        self._process_func: Optional[Callable] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._queue_lock = threading.Lock()
        self._initialized = True
        logger.info("File d'attente des requêtes initialisée")

    def start_worker(self, process_func: Callable):
        """
        Démarre le worker qui traite la file d'attente.

        Args:
            process_func: Fonction de traitement (text, directive, model_name) -> result
        """
        self._initialize()
        self._process_func = process_func
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Worker de traitement démarré")

    def stop_worker(self):
        """Arrête le worker de traitement."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            logger.info("Worker de traitement arrêté")

    def _worker_loop(self):
        """Boucle principale du worker : traite un élément à la fois."""
        while not self._stop_event.is_set():
            item = self._dequeue()
            if item is None:
                time.sleep(0.5)  # Attendre avant de vérifier à nouveau
                continue

            # Marquer comme en cours de traitement
            with self._queue_lock:
                item.status = QueueItemStatus.PROCESSING
                self._processing = item

            logger.info(f"Traitement de la requête {item.request_id} (utilisateur: {item.user_email})")

            try:
                if self._process_func:
                    result = self._process_func(item.text, item.directive, item.model_name)
                    item.result = result
                    item.status = QueueItemStatus.COMPLETED
                    logger.info(f"Requête {item.request_id} traitée avec succès")
                    
                    
                    # Sauvegarder le résultat OU l'erreur en base de données
                    self._persist_to_db(item)
                else:
                    item.status = QueueItemStatus.FAILED
                    item.error = "Aucune fonction de traitement configurée"
                    logger.error("Pas de fonction de traitement configurée")
                    self._persist_to_db(item)
            except Exception as e:
                item.status = QueueItemStatus.FAILED
                item.error = str(e)
                logger.error(f"Erreur lors du traitement de {item.request_id} : {str(e)}")
                self._persist_to_db(item)
            finally:
                with self._queue_lock:
                    self._processing = None
                    # Mettre à jour les positions (l'élément est libéré de la mémoire RAM de la file)
                    self._update_positions()

                # Notifier le webhook si configuré
                if item.webhook:
                    self._notify_webhook(item)

    def _notify_webhook(self, item: QueueItem):
        """Envoie une requête POST au webhook configuré avec le résultat du traitement."""
        if not item.webhook:
            return

        is_discord = "discord.com/api/webhooks" in item.webhook

        # Format générique
        payload = {
            "request_id": item.request_id,
            "status": item.status.value,
            "user_email": item.user_email,
        }

        if item.status == QueueItemStatus.COMPLETED:
            payload["result_url"] = item.result_url
        else:
            payload["error"] = item.error

        # Format spécifique pour Discord
        if is_discord:
            color = 65280 if item.status == QueueItemStatus.COMPLETED else 16711680 # Vert ou Rouge
            title = "✅ Extraction Terminée" if item.status == QueueItemStatus.COMPLETED else "❌ Échec de l'Extraction"
            desc = f"**ID** : `{item.request_id}`\n**Utilisateur** : `{item.user_email}`"
            
            if item.status == QueueItemStatus.COMPLETED:
                desc += f"\n**Résultat** : [Télécharger le JSON]({item.result_url})"
            else:
                desc += f"\n**Erreur** : {item.error}"

            payload = {
                "embeds": [{
                    "title": title,
                    "description": desc,
                    "color": color
                }]
            }

        def perform_request():
            import httpx
            try:
                # Fire-and-forget: on utilise le client synchrone pour la simplicité dans ce thread
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(item.webhook, json=payload)
                    response.raise_for_status()
                    logger.info(f"Webhook notifié avec succès pour {item.request_id} ({response.status_code})")
            except Exception as e:
                logger.error(f"Échec de la notification webhook pour {item.request_id} : {str(e)}")

        # Exécuter dans un thread séparé pour ne pas bloquer la boucle principale
        threading.Thread(target=perform_request, daemon=True).start()

    def _persist_to_db(self, item: QueueItem):
        """
        Sauvegarde le résultat de la requête (succès ou échec) en base de données.
        """
        from src.database import SessionLocal
        from src.models.extraction_result import ExtractionResult
        
        db = SessionLocal()
        try:
            # Sérialisation du résultat si c'est un dict ou une liste
            result_data = None
            if item.result is not None:
                # Si c'est un objet (ex: CharacterTraitsResponse Pydantic), on le cast en dict
                if hasattr(item.result, "model_dump"):
                    result_data = item.result.model_dump()
                elif hasattr(item.result, "dict"):
                    result_data = item.result.dict()
                else:
                    result_data = item.result

            db_result = ExtractionResult(
                request_id=item.request_id,
                user_id=item.user_id,
                user_email=item.user_email,
                status=item.status.value,
                result_json=result_data,
                error_message=item.error,
            )
            db.add(db_result)
            db.commit()
            logger.info(f"Résultat pour {item.request_id} ({item.status.value}) sauvegardé en BDD")
        except Exception as e:
            db.rollback()
            logger.error(f"Échec de la sauvegarde DB pour {item.request_id} : {str(e)}")
        finally:
            db.close()

    def enqueue(self, item: QueueItem) -> int:
        """
        Ajoute un élément à la file d'attente.

        Args:
            item: Élément à ajouter

        Returns:
            Position dans la file d'attente
        """
        self._initialize()
        with self._queue_lock:
            item.position = len(self._queue) + (1 if self._processing else 0)
            self._queue.append(item)
            logger.info(f"Requête {item.request_id} ajoutée en position {item.position}")
            return item.position

    def _dequeue(self) -> Optional[QueueItem]:
        """Retire et retourne le prochain élément de la file."""
        with self._queue_lock:
            if self._queue:
                return self._queue.pop(0)
            return None

    def _update_positions(self):
        """Met à jour les positions de tous les éléments dans la file."""
        offset = 1 if self._processing else 0
        for i, item in enumerate(self._queue):
            item.position = i + offset

    def remove_waiting_request(self, request_id: str) -> bool:
        """
        Retire une requête de la file d'attente si elle n'a pas encore commencé.
        Utile pour surcharger/écraser une requête existante.
        
        Args:
            request_id: Identifiant de la requête
            
        Returns:
            True si l'élément a été trouvé et retiré, False sinon.
        """
        self._initialize()
        with self._queue_lock:
            for i, item in enumerate(self._queue):
                if item.request_id == request_id:
                    self._queue.pop(i)
                    self._update_positions()
                    logger.info(f"Requête {request_id} retirée de la file d'attente (surcharge)")
                    return True
            return False

    def get_queue_status(self, user_id: Optional[int] = None) -> dict:
        """
        Récupère l'état actuel de la file d'attente.

        Args:
            user_id: Si fourni, filtre sur cet utilisateur uniquement

        Returns:
            Dictionnaire avec l'état de la file
        """
        self._initialize()
        with self._queue_lock:
            queue_items = []
            for item in self._queue:
                if user_id is None or item.user_id == user_id:
                    queue_items.append({
                        "request_id": item.request_id,
                        "user_email": item.user_email,
                        "status": item.status.value,
                        "position": item.position,
                    })

            processing = None
            if self._processing and self._processing.status == QueueItemStatus.PROCESSING:
                if user_id is None or self._processing.user_id == user_id:
                    processing = {
                        "request_id": self._processing.request_id,
                        "user_email": self._processing.user_email,
                        "status": self._processing.status.value,
                    }

            return {
                "queue_length": len(self._queue),
                "processing": processing,
                "items": queue_items,
            }

    def get_request_status(self, request_id: str) -> Optional[dict]:
        """
        Récupère le statut d'une requête spécifique.

        Args:
            request_id: Identifiant de la requête

        Returns:
            Dictionnaire avec le statut ou None
        """
        self._initialize()
        with self._queue_lock:
            # Vérifier si c'est en cours de traitement
            if self._processing and self._processing.request_id == request_id:
                return {
                    "request_id": request_id,
                    "status": QueueItemStatus.PROCESSING.value,
                    "position": 0,
                }

            # Vérifier dans la file d'attente
            for item in self._queue:
                if item.request_id == request_id:
                    return {
                        "request_id": request_id,
                        "status": item.status.value,
                        "position": item.position,
                    }

            # Si pas trouvé en file, vérifier en base de données
            from src.database import SessionLocal
            from src.models.extraction_result import ExtractionResult
            
            db = SessionLocal()
            try:
                result_item = db.query(ExtractionResult).filter(ExtractionResult.request_id == request_id).first()
                if result_item:
                    return {
                        "request_id": request_id,
                        "status": result_item.status,
                        "result": result_item.result_json,
                        "error": result_item.error_message,
                    }
            finally:
                db.close()

        return None

    def get_result(self, request_id: str) -> Optional[Any]:
        """
        Récupère le résultat d'une requête terminée.

        Args:
            request_id: Identifiant de la requête

        Returns:
            Résultat ou None
        """
        self._initialize()
        status = self.get_request_status(request_id)
        if status and status.get("status") == QueueItemStatus.COMPLETED.value:
            return status.get("result")
        return None

    def get_user_recent_items(self, user_id: int, limit: int = 20) -> List[dict]:
        """
        Récupère les éléments récents d'un utilisateur (en file + terminés).
        Garantit l'absence de doublons par request_id.

        Args:
            user_id: Identifiant de l'utilisateur
            limit: Nombre maximum d'éléments

        Returns:
            Liste de dictionnaires décrivant les éléments
        """
        self._initialize()
        # Utiliser un dictionnaire pour éviter les doublons par request_id
        items_dict = {}

        # 1. Récupérer l'historique complet depuis la base de données
        from src.database import SessionLocal
        from src.models.extraction_result import ExtractionResult
        
        db = SessionLocal()
        try:
            # 20 résultats les plus récents en BDD
            db_results = (db.query(ExtractionResult)
                          .filter(ExtractionResult.user_id == user_id)
                          .order_by(ExtractionResult.created_at.desc())
                          .limit(limit)
                          .all())
            
            for db_res in db_results:
                items_dict[db_res.request_id] = {
                    "request_id": db_res.request_id,
                    "status": db_res.status,
                    "position": -1,
                    "created_at": db_res.created_at.timestamp(),
                    "error": db_res.error_message,
                }
        finally:
            db.close()

        with self._queue_lock:
            # 2. Éléments en file d'attente (écrase la vue BDD s'il y a relance)
            for item in self._queue:
                if item.user_id == user_id:
                    items_dict[item.request_id] = {
                        "request_id": item.request_id,
                        "status": item.status.value,
                        "position": item.position,
                        "created_at": item.created_at,
                    }

            # 3. Élément en cours de traitement (prioritaire pour l'affichage en cours)
            if self._processing and self._processing.user_id == user_id and self._processing.status == QueueItemStatus.PROCESSING:
                items_dict[self._processing.request_id] = {
                    "request_id": self._processing.request_id,
                    "status": self._processing.status.value,
                    "position": 0,
                    "created_at": self._processing.created_at,
                }

        # Convertir en liste, trier par date et limiter
        items = list(items_dict.values())
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[:limit]
