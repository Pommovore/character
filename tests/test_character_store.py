"""
Tests pour le service de stockage des caractères.

Ce module contient des tests unitaires pour le service CharacterStore.
"""

import pytest
import time
from unittest.mock import MagicMock

from src.services.character_store import CharacterStore
from src.models.character_traits import CharacterTraitsResponse, CharacterTrait


def test_singleton_pattern():
    """Teste que CharacterStore est bien un singleton."""
    store1 = CharacterStore()
    store2 = CharacterStore()
    assert store1 is store2


def test_register_and_check_pending():
    """Teste l'enregistrement et la vérification des demandes en attente."""
    store = CharacterStore()
    request_id = "test123"
    
    # Vérifier que la demande n'est pas connue initialement
    assert not store.is_request_known(request_id)
    assert not store.is_request_pending(request_id)
    
    # Enregistrer la demande
    store.register_pending_request(request_id)
    
    # Vérifier qu'elle est maintenant connue et en attente
    assert store.is_request_known(request_id)
    assert store.is_request_pending(request_id)


def test_store_and_get_result():
    """Teste le stockage et la récupération des résultats."""
    store = CharacterStore()
    request_id = "test456"
    
    # Créer un résultat fictif
    mock_result = CharacterTraitsResponse(
        traits=[
            CharacterTrait(trait="Courageux", score=0.9, category="Personnalité")
        ],
        summary="Un personnage courageux",
        model_used="test-model",
        request_id=request_id,
        status="completed"
    )
    
    # Stocker le résultat
    store.store_result(request_id, mock_result)
    
    # Vérifier qu'il est connu mais plus en attente
    assert store.is_request_known(request_id)
    assert not store.is_request_pending(request_id)
    
    # Récupérer et vérifier le résultat
    result = store.get_result(request_id)
    assert result is mock_result
    assert result.request_id == request_id
    assert result.traits[0].trait == "Courageux"


def test_async_processing():
    """Teste le traitement asynchrone."""
    store = CharacterStore()
    request_id = "test789"
    
    # Créer un résultat fictif
    mock_result = CharacterTraitsResponse(
        traits=[
            CharacterTrait(trait="Intelligent", score=0.85, category="Personnalité")
        ],
        summary="Un personnage intelligent",
        model_used="test-model",
        request_id=request_id,
        status="completed"
    )
    
    # Fonction de traitement simulée avec délai
    def process_func():
        time.sleep(0.1)  # Simuler un traitement
        return mock_result
    
    # Lancer le traitement asynchrone
    store.process_async(request_id, process_func)
    
    # Vérifier qu'il est en attente
    assert store.is_request_pending(request_id)
    
    # Attendre que le traitement soit terminé
    max_wait = 0.5  # secondes
    start_time = time.time()
    while store.is_request_pending(request_id):
        if time.time() - start_time > max_wait:
            pytest.fail("Le traitement asynchrone a pris trop de temps")
        time.sleep(0.05)
    
    # Vérifier le résultat
    result = store.get_result(request_id)
    assert result is not None
    assert result.request_id == request_id
    assert result.traits[0].trait == "Intelligent"