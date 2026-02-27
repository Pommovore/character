"""Tests pour la persistance des résultats d'extraction.
"""

import os
import json
import pytest
import shutil
from src.services.request_queue import QueueItem, RequestQueue, QueueItemStatus
from src.utils.path_utils import sanitize_email

@pytest.fixture
def cleanup_results():
    """Nettoie le dossier data/results après les tests."""
    yield
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "results"))
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)

def test_sanitize_email():
    """Teste la fonction de sanitisation des e-mails."""
    assert sanitize_email("moi@ici.fr") == "moi_at_ici_fr"
    assert sanitize_email("Jean.Doe-99@example.com") == "jean_doe_99_at_example_com"
    assert sanitize_email("user+tag@domain.co.uk") == "user_tag_at_domain_co_uk"

def test_persist_result(cleanup_results):
    """Teste la sauvegarde d'un résultat sur le disque via RequestQueue."""
    queue = RequestQueue()
    
    item = QueueItem(
        request_id="test-persist-001",
        user_id=1,
        user_email="test@example.com",
        text="Texte de test",
        result={"traits": [], "summary": "Test", "model_used": "test-model"},
        status=QueueItemStatus.COMPLETED
    )
    
    # Appel de la méthode de persistance (privée)
    queue._persist_result(item)
    
    # Vérification du fichier
    sanitized = sanitize_email("test@example.com")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    expected_path = os.path.join(base_dir, "data", "results", sanitized, "test-persist-001.json")
    
    assert os.path.exists(expected_path)
    
    with open(expected_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["request_id"] == "test-persist-001"
        assert data["user_email"] == "test@example.com"
        assert data["result"]["summary"] == "Test"
