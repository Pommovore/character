"""Module de configuration de la base de données.

Ce module fournit la connexion SQLite, la factory de session,
et la base déclarative pour les modèles SQLAlchemy.
"""

import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Configuration du logging
logger = logging.getLogger(__name__)

# Répertoire de stockage de la base de données
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(BASE_DIR, "data", "db")
DB_PATH = os.path.join(DB_DIR, "character.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Base déclarative pour les modèles
Base = declarative_base()

# Moteur et session (initialisés à la demande)
engine = None
SessionLocal = None


def init_db():
    """
    Initialise la base de données : crée le répertoire, le moteur
    et les tables si elles n'existent pas encore.
    """
    global engine, SessionLocal

    import src.models.user  # Importer les modèles pour qu'ils soient enregistrés
    import src.models.extraction_result  # Modèle des résultats

    # Créer le répertoire de la base de données s'il n'existe pas
    db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
    if db_dir and db_dir != "sqlite://":  # Ignorer pour la base de données en mémoire
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Répertoire de la base de données : {db_dir}")

    from sqlalchemy.pool import NullPool

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Créer toutes les tables
    Base.metadata.create_all(bind=engine)
    logger.info("Base de données initialisée avec succès")


def get_db():
    """
    Générateur de session pour l'injection de dépendance FastAPI.

    Yields:
        Session SQLAlchemy
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
