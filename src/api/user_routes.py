"""Routes pour les utilisateurs : connexion, inscription, tableau de bord.

Ce module gère l'authentification des utilisateurs, leur inscription,
et l'affichage de leur tableau de bord avec la file d'attente en temps réel.
"""

import json
import asyncio
import logging
import os

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User, ApiToken
from src.services.auth_service import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_remaining_requests
)
from src.services.request_queue import RequestQueue
from src.config import get_available_models

# Configuration du logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Utilisateur"])

# Templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Affiche le formulaire de connexion."""
    setup_ok = request.query_params.get("setup") == "ok"
    registered = request.query_params.get("registered") == "ok"
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
        "success": "Configuration terminée. Connectez-vous." if setup_ok
                   else "Inscription réussie. Attendez la validation par l'administrateur." if registered
                   else None,
    })


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Traite la tentative de connexion."""
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Email ou mot de passe incorrect",
        })

    if user.status == "pending":
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Votre compte est en attente de validation par l'administrateur",
        })

    if user.status in ("rejected", "suspended"):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Votre compte a été {user.status}",
        })

    # Créer le token JWT et le stocker dans un cookie
    token = create_access_token({"user_id": user.id, "email": user.email})
    redirect_url = f"{request.scope.get('root_path', '')}/admin" if user.role == "admin" else f"{request.scope.get('root_path', '')}/dashboard"
    root_path = request.scope.get("root_path", "")
    redirect = root_path + redirect_url
    response = RedirectResponse(url=redirect, status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,  # 24 heures
        samesite="lax",
    )

    logger.info(f"Connexion réussie pour : {user.email}")
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Affiche le formulaire d'inscription."""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error": None,
    })


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    """Traite l'inscription d'un nouvel utilisateur."""
    # Validation
    errors = []
    if not email or "@" not in email:
        errors.append("Adresse email invalide")
    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères")
    if password != password_confirm:
        errors.append("Les mots de passe ne correspondent pas")

    # Vérifier si l'email existe déjà
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        errors.append("Cette adresse email est déjà utilisée")

    if errors:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": " | ".join(errors),
            "email": email,
        })

    # Créer l'utilisateur en statut pending
    new_user = User(
        email=email,
        hashed_password=hash_password(password),
        status="pending",
        role="user",
    )
    db.add(new_user)
    db.commit()

    logger.info(f"Nouvel utilisateur inscrit (en attente de validation) : {email}")

    return RedirectResponse(url=f"{request.scope.get('root_path', '')}/login?registered=ok", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """Affiche le tableau de bord de l'utilisateur."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/login", status_code=302)

    # Récupérer le token actif
    active_token = db.query(ApiToken).filter(
        ApiToken.user_id == user.id,
        ApiToken.is_active == True
    ).first()

    # Requêtes restantes
    remaining = get_remaining_requests(user, db)

    # File d'attente
    queue = RequestQueue()
    queue_items = queue.get_user_recent_items(user.id)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "active_token": active_token,
        "remaining_requests": remaining,
        "queue_items": queue_items,
        "available_models": get_available_models(),
    })


@router.post("/dashboard/model")
async def update_preferred_model(
    request: Request,
    model: str = Form(...),
    db: Session = Depends(get_db),
):
    """Met à jour le modèle préféré de l'utilisateur."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
        
    models = get_available_models()
    if model in models:
        user.preferred_model = model
        db.commit()
        logger.info(f"Modèle préféré mis à jour pour {user.email} -> {model}")
        
    return RedirectResponse(url=f"{request.scope.get('root_path', '')}/dashboard", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    """Déconnecte l'utilisateur."""
    response = RedirectResponse(url=f"{request.scope.get('root_path', '')}/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/api/v1/queue/status")
async def queue_sse(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint SSE pour la mise à jour en temps réel de la file d'attente.

    Envoie l'état de la file toutes les 2 secondes.
    """
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")

    queue = RequestQueue()

    async def event_generator():
        """Générateur d'événements SSE."""
        while True:
            # Vérifier si le client est toujours connecté
            if await request.is_disconnected():
                break

            # Récupérer l'état de la file pour cet utilisateur
            status = queue.get_queue_status(user.id)
            remaining = get_remaining_requests(user, db)
            status["remaining_requests"] = remaining

            yield f"data: {json.dumps(status, default=str)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
