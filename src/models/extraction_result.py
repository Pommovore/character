"""Modèle SQLAlchemy pour persister les résultats d'extraction.

Ce module définit la table de la base de données pour stocker 
les résultats des extractions de traits de caractère.
"""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from src.database import Base


class ExtractionResult(Base):
    """Modèle représentant le résultat d'une requête d'extraction."""

    __tablename__ = "extraction_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_email = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # completed, failed
    result_json = Column(JSON, nullable=True)     # Contient les traits et le summary
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<ExtractionResult(id={self.id}, request_id='{self.request_id}', status='{self.status}')>"
