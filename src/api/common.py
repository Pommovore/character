"""Module partagé pour les ressources communes aux routes.

Ce module fournit une instance unique de Jinja2Templates
utilisée par tous les fichiers de routes.
"""

import os

from fastapi.templating import Jinja2Templates

# Chemin unique vers le répertoire de templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

# Instance partagée de Jinja2Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Exposer une fonction pour récupérer le token CSRF aux templates
templates.env.globals['csrf_token'] = lambda request: (
    request.scope.get("csrftoken")() 
    if callable(request.scope.get("csrftoken")) 
    else request.scope.get("csrftoken", "")
)
