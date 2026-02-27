"""Modèles SQLAlchemy pour les utilisateurs, tokens et logs de requêtes.

Ce module définit les tables de la base de données pour la gestion
des utilisateurs, des tokens d'API et du suivi des requêtes.
"""

import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from src.database import Base


class User(Base):
    """Modèle représentant un utilisateur de l'application."""

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, normal, vip, rejected, suspended
    role = Column(
        String(20), nullable=False, default="user"
    )  # user, admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relations
    tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', status='{self.status}', role='{self.role}')>"


class ApiToken(Base):
    """Modèle représentant un token d'API pour l'authentification des requêtes."""

    __tablename__ = "api_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    token = Column(String(64), unique=True, nullable=False, index=True)
    source_string = Column(Text, nullable=True)  # La chaîne d'origine utilisée pour générer le token
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="tokens")
    request_logs = relationship("RequestLog", back_populates="api_token", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ApiToken(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class RequestLog(Base):
    """Modèle pour le suivi des requêtes API (rate limiting)."""

    __tablename__ = "request_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("api_token.id"), nullable=False)
    request_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="request_logs")
    api_token = relationship("ApiToken", back_populates="request_logs")

    def __repr__(self):
        return f"<RequestLog(id={self.id}, user_id={self.user_id}, token_id={self.token_id})>"
