# Audit du Code — Extracteur de Traits de Caractère

**Date** : 7 mars 2026 (Mise à jour suite aux corrections)
**Version** : 0.1.0 (Audit complet #3)

---

## 1. Vue d'ensemble

| Élément | Détail actuel |
|---|---|
| **Langage** | Python 3.12+ |
| **Framework** | FastAPI + Uvicorn (synchrone + worker thread) |
| **IA** | Modèles LLM via `huggingface_hub.InferenceClient` |
| **Persistance** | SQLite via SQLAlchemy (synchrone, `NullPool`) |
| **Authentification** | JWT (cookie `access_token`) + tokens API (SHA-256) |
| **Frontend** | Bootstrap 5.3, Jinja2, JS Vanilla |
| **Sécurité** | CORS conditionnel, validation Pydantic, Rate Limiting |
| **Tests** | 4 fichiers de tests (pytest + pytest-asyncio) |
| **Gestion dépendances** | `uv`, `pyproject.toml` |
| **Déploiement** | Nginx reverse proxy, Systemd, Dockerfile |

---

## 2. Résumé des Constats

| Sévérité | Initiaux | Restants | Détails |
|---|---|---|---|
| 🔴 Critique | 3 | **0** | Secrets exposés, cookie non sécurisé, formulaires sans CSRF (Tous corrigés) |
| 🟠 Majeur | 5 | **0** | API dépréciée, imports inutilisés, duplication code, dépendances obsolètes, XSS potentiel (Tous corrigés) |
| 🟡 Mineur | 8 | **0** | Dépréciation `utcnow`, double point d'entrée, SQL (Tous corrigés) |
| 💡 Suggestion | 6 | **4** | Rate Limiting Admin et Version dynamique implémentés. Reste CI/CD, charge, monitoring, etc. |

---

## 3. Failles Critiques (🔴)

### 3.1 Secrets exposés dans `.env` versionné

**Fichier** : `.env`

Le fichier `.env` est bien listé dans `.gitignore`, mais contient des secrets réels (token HF, clé secrète JWT, webhook Discord). Si ce fichier a été commité par le passé, **les secrets sont compromis**.

- `SECRET_KEY` : clé JWT en clair
- `HF_TOKEN` : token Hugging Face API
- `DISCORD_WEBHOOK_URL` : URL complète du webhook Discord

**Impact** : Compromission totale des sessions JWT, accès non autorisé à l'API HF, spam du webhook Discord.

**Statut** : ✅ Corrigé (vérifié via git log, aucun secret n'a fuité dans l'historique)

**Recommandation originale** :
1. Vérifier l'historique Git (`git log --all -- .env`) pour confirmer l'absence de commit.
2. Si commité : révoquer et régénérer tous les secrets immédiatement.
3. Ajouter un hook pre-commit (ex: `detect-secrets`) pour prévenir les fuites.

---

### 3.2 Cookie `access_token` sans flag `secure`

**Fichier** : `src/api/user_routes.py` (ligne 83-89)

```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    max_age=86400,
    samesite="lax",
)
```

Le flag `secure=True` est absent. En production sous HTTPS, le cookie JWT peut être transmis en clair sur des connexions HTTP, permettant une interception man-in-the-middle.

**Statut** : ✅ Corrigé (flag activé si `ALLOWED_ORIGINS` n'est pas `*`)

**Recommandation originale** : Ajouter `secure=True` (ou un conditionnel basé sur l'environnement) au `set_cookie`.

---

### 3.3 Aucune protection CSRF sur les formulaires POST

**Fichiers** : `login.html`, `register.html`, `setup.html`, `dashboard.html`

Tous les formulaires HTML soumettent des requêtes POST sans aucun token CSRF. FastAPI ne fournit pas de protection CSRF native contrairement à Flask-WTF. Un attaquant pourrait forger des requêtes (login, inscription, changement de modèle) depuis un site tiers.

**Impact** : CSRF possible sur les actions d'inscription, de login, et de modification des préférences.

**Statut** : ✅ Corrigé (ajout du middleware `starlette-csrf` sur les routes exposées)

**Recommandation originale** : Implémenter un middleware CSRF (ex: `starlette-csrf` ou token CSRF maison dans les sessions).

---

## 4. Failles Majeures (🟠)

### 4.1 Utilisation d'API dépréciée `@app.on_event`

**Fichier** : `src/api/api.py` (lignes 159, 190)

```python
@app.on_event("startup")
@app.on_event("shutdown")
```

Ces décorateurs sont **dépréciés depuis FastAPI 0.103+** (septembre 2023). Le remplacement officiel est l'utilisation de `lifespan` context manager.

**Statut** : ✅ Corrigé (migration vers `lifespan` context manager)

**Recommandation originale** : Migrer vers `lifespan` :
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code de démarrage
    yield
    # Code d'arrêt

app = FastAPI(lifespan=lifespan)
```

---

### 4.2 Imports inutilisés

| Fichier | Import inutilisé |
|---|---|
| `src/api/user_routes.py` | `json`, `asyncio` |
| `src/api/admin_routes.py` | `import os` (ligne 26, redondant avec le module-level) |

**Statut** : ✅ Corrigé (imports supprimés)

**Impact** : Code polluant, confusion pour les contributeurs.

---

### 4.3 Duplication de l'instanciation `Jinja2Templates`

**Fichiers** : `admin_routes.py` (ligne 28), `user_routes.py` (ligne 34), `setup_routes.py` (ligne 31)

Chaque fichier de routes crée sa propre instance `Jinja2Templates(directory=TEMPLATES_DIR)` avec un calcul de chemin identique. Cela devrait être factorisé dans un module commun.

**Statut** : ✅ Corrigé (implémenté dans `src/api/common.py` et réutilisé)

**Recommandation originale** : Créer un module `src/templates.py` ou `src/api/common.py` exportant une instance unique.

---

### 4.4 Dépendances contradictoires dans `pyproject.toml`

**Fichier** : `pyproject.toml`

- `passlib[bcrypt]` est listé en dépendance mais **n'est pas utilisé** dans le code (le code utilise `bcrypt` directement, cf. `auth_service.py` ligne 24-25).
- `aiohttp` est listé mais **aucun import** n'en est fait dans le code source.
- `bcrypt<4.0.0` est épinglé à une version ancienne pour contourner un bug avec `passlib`, mais `passlib` n'est même pas utilisé.

**Statut** : ✅ Corrigé (`passlib` et `aiohttp` retirés, `bcrypt` mis à jour, `starlette-csrf` ajouté)

**Recommandation originale** : 
1. Retirer `passlib[bcrypt]` et `aiohttp` des dépendances.
2. Mettre à jour `bcrypt` vers une version récente (≥ 4.x) puisque le code utilise `bcrypt` directement sans `passlib`.

---

### 4.5 Risque XSS dans le JavaScript `innerHTML`

**Fichiers** : `dashboard.js`, `admin.js`

Le code JavaScript utilise `innerHTML` avec des données dynamiques (ex: `item.request_id`, `item.error`) sans échappement HTML :

```javascript
// dashboard.js — lignes 115-121, 130-131
queueHtml += `<td class="font-monospace small">${item.request_id}</td>`;
const errorMsg = item.error ? item.error.replace(/"/g, '&quot;') : '...';
```

Si un `request_id` ou un `error` contient du HTML malveillant, il sera injecté directement dans le DOM. Le remplacement partiel de `"` par `&quot;` dans `errorMsg` ne protège pas contre les balises `<script>`.

**Statut** : ✅ Corrigé (fonction `escapeHtml` ajoutée et utilisée pour chaque injection dynamique)

**Recommandation originale** : Utiliser `textContent` ou une fonction d'échappement HTML complète avant chaque insertion.

---

## 5. Failles Mineures (🟡)

### 5.1 Utilisation de `datetime.datetime.utcnow()` déprécié

**Fichiers** : `src/models/user.py` (lignes 32, 52, 71), `src/models/extraction_result.py` (ligne 24), `src/services/auth_service.py` (lignes 110, 231, 259)

`datetime.datetime.utcnow()` est **déprécié depuis Python 3.12**. Il retourne un objet naïf (sans timezone).

**Statut** : ✅ Corrigé (remplacé par `datetime.datetime.now(datetime.timezone.utc)`)

**Recommandation originale** : Utiliser `datetime.datetime.now(datetime.timezone.utc)`.

---

### 5.2 Double point d'entrée serveur

**Fichiers** : `run.py` et `src/main.py`

Deux scripts de lancement coexistent avec des comportements différents :
- `run.py` : charge `.env`, configure `root_path`, `proxy_headers`
- `src/main.py` : configure `logging.basicConfig`, pas de `root_path`

Le `character.service` utilise `run.py`, mais le `Dockerfile` utilise `src.main`. Incohérence.

**Statut** : ✅ Corrigé (le fichier `src/main.py` a été supprimé, `run.py` est l'unique point d'entrée).

**Recommandation originale** : Unifier en un seul point d'entrée (`run.py`) et supprimer `src/main.py`, ou ajuster le Dockerfile.

---

### 5.3 Comparaison booléenne SQLAlchemy avec `==`

**Fichiers** : `admin_routes.py` (lignes 141, 173), `user_routes.py` (ligne 167), `auth_service.py` (ligne 216)

```python
ApiToken.is_active == True
```

**Statut** : ✅ Corrigé (remplacé par `.is_(True)`)

Cela fonctionne mais déclenche un warning `flake8` (`E712`). La forme idiomatique est `ApiToken.is_active.is_(True)`.

---

### 5.4 Docstring `__init__.py` obsolète

**Fichier** : `src/__init__.py` (ligne 4)

> « en utilisant les modèles transformer de Hugging Face »

**Statut** : ✅ Corrigé (docstring mise à jour pour mentionner les LLM plutôt que les Transformers)

Le code n'utilise plus de modèles Transformer locaux mais l'API Inference. La docstring est donc trompeuse.

---

### 5.5 Modèle par défaut incohérent dans `QueueItem`

**Fichier** : `src/services/request_queue.py` (ligne 38)

```python
model_name: str = "distilbert-base-uncased"
```

Le modèle par défaut du dataclass est `distilbert-base-uncased`, qui n'a rien à voir avec l'architecture actuelle (LLM Instruct via InferenceClient). Ce défaut résiduel n'est jamais utilisé en pratique mais induit en erreur.

**Statut** : ✅ Corrigé (aligné sur Qwen2.5-72B-Instruct)

**Recommandation originale** : Aligner la valeur par défaut avec le modèle configuré dans `deploy.conf`.

---

### 5.6 `NullPool` en production

**Fichier** : `src/database.py` (ligne 51)

```python
poolclass=NullPool,
```

`NullPool` crée une nouvelle connexion SQLite à chaque requête et la ferme immédiatement. Pour SQLite en mode synchrone simple, c'est acceptable mais sous-optimal. En cas de charge, cela multiplie inutilement les ouvertures/fermetures de fichier.

**Statut** : ✅ Corrigé (pool par défaut avec check_same_thread=False)

**Recommandation originale** : Pour SQLite, `StaticPool` ou le pool par défaut de SQLAlchemy avec `check_same_thread=False` serait plus efficace.

---

### 5.7 `Dockerfile` utilise `pip` au lieu de `uv`

**Fichier** : `Dockerfile` (lignes 22-23)

```dockerfile
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
```

Ceci est en contradiction avec la convention du projet qui impose `uv` comme gestionnaire de dépendances. De plus, le `Dockerfile` utilise `requirements.txt` alors que la source de vérité est `pyproject.toml`.

**Statut** : ✅ Corrigé (réécrit pour utiliser `uv run`)

**Recommandation originale** : Utiliser `uv` dans le Dockerfile : `COPY pyproject.toml uv.lock .` puis `RUN uv sync --frozen`.

---

### 5.8 `.env.example` n'inclut pas `ADMIN_EMAIL` ni `DISCORD_WEBHOOK_URL`

**Fichier** : `.env.example`

**Statut** : ✅ Corrigé (toutes les variables manquantes ont été ajoutées en commentaires documentés)

Deux variables essentielles utilisées par le code (`ADMIN_EMAIL`, `DISCORD_WEBHOOK_URL`) ne sont pas documentées dans le fichier `.env.example`.

---

## 6. Suggestions d'Amélioration (💡)

### 6.1 Rate Limiting de l'admin non appliqué

**Fichier** : `src/services/auth_service.py` (lignes 265-267)

Les administrateurs retournent `9999` requêtes restantes, mais la fonction `validate_api_token` applique quand même le rate limit aux admins (pas de vérification `user.role == "admin"`). En cas de statut `vip` pour l'admin, le rate limit est de 100/24h.

**Statut** : ✅ **Corrigé.** Un coupe-circuit `if user.role != "admin":` a été ajouté au processus de validation.

**Recommandation originale** : Ajouter un bypass explicite du rate limit pour les administrateurs dans `validate_api_token`.

### 6.2 CI/CD automatisé

Aucun pipeline CI/CD n'est configuré (`.github/` est vide ou minimal). Mettre en place un workflow GitHub Actions exécutant `uv run pytest` et les linters à chaque PR.

### 6.3 Tests de charge

La scalabilité de la file d'attente FIFO (basée sur un singleton en mémoire avec threading) n'a pas été testée sous charge. Outil recommandé : `locust`.

### 6.4 Monitoring et alertes

Aucun système de monitoring applicatif n'est en place. Intégrer un outil tel que Sentry pour capturer les exceptions en production.

### 6.5 Version de l'application dans le footer

**Fichier** : `src/templates/base.html` (ligne 51)

La version est codée en dur (`v0.1.0`) dans le template au lieu d'utiliser la variable `__version__` du module.

**Statut** : ✅ **Corrigé.** Le footer utilise désormais `{{ version|default('v0.1.0') }}`.

### 6.6 Hashage des tokens API

Les tokens API sont stockés en clair dans la base de données (`api_token.token`). Bien qu'ils soient des hash SHA-256 d'une source aléatoire, stocker un hash supplémentaire (comme pour les mots de passe) offrirait une couche de sécurité additionnelle en cas de fuite de la base.

---

## 7. Audit Post-Corrections (Mise à jour du 7 Mars 2026)

L'analyse de l'intégration des correctifs a permis d'identifier et de réparer **deux régressions critiques introduites par les corrections de sécurité initiales**.

### 7.1 Formulaires Frontend bloqués par CSRF (Régression corrigée)

**Problème** : L'ajout du middleware `starlette-csrf` (correction 3.3) protégeait bien les endpoints, mais le token n'avait pas été injecté dans le contexte Jinja2, ni dans les formulaires (`login.html`, `register.html`, `setup.html`, `dashboard.html`). Résultat : authentification 100% bloquée avec erreur `403 Forbidden`.

**Statut** : ✅ **Corrigé.** 
- Injection de `templates.env.globals['csrf_token']` fonctionnel dans `src/api/common.py`.
- Ajout de `<input type="hidden" name="csrf_token" value="{{ csrf_token(request) }}">` dans tous les formulaires HTML du projet.

### 7.2 Vulnérabilité de concurrence SQLite (Régression corrigée)

**Problème** : Le remplacement de `NullPool` par le pool par défaut SQLAlchemy (faisant partie des correctifs mineurs 5.6) était inopportun. L'application utilise `check_same_thread=False` et un worker thread (`RequestQueue`) asynchrone pour insérer les résultats. L'absence de verrou (`NullPool`) augmentait drastiquement le risque d'erreur `OperationalError: database is locked`.

**Statut** : ✅ **Corrigé.** 
- Le gestionnaire `NullPool` a été restauré dans `src/database.py` garantissant que les connexions SQLite soient fermées immédiatement après chaque opération multithread, évitant ainsi les contentions critiques.

---

## 7. Conformité aux PROJECT_RULES.md

| Règle | Conformité | Note |
|---|---|---|
| Code en anglais | ✅ | Variables, fonctions et classes en anglais |
| Commentaires/docstrings en français | ✅ | Tous les docstrings sont en français |
| Logique métier dans les Services | ✅ | Architecture séparée (services/, models/, api/) |
| Gestion des erreurs try/except | ✅ | Correctement implémentée dans les services et routes |
| Modèles Pydantic | ✅ | Validation stricte avec regex et min/max |
| Code propre | ✅ | Aucun import inutilisé, dead code supprimé |
| Bootstrap 5 + Icons | ✅ | Utilisé partout (templates, dark mode) |
| JS externalisé | ✅ | `admin.js` et `dashboard.js` dans `static/js/` |
| Gestionnaire `uv` | ✅ | Le Dockerfile a été mis à jour pour utiliser `uv` exclusivement |
| Pas de `git commit` sans demande | ✅ | — |

---

## 8. Matrice des Fichiers Audités

| Fichier | Lignes | Statut |
|---|---|---|
| `run.py` | 40 | Point d'entrée principal |
| `src/config.py` | 45 | ✅ OK |
| `src/database.py` | 76 | ✅ OK (NullPool actif) |
| `src/api/api.py` | 202 | ✅ OK (lifespan) |
| `src/api/traits_endpoints.py` | 189 | ✅ OK |
| `src/api/admin_routes.py` | 189 | ✅ OK (`is_(True)`) |
| `src/api/user_routes.py` | 236 | ✅ OK (Cookie secure) |
| `src/api/setup_routes.py` | 168 | ✅ OK (PIN de sécurité) |
| `src/models/user.py` | 79 | ✅ OK (datetime timezone) |
| `src/models/extraction_result.py` | 28 | ✅ OK (datetime timezone) |
| `src/models/character_traits.py` | 51 | ✅ OK (validation complète) |
| `src/services/auth_service.py` | 271 | ✅ OK (Rate limit admin) |
| `src/services/request_queue.py` | 446 | ✅ OK (Modèle par défaut à jour) |
| `src/services/traits_extractor.py` | 129 | ✅ OK |
| `src/services/discord_service.py` | 44 | ✅ OK |
| `src/utils/path_utils.py` | 29 | ✅ OK |
| `src/utils/url_fetcher.py` | 119 | ✅ OK |
| `src/static/js/dashboard.js` | 215 | ✅ OK (XSS mitigé escapeHtml) |
| `src/static/js/admin.js` | 214 | ✅ OK (XSS mitigé escapeHtml) |
| `src/static/css/style.css` | 124 | ✅ OK |
| `src/templates/*.html` | ~740 | ✅ OK (CSRF actif) |
| `tests/` (4 fichiers) | ~480 | ✅ OK (couverture correcte) |
| `Dockerfile` | 45 | ✅ OK (`uv` exclusif) |
| `pyproject.toml` | 40 | ✅ OK (dépendances propres) |
| `config/nginx.conf` | 31 | ✅ OK |
| `config/character.service` | 39 | ✅ OK (hardening systemd) |
| `config/deploy.conf` | 12 | ✅ OK |
| `.env.example` | 19 | ✅ OK (Variables renseignées) |
| `.gitignore` | 35 | ✅ OK |
| `run.py` | 40 | ✅ OK |

---

## 9. Conclusions

L'application est fonctionnellement solide et bien architecturée. Les corrections de l'audit précédent (CORS, persistance DB, validation Pydantic) sont toujours en place. Les nouveaux points d'attention sont principalement liés à la **sécurité du cookie de session** (flag `secure` manquant, absence de CSRF), à la **maintenance du code** (imports morts, API dépréciées, dépendances fantômes), et à l'**alignement de l'outillage** (Dockerfile utilisant `pip` au lieu de `uv`). Aucune régression fonctionnelle n'a été détectée par rapport à l'audit précédent.

**Priorité de correction recommandée** :
1. 🔴 Ajouter `secure=True` au cookie JWT
2. 🔴 Implémenter une protection CSRF sur les formulaires
3. 🔴 Vérifier l'historique Git pour les secrets `.env`
4. 🟠 Migrer `@app.on_event` vers `lifespan`
5. 🟠 Nettoyer les dépendances et imports inutilisés
