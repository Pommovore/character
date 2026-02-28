"""Service d'intégration avec Discord.

Permet d'envoyer des notifications sur un canal serveur via Webhook.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

async def send_discord_notification(message: str) -> bool:
    """
    Envoie une notification asynchrone via le Webhook Discord.
    
    Args:
        message: Le texte de la notification à envoyer
        
    Returns:
        True si envoyé, False sinon
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False
        
    payload = {
        "content": message,
        "username": "Character Setup",
        "avatar_url": "https://cdn.iconscout.com/icon/free/png-256/bot-146-453026.png"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=5.0)
            if response.status_code in (200, 204):
                logger.debug("Notification Discord envoyée avec succès")
                return True
            else:
                logger.warning(f"Échec de l'envoi Discord (statut {response.status_code})")
                return False
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au Webhook Discord : {str(e)}")
        return False
