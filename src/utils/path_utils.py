"""Module utilitaire pour la gestion des chemins de fichiers.

Ce module fournit des fonctions pour manipuler les noms de fichiers et de dossiers,
notamment pour la sanitisation des e-mails d'utilisateurs.
"""

import re

def sanitize_email(email: str) -> str:
    """
    Sanitise une adresse e-mail pour l'utiliser comme nom de dossier.
    
    Remplace le '@' par '_at_' et tout caractère non alphanumérique par '_'.
    Convertit le résultat en minuscules.

    Args:
        email: L'adresse e-mail à sanitiser.

    Returns:
        L'adresse e-mail sanitisée.
    """
    # Remplacer '@' par '_at_'
    sanitized = email.replace('@', '_at_')
    
    # Remplacer tout ce qui n'est pas alphanumérique par '_'
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', sanitized)
    
    return sanitized.lower()
