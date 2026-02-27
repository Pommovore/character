# Architecture de l'Extracteur de Traits de Caractère

Ce document détaille l'architecture et les fonctions implémentées dans l'application Extracteur de Traits de Caractère.

## Structure du Projet

```
extracteur-traits-caractere/
├── .github/            # Workflows GitHub pour CI/CD
├── docs/               # Documentation
├── src/                # Code source
│   ├── api/            # Points de terminaison API
│   ├── models/         # Modèles Pydantic
│   ├── services/       # Logique métier
│   └── utils/          # Utilitaires
├── tests/              # Fichiers de test
├── Dockerfile          # Configuration Docker
└── requirements.txt    # Dépendances
```

## Architecture Globale

L'application est construite selon une architecture en couches:

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Requests
┌──────▼──────┐
│     API     │ <── Validation (Pydantic)
└──────┬──────┘
       │
┌──────▼──────┐
│  Services   │ <── Business Logic
└──────┬──────┘
       │
┌──────▼──────┐
│ AI Models   │ <── Hugging Face
└─────────────┘
```

### Flux d'Exécution Asynchrone

```
1. Client soumet une analyse (request_id) ──> API
2. API ──> Retourne immédiatement HTTP 202 au client
3. API ──> Démarre un traitement asynchrone (ThreadPool)
4. Client demande résultat (request_id) ──> API
5. API ──> Vérifie si traitement terminé
6. Si terminé ──> Retourne résultats (HTTP 200)
   Si en cours ──> Retourne "en cours" (HTTP 202)
   Si inconnu ──> Retourne "inconnu" (HTTP 404)
```

## Composants Principaux

### 1. API Layer (`src/api/`)

#### 1.1. `api.py`
- Configure l'application FastAPI
- Gère les middlewares CORS
- Configure les routes API
- Fournit un endpoint `/health` pour la surveillance

#### 1.2. `traits_endpoints.py`
- Définit les routes pour l'extraction de traits
- Implémente le point d'entrée asynchrone
- Gère la récupération des résultats

**Endpoints:**
- `POST /api/v1/traits/extract`: Soumet une demande d'analyse
- `GET /api/v1/traits/get_character/{request_id}`: Récupère les résultats
- `GET /health`: Vérifie l'état de l'API

### 2. Service Layer (`src/services/`)

#### 2.1. `traits_extractor.py`
- Implémente la logique d'extraction des traits
- Utilise les modèles Hugging Face pour l'analyse
- Catégorise les traits par type
- Génère des résumés basés sur les traits extraits

#### 2.2. `character_store.py`
- Implémente un stockage en mémoire pour les résultats
- Fournit un mécanisme de traitement asynchrone
- Gère l'état des demandes (pending/completed)
- Utilise le pattern Singleton pour le partage d'état

### 3. Model Layer (`src/models/`)

#### 3.1. `character_traits.py`
- Définit les schémas de données avec Pydantic
- Valide les entrées et sorties de l'API
- Fournit les structures pour les traits de caractère

**Modèles clés:**
- `CharacterDescription`: Structure d'entrée pour l'analyse
- `CharacterTrait`: Représentation d'un trait individuel
- `CharacterTraitsResponse`: Structure de résultat d'analyse
- `CharacterProcessingStatus`: État de traitement d'une demande

## Fonctionnalités Implémentées

### 1. Traitement Asynchrone

La fonctionnalité permet de démarrer une analyse et de récupérer les résultats ultérieurement:

```python
def process_async(self, request_id: str, process_func: Callable[[], Any]) -> None:
    self.register_pending_request(request_id)
    
    def _wrapper():
        try:
            result = process_func()
            self.store_result(request_id, result)
        except Exception as e:
            logger.error(f"Erreur lors du traitement: {str(e)}")
    
    self.executor.submit(_wrapper)
```

### 2. Système de Directives

L'API accepte des directives pour orienter l'analyse des personnages:

```python
def extract_traits(self, text: str, directive: Optional[str] = None) -> List[CharacterTrait]:
    if directive:
        logger.info(f"Directive fournie pour l'extraction : {directive}")
        # Utilisation de la directive pour guider le modèle
