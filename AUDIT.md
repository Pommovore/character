# Audit du Code — Extracteur de Traits de Caractère

**Date** : 27 février 2026  
**Version** : 0.1.0  

---

## 1. Vue d'ensemble

| Élément | Détail |
|---|---|
| **Langage** | Python 3.12+ (`.python-version`), Dockerfile cible 3.10 |
| **Framework** | FastAPI + Uvicorn |
| **IA** | Hugging Face Transformers (zero-shot classification) |
| **Tests** | pytest + pytest-asyncio (20 tests) |
| **Gestion dépendances** | `uv`, `requirements.txt` / `requirements-dev.txt` |

---

## 2. Résumé des Constats

| Sévérité | Nombre |
|---|---|
| 🔴 Critique | 3 |
| 🟠 Majeur | 5 |
| 🟡 Mineur | 7 |
| 💡 Suggestion | 4 |

---

## 3. Constats Critiques (🔴)

### 3.1 CORS sans restriction — `api.py:42-48`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Risque** : `allow_origins=["*"]` combiné avec `allow_credentials=True` est une faille de sécurité. N'importe quel site peut effectuer des requêtes authentifiées vers l'API.  
**Recommandation** : Définir les origines autorisées via variable d'environnement (`ALLOWED_ORIGINS`). Désactiver `allow_credentials` si le wildcard est utilisé.

### 3.2 Stockage en mémoire sans limite ni nettoyage — `character_store.py`

Les résultats sont stockés dans un dictionnaire en mémoire (`self.results`, `self.pending_requests`) sans aucune limite de taille ni mécanisme de nettoyage actif. La méthode `cleanup_old_results` est vide (`pass`).

**Risque** : Fuite de mémoire progressive — en production, le processus finira par manquer de RAM.  
**Recommandation** : 
- Implémenter un TTL avec timestamps sur chaque résultat.
- Ajouter une tâche périodique (ex: `BackgroundTask` FastAPI ou `asyncio.create_task`) pour le nettoyage.
- Ou utiliser Redis / un cache externe avec TTL natif.

### 3.3 Pas de gestion d'erreur pour les tâches échouées — `character_store.py:102-107`

Quand `process_func()` lève une exception dans `process_async`, la demande est retirée de `pending_requests` mais aucun résultat d'erreur n'est stocké. Le client qui interroge `/get_character/{request_id}` recevra un 404 (`"inconnu"`) sans indication que le traitement a échoué.

**Recommandation** : Stocker un objet d'erreur ou un statut `"failed"` avec le message d'erreur, et le remonter au client via un code HTTP 500 ou un champ `error` dans la réponse.

---

## 4. Constats Majeurs (🟠)

### 4.1 Double `import os` et hack `sys.path` — `src/main.py:8-14`

```python
import os       # Ligne 8
import sys
import os       # Ligne 11 — doublon

sys.path.insert(0, os.path.abspath(...))
```

