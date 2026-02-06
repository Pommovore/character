"""
Service de stockage pour les résultats de traitement des caractères.

Ce module fournit un service pour stocker et récupérer les résultats des analyses
de caractères effectuées de manière asynchrone.
"""

import threading
import time
import logging
from typing import Dict, Optional, Callable, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.models.character_traits import CharacterTraitsResponse

# Configuration du logging
logger = logging.getLogger(__name__)

class CharacterStore:
    """Service de stockage et de gestion des résultats d'extraction de traits."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implémentation du pattern Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CharacterStore, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialisation des attributs du singleton."""
        self.results: Dict[str, Optional[CharacterTraitsResponse]] = {}
        self.pending_requests: Dict[str, bool] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)  # Limite à 5 traitements simultanés
        self.lock = threading.Lock()
    
    def is_request_known(self, request_id: str) -> bool:
        """Vérifie si l'identifiant de demande est connu du système."""
        with self.lock:
            return request_id in self.results or request_id in self.pending_requests
    
    def is_request_pending(self, request_id: str) -> bool:
        """Vérifie si une demande est en cours de traitement."""
        with self.lock:
            return request_id in self.pending_requests
    
    def get_result(self, request_id: str) -> Optional[CharacterTraitsResponse]:
        """
        Récupère le résultat d'une demande d'extraction de traits.
        
        Args:
            request_id: Identifiant unique de la demande
            
        Returns:
            Résultat de l'extraction ou None si non disponible
        """
        with self.lock:
            return self.results.get(request_id)
    
    def store_result(self, request_id: str, result: CharacterTraitsResponse) -> None:
        """
        Stocke le résultat d'une extraction de traits.
        
        Args:
            request_id: Identifiant unique de la demande
            result: Résultat de l'extraction
        """
        with self.lock:
            self.results[request_id] = result
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    def register_pending_request(self, request_id: str) -> None:
        """
        Enregistre une nouvelle demande en attente.
        
        Args:
            request_id: Identifiant unique de la demande
        """
        with self.lock:
            self.pending_requests[request_id] = True
    
    def process_async(self, request_id: str, process_func: Callable[[], Any]) -> None:
        """
        Traite une demande de manière asynchrone.
        
        Args:
            request_id: Identifiant unique de la demande
            process_func: Fonction à exécuter pour le traitement
        """
        self.register_pending_request(request_id)
        
        def _wrapper():
            try:
                result = process_func()
                self.store_result(request_id, result)
                logger.info(f"Traitement terminé pour request_id: {request_id}")
            except Exception as e:
                logger.error(f"Erreur lors du traitement de request_id {request_id}: {str(e)}")
                # Stocker l'erreur si nécessaire
                with self.lock:
                    if request_id in self.pending_requests:
                        del self.pending_requests[request_id]
        
        self.executor.submit(_wrapper)
        
    def cleanup_old_results(self, max_age_seconds: int = 3600) -> None:
        """
        Nettoie les anciens résultats pour éviter une utilisation excessive de mémoire.
        
        Args:
            max_age_seconds: Âge maximum des résultats en secondes (par défaut 1 heure)
        """
        # Dans une implémentation réelle, chaque résultat aurait un timestamp
        # et cette méthode serait appelée périodiquement pour supprimer les anciens résultats
        pass