```

### 3. Gestion d'État des Demandes

Le système suit l'état des demandes avec une gestion thread-safe:

```python
def is_request_known(self, request_id: str) -> bool:
    with self.lock:
        return request_id in self.results or request_id in self.pending_requests
```

### 4. Classification des Traits

Les traits sont catégorisés selon une taxonomie prédéfinie:

```python
TRAIT_CATEGORIES = {
    "Personnalité": [
        "Courageux", "Ambitieux", "Intelligent", "Compatissant", ...
    ],
    "Valeurs": [
        "Honnête", "Fiable", "Juste", "Honorable", ...
    ],
    "Émotions": [
        "Joyeux", "Craintif", "Colérique", "Mélancolique", ...
    ]
}
```

### 5. Limitation de Ressources

Le système contrôle la quantité de traitements simultanés:

```python
self.executor = ThreadPoolExecutor(max_workers=5)  # Limite à 5 traitements
```

## Patterns de Conception

1. **Singleton**: Pour garantir une seule instance du service de stockage
2. **Factory**: Pour la création des extracteurs de traits
3. **Dependency Injection**: Pour l'injection des dépendances dans FastAPI
4. **Repository**: Pour l'abstraction du stockage des résultats
5. **Builder**: Pour la construction progressive des résultats d'analyse

## Évolutivité et Maintenance

L'architecture est conçue pour faciliter:

- **Extension**: Ajout de nouveaux types de traits ou catégories
- **Remplacement**: Substitution des modèles d'IA sous-jacents
- **Scaling**: Migration vers un stockage distribué (Redis, DB)
- **Monitoring**: Ajout de métriques et de traçage
- **Multitenancy**: Support de plusieurs utilisateurs/projets

## Considérations de Performance

- **Mise en cache**: Les modèles Hugging Face sont chargés une seule fois
- **Traitement asynchrone**: Évite de bloquer l'API pendant les analyses
- **Limite de concurrence**: Évite la surcharge du serveur
- **Nettoyage périodique**: Option pour purger les anciens résultats

## Diagramme de Séquence

```
┌─────────┐                  ┌──────┐                ┌────────────┐      ┌──────────────┐
│ Client  │                  │ API  │                │CharacterStore│      │TraitsExtractor│
└────┬────┘                  └──┬───┘                └──────┬───────┘      └───────┬──────┘
     │                          │                           │                      │
     │ POST /extract            │                           │                      │
     │ (text, directive, id)    │                           │                      │
     │─────────────────────────>│                           │                      │
     │                          │                           │                      │
     │                          │ process_async(id, func)   │                      │
     │                          │─────────────────────────>│                      │
     │                          │                           │                      │
     │ 202 Accepted             │                           │                      │
     │<─────────────────────────│                           │                      │
     │                          │                           │                      │
     │                          │                           │ extract_traits()     │
     │                          │                           │─────────────────────>│
     │                          │                           │                      │
     │                          │                           │<─────────────────────│
     │                          │                           │ traits               │
     │                          │                           │                      │
     │ GET /get_character/id    │                           │                      │
     │─────────────────────────>│                           │                      │
     │                          │ is_request_pending(id)    │                      │
     │                          │─────────────────────────>│                      │
     │                          │<─────────────────────────│                      │
     │                          │ false                     │                      │
     │                          │                           │                      │
     │                          │ get_result(id)            │                      │
     │                          │─────────────────────────>│                      │
     │                          │<─────────────────────────│                      │
     │                          │ CharacterTraitsResponse   │                      │
     │                          │                           │                      │
     │ 200 OK                   │                           │                      │
     │ (traits, summary)        │                           │                      │
     │<─────────────────────────│                           │                      │
```

## Évolutions Futures

1. **Persistance**: Migration vers une base de données pour le stockage
2. **API Gateway**: Ajout d'authentification et de limitation de débit
3. **WebSockets**: Notifications temps réel de fin de traitement
4. **Microservices**: Séparation en services distincts pour scaling
5. **Models Avancés**: Fine-tuning de modèles pour l'analyse de personnage