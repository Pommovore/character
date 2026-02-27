"""Module API principal pour l'application d'extraction de traits de caractère.

Ce module configure et crée l'instance de l'application FastAPI,
incluant les templates Jinja2, les fichiers statiques, le middleware
de setup, et tous les routeurs.
"""

import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from src import __version__
from src.database import init_db
from src.api.traits_endpoints import router as traits_router
from src.api.setup_routes import router as setup_router, is_setup_done
from src.api.admin_routes import router as admin_router
from src.api.user_routes import router as user_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SetupMiddleware(BaseHTTPMiddleware):
    """Middleware qui redirige vers /setup si la configuration initiale n'est pas faite."""

    async def dispatch(self, request: Request, call_next):
        """Vérifie si le setup est fait, sinon redirige."""
        # Ne pas rediriger les requêtes vers /setup, /static, /health, /api/docs
        path = request.url.path
        allowed_paths = ["/setup", "/static", "/health", "/api/docs", "/api/redoc", "/api/openapi.json"]

        if not is_setup_done() and not any(path.startswith(p) for p in allowed_paths):
            return RedirectResponse(url="/setup", status_code=302)

        return await call_next(request)


def create_application(start_worker: bool = True) -> FastAPI:
    """
    Crée et configure l'application FastAPI.

    Returns:
        Instance d'application FastAPI configurée
    """
    # Charger les variables d'environnement (chercher à la racine du projet)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env_path = os.path.join(root_dir, ".env")
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Variables d'environnement chargées depuis {env_path}")
    else:
        # Fallback : charger depuis le répertoire de travail actuel
        load_dotenv()
        logger.info("Tentative de chargement des variables d'environnement depuis le CWD")

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

    # Ajouter le middleware de setup
    app.add_middleware(SetupMiddleware)

    # Ajouter le middleware CORS
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Monter les fichiers statiques
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Inclure tous les routeurs
    app.include_router(setup_router)
    app.include_router(admin_router)
    app.include_router(user_router)
    app.include_router(traits_router)

    # Point de terminaison de vérification de santé
    @app.get("/health", tags=["Santé"])
    async def health_check():
        """Point de terminaison de vérification de santé."""
        return {"status": "en bonne santé", "version": __version__}

    # Page d'accueil — redirige vers login ou dashboard
    @app.get("/")
    async def root(request: Request):
        """Redirige la racine vers la page appropriée."""
        from src.services.auth_service import get_current_user
        from src.database import get_db, SessionLocal

        if SessionLocal:
            db = SessionLocal()
            try:
                user = get_current_user(request, db)
                if user:
                    if user.role == "admin":
                        return RedirectResponse(url="/admin", status_code=302)
                    return RedirectResponse(url="/dashboard", status_code=302)
            finally:
                db.close()

        return RedirectResponse(url="/login", status_code=302)

    # Gestionnaire d'exceptions global
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Exception non gérée : {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Une erreur inattendue s'est produite."}
        )

    # Initialiser la base de données au démarrage
    @app.on_event("startup")
    async def startup_event():
        """Initialise la base de données et le worker de la file d'attente au démarrage."""
        init_db()
        logger.info("Base de données initialisée")

        if start_worker:
            # Démarrer le worker de la file d'attente
            from src.services.request_queue import RequestQueue
            from src.services.traits_extractor import TraitsExtractor

            queue = RequestQueue()

            def process_request(text, directive, model_name):
                """Fonction de traitement pour la file d'attente."""
                extractor = TraitsExtractor(model_name)
                traits = extractor.extract_traits(text, directive)
                summary = extractor.generate_summary(traits)
                return {
                    "traits": [{"trait": t.trait, "score": t.score, "category": t.category} for t in traits],
                    "summary": summary,
                    "model_used": model_name,
                }

            queue.start_worker(process_request)
            logger.info("Worker de la file d'attente démarré")
        else:
            logger.info("Démarrage du worker ignoré (start_worker=False)")

    # Arrêter proprement le worker à la fermeture
    @app.on_event("shutdown")
    async def shutdown_event():
        """Arrête le worker de la file d'attente à la fermeture."""
        from src.services.request_queue import RequestQueue
        queue = RequestQueue()
        queue.stop_worker()
        logger.info("Worker de la file d'attente arrêté proprement")

    return app


# Créer l'instance de l'application
app = create_application()