**Problème** : Import dupliqué et manipulation de `sys.path` inutile si le projet est correctement installé ou si `PYTHONPATH` est configuré (comme c'est le cas dans le Dockerfile).  
**Recommandation** : Supprimer le doublon et le hack `sys.path`. Utiliser `uv run` ou `pip install -e .` pour la résolution de modules.

### 4.2 Incohérence de version Python — `Dockerfile` vs `.python-version`

- `.python-version` : `3.12`
- `Dockerfile` : `python:3.10-slim`
- `pyproject.toml` : `requires-python = ">=3.10"`

**Recommandation** : Aligner le Dockerfile sur `python:3.12-slim` pour correspondre à l'environnement de développement.

### 4.3 Cache global mutable thread-unsafe — `traits_endpoints.py:31`

```python
extractors = {}
```

Le dictionnaire global `extractors` est accédé en lecture/écriture depuis `get_extractor()` sans verrou, alors que le `ThreadPoolExecutor` de `CharacterStore` exécute des traitements concurrents qui utilisent les extractors.

**Recommandation** : Ajouter un verrou (`threading.Lock`) autour de l'accès au cache `extractors`, ou utiliser `functools.lru_cache` sur `get_extractor`.

### 4.4 Point d'entrée racine inutile — `main.py` (racine)

Le fichier `main.py` à la racine du projet contient uniquement `print("Hello from charactere!")` — il semble être un artéfact du scaffolding initial et ne sert à rien.

**Recommandation** : Supprimer ou remplacer par un point d'entrée qui délègue à `src.main:main`.

### 4.5 `pyproject.toml` incomplet

```toml
[project]
name = "charactere"  # Typo : « charactere » au lieu de « character »
dependencies = []     # Vide alors que requirements.txt contient 9 dépendances
```

**Recommandation** : 
- Corriger le nom du projet.
- Synchroniser les dépendances avec `requirements.txt` ou migrer vers `[project.dependencies]` comme source unique.
- Ajouter les métadonnées manquantes (auteur, licence, etc.).

---

## 5. Constats Mineurs (🟡)

### 5.1 Logging configuré deux fois

`logging.basicConfig()` est appelé à la fois dans `src/main.py:19` et `src/api/api.py:15`. Seul le premier appel a un effet, les suivants sont ignorés.

**Recommandation** : Centraliser la configuration du logging dans un seul endroit (ex: `src/main.py`).

### 5.2 Imports non utilisés — `traits_endpoints.py`

- `Optional`, `Dict` (ligne 8) — jamais utilisés.
- `asyncio` (ligne 9) — jamais utilisé.
- `Path`, `Query` (ligne 11) — jamais utilisés.
- `JSONResponse` (ligne 12) — jamais utilisé.
- `CharacterRequestId` (ligne 18) — jamais utilisé.

### 5.3 `.gitignore` incomplet

Manquent : `.env`, `.idea/`, `.vscode/`, `*.sqlite3`, `.pytest_cache/`, `.mypy_cache/`, `htmlcov/`, `.coverage`.

### 5.4 Seuil de confiance en dur — `traits_extractor.py:91`

```python
if score > 0.3:
```

Le seuil de 0.3 est codé en dur. Il devrait être configurable via paramètre ou variable d'environnement.

### 5.5 Absence de rate limiting

L'API n'a pas de mécanisme de limitation du nombre de requêtes. Un client peut envoyer un grand nombre de requêtes et saturer le `ThreadPoolExecutor` (limité à 5 workers).

### 5.6 Pas de validation de `request_id` 

Le `request_id` est un `str` sans contrainte de format. Un client pourrait envoyer des IDs très longs ou contenant des caractères spéciaux.

**Recommandation** : Ajouter une contrainte `max_length` et un pattern regex dans le modèle Pydantic.

### 5.7 Utilisation de HTTP 202 comme exception — `traits_endpoints.py:162`

```python
raise HTTPException(status_code=202, detail="Traitement en cours")
```

HTTP 202 n'est pas une erreur ; lever une `HTTPException` avec ce code est sémantiquement incorrect.

**Recommandation** : Retourner directement une `JSONResponse(status_code=202, content=...)`.

---

## 6. Suggestions (💡)

### 6.1 Ajouter un fichier `.env.example`

Documenter les variables d'environnement attendues (`HOST`, `PORT`, `HF_TOKEN`, `ALLOWED_ORIGINS`).

### 6.2 Ajouter un healthcheck dans le Dockerfile

```dockerfile
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health || exit 1
```

### 6.3 Configurer la CI/CD

Ajouter un workflow GitHub Actions (`.github/workflows/`) pour exécuter les tests automatiquement sur chaque push/PR.

### 6.4 Ajouter des tests de charge

Utiliser `locust` ou `k6` pour valider le comportement sous charge avant la mise en production.

---

## 7. Conformité aux PROJECT_RULES.md

| Règle | Conformité | Note |
|---|---|---|
| Code en anglais | ✅ | Variables, fonctions et classes en anglais |
| Commentaires/docstrings en français | ✅ | Tous les docstrings sont en français |
| Logique métier dans les Services | ✅ | `TraitsExtractor` et `CharacterStore` sont séparés |
| Gestion des erreurs try/except | ✅ | Présent dans les endpoints et services |
| Modèles Pydantic | ✅ | Définis dans `character_traits.py` |
| Code propre, pas de `print` de debug | ⚠️ | `main.py` racine contient un `print()` |

---

## 8. Arborescence du projet

```
character/
├── main.py                          # ⚠️ Artéfact inutile
├── Dockerfile
├── pyproject.toml                   # ⚠️ Incomplet
├── requirements.txt
├── requirements-dev.txt
├── docs/
│   ├── README.md
│   └── USAGE.md
├── src/
│   ├── __init__.py
│   ├── main.py                      # Point d'entrée Uvicorn
│   ├── api/
│   │   ├── api.py                   # Factory FastAPI
│   │   └── traits_endpoints.py      # Routes /api/v1/traits/*
│   ├── models/
│   │   └── character_traits.py      # Modèles Pydantic
│   ├── services/
│   │   ├── character_store.py       # Stockage résultats (singleton)
│   │   └── traits_extractor.py      # Extraction IA
│   └── utils/
│       └── url_fetcher.py           # Détection/téléchargement URL
└── tests/
    ├── test_character_store.py
    ├── test_traits_api.py
    ├── test_traits_extractor.py
    └── test_url_fetcher.py
```

---

## 9. Couverture de tests

| Module | Tests | Couverture estimée |
|---|---|---|
| `url_fetcher.py` | 14 tests | ✅ Bonne |
| `traits_api` | 6 tests | ✅ Bonne |
| `character_store` | 4 tests | ⚠️ Moyenne (pas de test d'erreur) |
| `traits_extractor` | 3 tests | ⚠️ Moyenne (pas de test edge case) |

**Tests manquants** :
- Gestion d'erreur dans `process_async` (quand `process_func` échoue)
- Comportement du singleton `CharacterStore` entre les tests (état partagé)
- Test de la route `GET /get_character/{request_id}` (pas de test dédié)
- Test du endpoint `/health`
- Tests d'intégration bout-en-bout
