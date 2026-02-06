"""Module API principal pour l'application d'extraction de traits de caractère.

Ce module configure et crée l'instance de l'application FastAPI.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.api.traits_endpoints import router as traits_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """
    Crée et configure l'application FastAPI.
    
    Returns:
        Instance d'application FastAPI configurée
    """
    app = FastAPI(
        title="Extracteur de Traits de Caractère",
        description=(
            "API pour extraire les traits de caractère à partir de descriptions textuelles "
            "en utilisant les modèles transformer de Hugging Face."
        ),
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # Ajouter le middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En production, spécifiez les origines autorisées
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Inclure les routeurs
    app.include_router(traits_router)
    
    # Ajouter le point de terminaison de vérification de santé
    @app.get("/health", tags=["Santé"])
    async def health_check():
        """Point de terminaison de vérification de santé."""
        return {"status": "en bonne santé", "version": __version__}
    
    # Gestionnaire d'exceptions global
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Exception non gérée : {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Une erreur inattendue s'est produite."}
        )
    
    return app


# Créer l'instance de l'application
app = create_application()