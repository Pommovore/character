"""Service de file d'attente globale FIFO pour le traitement des requêtes.

Ce module gère une file d'attente unique qui traite les requêtes
d'extraction de traits une par une, dans l'ordre d'arrivée.
"""

import asyncio
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
    model_name: str = "distilbert-base-uncased"
    status: QueueItemStatus = QueueItemStatus.WAITING
    position: int = 0
    result: Any = None
    error: Optional[str] = None
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
        self._results: Dict[str, QueueItem] = {}
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
                    
                    # Sauvegarder le résultat sur le disque
                    self._persist_result(item)
                else:
                    item.status = QueueItemStatus.FAILED
                    item.error = "Aucune fonction de traitement configurée"
                    logger.error("Pas de fonction de traitement configurée")
            except Exception as e:
                item.status = QueueItemStatus.FAILED
                item.error = str(e)
                logger.error(f"Erreur lors du traitement de {item.request_id} : {str(e)}")
            finally:
                with self._queue_lock:
                    self._processing = None
                    self._results[item.request_id] = item
                    # Mettre à jour les positions
                    self._update_positions()

    def _persist_result(self, item: QueueItem):
        """
        Sauvegarde le résultat de la requête dans un fichier JSON.
        
        Les fichiers sont organisés par utilisateur (e-mail sanitisé) 
        dans le répertoire 'data/results/'.
        """
        try:
            # Préparer le répertoire de destination
            sanitized_email = sanitize_email(item.user_email)
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            results_dir = os.path.join(base_dir, "data", "results", sanitized_email)
            
            os.makedirs(results_dir, exist_ok=True)
            
            # Préparer le contenu du fichier
            file_path = os.path.join(results_dir, f"{item.request_id}.json")
            data = {
                "request_id": item.request_id,
                "user_email": item.user_email,
                "status": item.status.value,
                "result": item.result,
                "timestamp": item.created_at
            }
            
            # Écrire le fichier
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Résultat pour {item.request_id} sauvegardé dans {file_path}")
            
        except Exception as e:
            logger.error(f"Échec de la sauvegarde du résultat pour {item.request_id} : {str(e)}")

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
            if self._processing:
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

            # Vérifier dans les résultats
            if request_id in self._results:
                result_item = self._results[request_id]
                return {
                    "request_id": request_id,
                    "status": result_item.status.value,
                    "result": result_item.result,
                    "error": result_item.error,
                }

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
        with self._queue_lock:
            item = self._results.get(request_id)
            if item and item.status == QueueItemStatus.COMPLETED:
                return item.result
            return None

    def get_user_recent_items(self, user_id: int, limit: int = 20) -> List[dict]:
        """
        Récupère les éléments récents d'un utilisateur (en file + terminés).

        Args:
            user_id: Identifiant de l'utilisateur
            limit: Nombre maximum d'éléments

        Returns:
            Liste de dictionnaires décrivant les éléments
        """
        self._initialize()
        items = []
        with self._queue_lock:
            # En cours de traitement
            if self._processing and self._processing.user_id == user_id:
                items.append({
                    "request_id": self._processing.request_id,
                    "status": self._processing.status.value,
                    "position": 0,
                    "created_at": self._processing.created_at,
                })

            # En file d'attente
            for item in self._queue:
                if item.user_id == user_id:
                    items.append({
                        "request_id": item.request_id,
                        "status": item.status.value,
                        "position": item.position,
                        "created_at": item.created_at,
                    })

            # Résultats terminés
            for req_id, item in self._results.items():
                if item.user_id == user_id:
                    items.append({
                        "request_id": item.request_id,
                        "status": item.status.value,
                        "position": -1,
                        "created_at": item.created_at,
                        "error": item.error,
                    })

        # Trier par date de création (plus récent en premier) et limiter
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[:limit]
