"""Point d'entrée principal pour le service API d'extraction de traits de caractère.

Ce module fournit le point d'entrée pour exécuter l'API avec Uvicorn.
"""

import logging
import uvicorn
import os

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.api import app

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Exécute le serveur API en utilisant Uvicorn."""
    # Récupérer l'hôte et le port depuis l'environnement ou utiliser les valeurs par défaut
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    
    logger.info(f"Démarrage de l'API d'extraction de traits de caractère sur {host}:{port}")
    
    # Exécuter l'application avec Uvicorn
    uvicorn.run(
        "src.api.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()