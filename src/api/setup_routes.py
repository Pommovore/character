"""Routes pour le wizard de configuration initiale.

Ce module gère la page de setup affichée au premier lancement
pour configurer l'administrateur et les variables d'environnement.
"""

import os
import secrets
import logging

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.services.auth_service import hash_password

# Configuration du logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Setup"])

# Chemin du fichier .env
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_FILE = os.path.join(BASE_DIR, ".env")

# Templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def is_setup_done() -> bool:
    """Vérifie si le setup initial a déjà été effectué."""
    if not os.path.exists(ENV_FILE):
        return False
    with open(ENV_FILE, 'r') as f:
        return "ADMIN_EMAIL=" in f.read()


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Affiche le formulaire de configuration initiale."""
    if is_setup_done():
        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/login", status_code=302)

    return templates.TemplateResponse("setup.html", {
        "request": request,
        "error": None,
    })


@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    setup_pin: str = Form(""),
    discord_webhook: str = Form(""),
    hf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    """Traite le formulaire de configuration initiale."""
    if is_setup_done():
        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/login", status_code=302)

    # Validation
    errors = []
    
    expected_pin = None
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith("SETUP_PIN_CODE="):
                    expected_pin = line.strip().split("=", 1)[1]
                    break
                    
    if expected_pin and setup_pin != expected_pin:
        errors.append("Code PIN de sécurité incorrect")
        
    if not email or "@" not in email:
        errors.append("Adresse email invalide")
    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères")
    if password != password_confirm:
        errors.append("Les mots de passe ne correspondent pas")

    if errors:
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "error": " | ".join(errors),
            "email": email,
            "discord_webhook": discord_webhook,
            "hf_token": hf_token,
        })

    # Mettre à jour le fichier .env
    existing_env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing_env[k] = v

    secret_key = existing_env.get("SECRET_KEY", secrets.token_hex(32))
    
    existing_env["ADMIN_EMAIL"] = email
    existing_env["SECRET_KEY"] = secret_key
    existing_env["DISCORD_WEBHOOK_URL"] = discord_webhook
    existing_env["HF_TOKEN"] = hf_token
    if "DATABASE_URL" not in existing_env:
        existing_env["DATABASE_URL"] = "sqlite:///data/db/character.db"
    if "PORT" not in existing_env:
        existing_env["PORT"] = "8000"
    if "HOST" not in existing_env:
        existing_env["HOST"] = "0.0.0.0"

    if "SETUP_PIN_CODE" in existing_env:
        del existing_env["SETUP_PIN_CODE"]
        
    env_content = "\n".join([f"{k}={v}" for k, v in existing_env.items()]) + "\n"

    try:
        with open(ENV_FILE, "w") as f:
            f.write(env_content)
        logger.info(f"Fichier .env mis à jour avec succès pour l'administrateur : {email}")

        # Charger les variables d'environnement
        os.environ["ADMIN_EMAIL"] = email
        os.environ["SECRET_KEY"] = secret_key
        os.environ["DISCORD_WEBHOOK_URL"] = discord_webhook
        os.environ["HF_TOKEN"] = hf_token

    except Exception as e:
        logger.error(f"Erreur lors de la création du fichier .env : {str(e)}")
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "error": f"Erreur lors de la création de la configuration : {str(e)}",
        })

    # Créer l'utilisateur administrateur en base
    try:
        admin_user = User(
            email=email,
            hashed_password=hash_password(password),
            status="vip",
            role="admin",
        )
        db.add(admin_user)
        db.commit()
        logger.info(f"Administrateur créé : {email}")
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la création de l'administrateur : {str(e)}")
        # Supprimer le .env en cas d'erreur
        if os.path.exists(ENV_FILE):
            os.remove(ENV_FILE)
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "error": f"Erreur lors de la création de l'administrateur : {str(e)}",
        })

    return RedirectResponse(url=f"{request.scope.get('root_path', '')}/login?setup=ok", status_code=302)
