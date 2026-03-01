"""Tests pour la persistance des résultats d'extraction.
"""

import os
import json
import pytest
import shutil
from src.services.request_queue import QueueItem, RequestQueue, QueueItemStatus
from src.utils.path_utils import sanitize_email

@pytest.fixture
def db_session():
    import src.database
    
    if src.database.engine is None:
        src.database.init_db()
    else:
        # Just in case the engine is already initialized, enforce creation of tables
        src.database.Base.metadata.create_all(bind=src.database.engine)
    
    db = src.database.SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

def test_sanitize_email():
    """Teste la fonction de sanitisation des e-mails."""
    assert sanitize_email("moi@ici.fr") == "moi_at_ici_fr"
    assert sanitize_email("Jean.Doe-99@example.com") == "jean_doe_99_at_example_com"
    assert sanitize_email("user+tag@domain.co.uk") == "user_tag_at_domain_co_uk"

def test_persist_result(db_session):
    """Teste la sauvegarde d'un résultat en base de données via RequestQueue."""
    # Nettoyer avant
    from src.models.extraction_result import ExtractionResult
    db_session.query(ExtractionResult).filter_by(request_id="test-persist-001").delete()
    db_session.commit()

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
    queue._persist_to_db(item)
    
    # Vérification en base de données
    saved_result = db_session.query(ExtractionResult).filter_by(request_id="test-persist-001").first()
    
    assert saved_result is not None
    assert saved_result.request_id == "test-persist-001"
    assert saved_result.user_email == "test@example.com"
    assert saved_result.status == "completed"
    assert saved_result.result_json["summary"] == "Test"
