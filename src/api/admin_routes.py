"""Routes pour l'interface d'administration.

Ce module fournit les pages et actions pour la gestion des utilisateurs
et des tokens par l'administrateur du site.
"""

import logging

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User, ApiToken
from src.services.auth_service import (
    get_current_user, generate_api_token, generate_random_token
)

# Configuration du logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administration"])

# Templates
import os
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dépendance qui vérifie que l'utilisateur connecté est administrateur.

    Raises:
        RedirectResponse: Redirige vers /login si non connecté ou non admin
    """
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": f"{request.scope.get('root_path', '')}/login"})
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user


@router.get("", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Affiche le tableau de bord d'administration."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    # Charger les tokens pour chaque utilisateur
    user_data = []
    for user in users:
        tokens = db.query(ApiToken).filter(ApiToken.user_id == user.id).all()
        user_data.append({
            "user": user,
            "tokens": tokens,
        })

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "admin": admin,
        "users": user_data,
    })


@router.post("/users/{user_id}/validate", response_class=JSONResponse)
async def validate_user(
    user_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Valide ou rejette un utilisateur.

    Args:
        user_id: identifiant de l'utilisateur
        status: nouveau statut (normal, vip, rejected)
    """
    if status not in ("normal", "vip", "rejected"):
        raise HTTPException(status_code=400, detail="Statut invalide")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    old_status = user.status
    user.status = status
    db.commit()

    logger.info(f"Admin {admin.email} a changé le statut de {user.email} : {old_status} -> {status}")

    return {"success": True, "message": f"Statut mis à jour : {status}"}


@router.post("/users/{user_id}/suspend", response_class=JSONResponse)
async def suspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Suspend un utilisateur."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.status = "suspended"
    db.commit()

    logger.info(f"Admin {admin.email} a suspendu {user.email}")

    return {"success": True, "message": "Utilisateur suspendu"}


@router.post("/users/{user_id}/token", response_class=JSONResponse)
async def create_token(
    user_id: int,
    source: str = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Génère un token API à partir d'une chaîne source.

    Args:
        user_id: identifiant de l'utilisateur
        source: chaîne source pour la génération du token
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Désactiver les anciens tokens
    db.query(ApiToken).filter(
        ApiToken.user_id == user_id,
        ApiToken.is_active == True
    ).update({"is_active": False})

    token_string = generate_api_token(source)
    new_token = ApiToken(
        user_id=user_id,
        token=token_string,
        source_string=source,
        is_active=True,
    )
    db.add(new_token)
    db.commit()

    logger.info(f"Admin {admin.email} a créé un token pour {user.email} (source: '{source}')")

    return {"success": True, "token": token_string, "source": source}


@router.post("/users/{user_id}/token/random", response_class=JSONResponse)
async def create_random_token(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Génère un token API aléatoire pour un utilisateur."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Désactiver les anciens tokens
    db.query(ApiToken).filter(
        ApiToken.user_id == user_id,
        ApiToken.is_active == True
    ).update({"is_active": False})

    token_string = generate_random_token()
    new_token = ApiToken(
        user_id=user_id,
        token=token_string,
        source_string="[aléatoire]",
        is_active=True,
    )
    db.add(new_token)
    db.commit()

    logger.info(f"Admin {admin.email} a créé un token aléatoire pour {user.email}")

    return {"success": True, "token": token_string, "source": "[aléatoire]"}
