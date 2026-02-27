"""Utilitaire pour la détection et le téléchargement de contenu depuis des URLs.

Ce module fournit des fonctions pour détecter si un texte est une URL
et pour télécharger le contenu textuel pointé par cette URL.
"""

import logging
from urllib.parse import urlparse

import httpx

# Configuration du logging
logger = logging.getLogger(__name__)

# Constantes de configuration
REQUEST_TIMEOUT_SECONDS = 30
MAX_CONTENT_SIZE_BYTES = 1_048_576  # 1 Mo


def is_url(text: str) -> bool:
    """
    Vérifie si le texte fourni est une URL valide (http ou https).

    Args:
        text: Texte à vérifier

    Returns:
        True si le texte est une URL valide, False sinon
    """
    text = text.strip()
    try:
        result = urlparse(text)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


async def fetch_text_content(url: str) -> str:
    """
    Télécharge le contenu textuel depuis l'URL fournie.

    Args:
        url: URL à partir de laquelle télécharger le contenu

    Returns:
        Contenu textuel de la page

    Raises:
        ValueError: Si le contenu n'est pas textuel, dépasse la taille maximale,
                     ou si le téléchargement échoue
    """
    url = url.strip()
    logger.info(f"Téléchargement du contenu depuis l'URL : {url}")

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Vérifier que le contenu est de type texte
            content_type = response.headers.get("content-type", "")
            if not _is_text_content_type(content_type):
                logger.warning(f"Type de contenu non textuel détecté : {content_type}")
                raise ValueError(
                    f"Le contenu de l'URL n'est pas textuel (type: {content_type}). "
                    "Seuls les contenus textuels sont acceptés."
                )

            # Vérifier la taille du contenu
            content_length = len(response.content)
            if content_length > MAX_CONTENT_SIZE_BYTES:
                logger.warning(
                    f"Contenu trop volumineux : {content_length} octets "
                    f"(max: {MAX_CONTENT_SIZE_BYTES})"
                )
                raise ValueError(
                    f"Le contenu de l'URL est trop volumineux "
                    f"({content_length} octets, max: {MAX_CONTENT_SIZE_BYTES})."
                )

            text_content = response.text
            logger.info(
                f"Contenu téléchargé avec succès : {len(text_content)} caractères"
            )
            return text_content

    except httpx.TimeoutException:
        logger.error(f"Timeout lors du téléchargement de l'URL : {url}")
        raise ValueError(
            f"Délai d'attente dépassé lors du téléchargement de l'URL ({REQUEST_TIMEOUT_SECONDS}s)."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Erreur HTTP {e.response.status_code} pour l'URL : {url}")
        raise ValueError(
            f"Erreur HTTP {e.response.status_code} lors du téléchargement de l'URL."
        )
    except httpx.RequestError as e:
        logger.error(f"Erreur de connexion pour l'URL {url} : {str(e)}")
        raise ValueError(
            f"Impossible de se connecter à l'URL : {str(e)}"
        )


def _is_text_content_type(content_type: str) -> bool:
    """
    Vérifie si le type de contenu HTTP correspond à du texte.

    Args:
        content_type: Valeur de l'en-tête Content-Type

    Returns:
        True si le contenu est textuel, False sinon
    """
    text_types = ("text/", "application/json", "application/xml")
    return any(content_type.startswith(t) for t in text_types)
