"""Service d'authentification et de gestion des tokens.

Ce module fournit les fonctions de hachage de mots de passe,
création/vérification de JWT, et validation des tokens API.
"""

import datetime
import hashlib
import logging
import secrets
import base64
import bcrypt
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException

from src.models.user import User, ApiToken, RequestLog

# Configuration du logging
logger = logging.getLogger(__name__)

# Note: Nous utilisons bcrypt directement au lieu de passlib pour éviter une incompatibilité
# entre passlib 1.7.4 et bcrypt >= 4.0.0 (AttributeError: module 'bcrypt' has no attribute '__about__')

# Configuration JWT (la SECRET_KEY sera chargée depuis .env)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 heures

# Limites de requêtes par 24h
RATE_LIMIT_NORMAL = 20
RATE_LIMIT_VIP = 100


def get_secret_key() -> str:
    """
    Récupère la clé secrète depuis les variables d'environnement.

    Returns:
        Clé secrète pour la signature JWT
    """
    import os
    key = os.environ.get("SECRET_KEY", "")
    if not key:
        # Clé par défaut pour le développement uniquement
        logger.warning("SECRET_KEY non définie, utilisation d'une clé par défaut (NON SÉCURISÉ)")
        key = "dev-secret-key-change-me-in-production"
    return key


def hash_password(password: str) -> str:
    """
    Hache un mot de passe avec bcrypt (après un pré-hachage SHA-256 pour éviter la limite de 72 octets).

    Args:
        password: Mot de passe en clair

    Returns:
        Mot de passe haché
    """
    # Pré-hachage SHA-256 pour surmonter la limite de 72 octets de bcrypt
    pre_hashed = hashlib.sha256(password.encode("utf-8")).digest()
    pre_hashed_b64 = base64.b64encode(pre_hashed).decode("utf-8")
    
    # Hachage bcrypt direct
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pre_hashed_b64.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie un mot de passe contre son hash.

    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash du mot de passe

    Returns:
        True si le mot de passe correspond
    """
    # Pré-hachage SHA-256 identique à celui de hash_password
    pre_hashed = hashlib.sha256(plain_password.encode("utf-8")).digest()
    pre_hashed_b64 = base64.b64encode(pre_hashed).decode("utf-8")
    
    # Vérification bcrypt directe
    try:
        return bcrypt.checkpw(
            pre_hashed_b64.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du mot de passe : {str(e)}")
        return False


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """
    Crée un token JWT pour l'authentification de session.

    Args:
        data: Données à encoder dans le token
        expires_delta: Durée de validité en minutes

    Returns:
        Token JWT encodé
    """
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """
    Vérifie et décode un token JWT.

    Args:
        token: Token JWT à vérifier

    Returns:
        Données décodées ou None si le token est invalide
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_token(source_string: str) -> str:
    """
    Génère un token API à partir d'une chaîne source.

    Args:
        source_string: Chaîne d'origine pour la génération

    Returns:
        Token API (hash SHA256)
    """
    # Ajouter un sel aléatoire pour garantir l'unicité
    salt = secrets.token_hex(8)
    raw = f"{source_string}:{salt}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    return token


def generate_random_token() -> str:
    """
    Génère un token API aléatoire.

    Returns:
        Token API aléatoire (32 octets hex)
    """
    return secrets.token_hex(32)


def get_current_user(request: Request, db: Session) -> Optional[User]:
    """
    Récupère l'utilisateur connecté à partir du cookie JWT.

    Args:
        request: Requête FastAPI
        db: Session de base de données

    Returns:
        Utilisateur connecté ou None
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = verify_access_token(token)
    if not payload:
        return None

    user_id = payload.get("user_id")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


def validate_api_token(authorization: str, db: Session) -> tuple:
    """
    Valide un token API et vérifie le rate limit.

    Args:
        authorization: Valeur du header Authorization (Bearer <token>) ou token brut
        db: Session de base de données

    Returns:
        Tuple (user, api_token) si valide

    Raises:
        HTTPException: Si le token est invalide, l'utilisateur bloqué, ou le rate limit dépassé
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token d'autorisation manquant")

    # Extraire le token (supporte 'Bearer <token>' ou '<token>')
    if authorization.startswith("Bearer "):
        token_string = authorization[7:]
    else:
        token_string = authorization

    # Chercher le token en base
    api_token = db.query(ApiToken).filter(
        ApiToken.token == token_string,
        ApiToken.is_active == True
    ).first()

    if not api_token:
        raise HTTPException(status_code=401, detail="Token API invalide ou désactivé")

    # Vérifier le statut de l'utilisateur
    user = api_token.user
    if user.status in ("rejected", "suspended", "pending"):
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : votre compte est en statut '{user.status}'"
        )

    # Vérifier le rate limit
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    request_count = db.query(RequestLog).filter(
        RequestLog.user_id == user.id,
        RequestLog.created_at >= since
    ).count()

    rate_limit = RATE_LIMIT_VIP if user.status == "vip" else RATE_LIMIT_NORMAL
    if request_count >= rate_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de requêtes atteinte ({rate_limit}/24h). "
                   f"Réessayez plus tard."
        )

    return user, api_token


def get_remaining_requests(user: User, db: Session) -> int:
    """
    Calcule le nombre de requêtes restantes pour un utilisateur.

    Args:
        user: Utilisateur
        db: Session de base de données

    Returns:
        Nombre de requêtes restantes dans les prochaines 24h
    """
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    request_count = db.query(RequestLog).filter(
        RequestLog.user_id == user.id,
        RequestLog.created_at >= since
    ).count()

    rate_limit = RATE_LIMIT_VIP if user.status == "vip" else RATE_LIMIT_NORMAL
    return max(0, rate_limit - request_count)
