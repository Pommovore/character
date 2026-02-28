"""Module de chargement de la configuration dynamique.

Ce module lit le fichier config/deploy.conf pour charger les
modèles disponibles pour l'interface utilisateur.
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)

def load_deploy_config():
    """Charge la configuration depuis config/deploy.conf."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(base_dir, "config", "deploy.conf")
    
    if not os.path.exists(config_path):
        logger.warning(f"Fichier de configuration {config_path} introuvable.")
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de deploy.conf: {e}")
        return {}

def get_available_models():
    """Retourne la liste des modèles définis dans deploy.conf."""
    config = load_deploy_config()
    models = config.get("models", [])
    if not models:
        # Fallback de sécurité
        models = [
            "Qwen/Qwen2.5-72B-Instruct",
            "meta-llama/Llama-3.2-3B-Instruct",
        ]
    return models

def get_default_model():
    """Retourne le premier modèle de la liste comme modèle par défaut."""
    models = get_available_models()
    return models[0] if models else "Qwen/Qwen2.5-72B-Instruct"
