"""Script de lancement pour l'API d'extraction de traits de caractère.

Il charge les variables d'environnement depuis le fichier .env et lance le serveur
Uvicorn avec l'hôte et le port spécifiés.
"""

import os
import uvicorn
from dotenv import load_dotenv

def run_server():
    """Charge la configuration et démarre le serveur Uvicorn."""
    # Charger les variables d'environnement depuis .env
    load_dotenv()
    
    # Récupérer l'hôte et le port depuis l'environnement (avec valeurs par défaut)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    
    # Mode reload désactivé par défaut (activable via RELOAD=True dans .env pour le dev)
    reload = os.environ.get("RELOAD", "False").lower() == "true"
    
    print(f"Démarrage du serveur sur {host}:{port} (reload={reload})")
    
    # Le reverse proxy nginx ajoute /character (doit être configuré via root_path pour aider FastAPI / StaticFiles)
    root_path = os.environ.get("ROOT_PATH", "/character")

    uvicorn.run(
        "src.api.api:app",
        host=host,
        port=port,
        reload=reload,
        proxy_headers=True,
        forwarded_allow_ips="*",
        root_path=root_path
    )

if __name__ == "__main__":
    run_server()
