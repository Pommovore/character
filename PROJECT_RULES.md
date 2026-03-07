# Règles et Conventions des projets développés avec ANTIGRAVITY

Ce document définit les standards de développement, l'architecture et les workflows à respecter pour maintenir la cohérence et la qualité du projet.

## 1. Technologies Principales

*   **Backend** : Python 3.12+ avec FastAPI.
*   **Base de données** : SQLite (Dev/Test/Prod) via SQLAlchemy.
*   **Frontend** : HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5.3.
*   **Gestionnaire de dépendances** : `uv`.

## 2. Architecture & Organisation du Code

### Backend
*   **Structure Modulaire** : Utiliser les **APIRouter** de FastAPI pour organiser les routes par domaine fonctionnel (ex: `routes/admin_routes.py`, `routes/user_routes.py`).
*   **Logique Métier** : Déporter la logique complexe dans des **Services** (`services/`) plutôt que de la laisser dans les routes.
*   **Modèles** : Définis dans `models/` avec SQLAlchemy ORM. Validation assurée par Pydantic.
*   **Gestion des Erreurs** : Utiliser `HTTPException` pour les requêtes API et retourner des affichages pertinents côté frontend via le contexte Jinja2.
*   **Cycle de vie** : Utiliser le context manager `lifespan` pour la gestion propre des connexions et pools (pas de `@app.on_event` déprécié).

### Frontend
*   **Framework UI** : **Bootstrap 5** est le standard. Ne pas introduire d'autres frameworks CSS lourds (ex: Tailwind) sans validation.
*   **Icônes** : Utiliser **Bootstrap Icons** (`bi bi-nom-icone`).
*   **Templating** : Jinja2. Utiliser l'héritage de templates (`{% extends "base.html" %}`).
*   **JavaScript** : Écrire du JS moderne (ES6+). Placer les scripts spécifiques dans `static/js/`. Echapper le contenu dynamique (`escapeHtml()`) avant d'utiliser `.innerHTML`.

## 3. Conventions de Nommage et Langue

*   **Code (Variables, Fonctions, Classes)** : Anglais (`get_user`, `Event`, `is_admin_mode`).
*   **Commentaires et Docstrings** : Français (pour faciliter la compréhension par l'équipe).
*   **Interfaces Utilisateur (UI)** : Français.
*   **Base de Données** : Noms de tables et colonnes en Anglais (`user`, `event_id`, `created_at`).

## 4. Base de Données

*   **Migrations** : Utiliser **Alembic pur** ou initialisation automatique (`create_all` pour SQLite simple). (Pas de Flask-Migrate).
    *   Toute nouvelle table doit lier un modèle Pydantic de validation.
*   **Contraintes** : Définir explicitement les Foreign Keys et Index.
*   **Concurrence SQLite** : En contexte asynchrone multithread (API + File d'attente), utiliser `NullPool` avec `check_same_thread=False` pour éviter les situations de *database is locked*.

## 5. Workflow de Développement

### Démarrage
*   Exécuter les instructions via le gestionnaire de dépendances `uv`.
*   Lancer le serveur : `uv run run.py` (ou `uv run uvicorn src.main:app` selon configuration du Root Path).

### Déploiement
*   Utiliser le script `deploy.py`.
*   **NE PAS** modifier les fichiers directement sur le serveur de production.
*   Toujours tester en local (`--dev`) avant de déployer en production.
*   Commande journalière (mise à jour légère du code) : `uv run python deploy.py --update`.
*   Commande globale (Mise à jour code + config Nginx/Systemd) : `uv run python deploy.py --prod`.
*   Se baser sur le fichier de configuration `config/deploy.conf` pour les paramètres de déploiement.

## 6. Bonnes Pratiques

*   **Sécurité** :
    *   Utiliser l'injection de dépendances idiomatique de FastAPI (`Depends(get_current_user)`, `Depends(require_admin)`).
    *   Protéger tous les formulaires POST naviguables HTML avec le middleware CSRF (`starlette-csrf`) et `<input type="hidden" name="csrf_token" value="{{ csrf_token(request) }}">`.
*   **Monitoring** : Utiliser un journal de logs (`RequestLog`) pour tracer et limiter (Rate Limiting) l'utilisation de l'API par token.
*   **Code Propre** : Supprimer le code mort (imports non utilisés, commentaires obsolètes) et utiliser les analyseurs statiques (`flake8`, `mypy`) via la suite d'outils de dév `uv`.
