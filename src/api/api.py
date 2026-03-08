"""Module API principal pour l'application d'extraction de traits de caractère.

Ce module configure et crée l'instance de l'application FastAPI,
incluant les templates Jinja2, les fichiers statiques, le middleware
de setup, et tous les routeurs.
"""

import os
import re
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette_csrf import CSRFMiddleware

from src import __version__
from src.database import init_db
from src.api.traits_endpoints import router as traits_router
from src.api.setup_routes import router as setup_router, is_setup_done
from src.api.admin_routes import router as admin_router
from src.api.user_routes import router as user_router

# Initialisation du logger pour ce module
logger = logging.getLogger(__name__)


class SetupMiddleware(BaseHTTPMiddleware):
    """Middleware qui redirige vers /setup si la configuration initiale n'est pas faite."""

    async def dispatch(self, request: Request, call_next):
        """Vérifie si le setup est fait, sinon redirige."""
        # Nettoyer le chemin brut en supprimant le préfixe si Nginx ne l'a pas fait
        path = request.scope.get('path', '')
        root_path = request.scope.get('root_path', '')
        if root_path and path.startswith(root_path):
            path = path[len(root_path):]
            if not path.startswith('/'):
                path = '/' + path
                
        allowed_paths = ["/setup", "/static", "/health", "/api/docs", "/api/redoc", "/api/openapi.json"]

        if not is_setup_done() and not any(path.startswith(p) for p in allowed_paths):
            return RedirectResponse(url=f"{root_path}/setup", status_code=302)

        return await call_next(request)


class ProxyPrefixMiddleware(BaseHTTPMiddleware):
    """Middleware qui FORCE le root_path à partir du header nginx X-Forwarded-Prefix."""

    async def dispatch(self, request: Request, call_next):
        prefix = request.headers.get("x-forwarded-prefix")
        if prefix:
            request.scope["root_path"] = prefix
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

    # Gestionnaire de cycle de vie (remplacement de @app.on_event déprécié)
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialise les ressources au démarrage et les libère à l'arrêt."""
        # --- Démarrage ---
        init_db()
        logger.info("Base de données initialisée")

        if start_worker:
            from src.services.request_queue import RequestQueue
            from src.services.traits_extractor import TraitsExtractor

            queue = RequestQueue()

            def process_request(text, directive, model_name):
                """Fonction de traitement pour la file d'attente."""
                extractor = TraitsExtractor(model_name)
                traits, validated_model = extractor.extract_traits(text, directive)
                summary = extractor.generate_summary(traits)
                return {
                    "traits": [{"trait": t.trait, "score": t.score, "category": t.category} for t in traits],
                    "summary": summary,
                    "model_used": model_name,
                    "validated_model": validated_model,
                }

            queue.start_worker(process_request)
            logger.info("Worker de la file d'attente démarré")
        else:
            logger.info("Démarrage du worker ignoré (start_worker=False)")

        yield  # L'application tourne ici

        # --- Arrêt ---
        from src.services.request_queue import RequestQueue
        queue = RequestQueue()
        queue.stop_worker()
        logger.info("Worker de la file d'attente arrêté proprement")

    app = FastAPI(
        title="Extracteur de Traits de Caractère",
        description=(
            "API pour extraire les traits de caractère à partir de descriptions textuelles "
            "en utilisant les modèles LLM de Hugging Face."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Ajouter le middleware de setup
    app.add_middleware(SetupMiddleware)

    # Ajouter le middleware CORS (Fix Audit 3.1)
    allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "*")
    allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]
    
    # Sécurité: Ne jamais autoriser les credentials avec le wildcard "*"
    allow_credentials = "*" not in allowed_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Protection CSRF pour les formulaires HTML (Double Submit Cookie)
    # Les routes API sont exclues car elles utilisent l'authentification par token
    csrf_secret = os.environ.get("SECRET_KEY", "dev-csrf-secret")
    app.add_middleware(
        CSRFMiddleware,
        secret=csrf_secret,
        required_urls=[
            re.compile(r".*/login$"),
            re.compile(r".*/register$"),
            re.compile(r".*/setup$"),
            re.compile(r".*/dashboard/model$"),
            re.compile(r".*/admin/users/.+")
        ],
        exempt_urls=[
            re.compile(r".*/api/.*"),
            re.compile(r".*/health$"),
            re.compile(r".*/static/.*")
        ],
    )

    # Ajouter le middleware de proxy/root_path EN PREMIER (le dernier ajouté est exécuté en premier)
    app.add_middleware(ProxyPrefixMiddleware)

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
        from src.database import SessionLocal

        if SessionLocal:
            db = SessionLocal()
            try:
                user = get_current_user(request, db)
                if user:
                    if user.role == "admin":
                        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/admin", status_code=302)
                    return RedirectResponse(url=f"{request.scope.get('root_path', '')}/dashboard", status_code=302)
            finally:
                db.close()

        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/login", status_code=302)

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