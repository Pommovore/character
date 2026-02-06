# Extracteur de Traits de Caractère

Une application FastAPI qui extrait les traits de caractère à partir de descriptions textuelles en utilisant les modèles transformer de Hugging Face.

## Aperçu

Ce service analyse les descriptions de personnages et identifie les principaux traits de personnalité, valeurs et caractéristiques émotionnelles. Il utilise des modèles transformer pré-entraînés de Hugging Face pour effectuer une classification zero-shot des traits de caractère.

## Fonctionnalités

- Extraction des traits de caractère à partir de descriptions textuelles
- Catégorisation des traits en traits de personnalité, valeurs et états émotionnels
- Génération d'un résumé du personnage basé sur les traits extraits
- API documentée avec OpenAPI/Swagger UI
- Conteneurisation Docker pour un déploiement facile
- Pipeline CI/CD utilisant GitHub Actions

## Architecture

L'application suit une architecture modulaire :

- **Couche API** (`src/api/`) : Points de terminaison FastAPI pour traiter les requêtes
- **Couche Service** (`src/services/`) : Logique métier principale pour l'extraction de traits
- **Couche Modèle** (`src/models/`) : Modèles Pydantic pour la validation des entrées/sorties
- **Utilitaires** (`src/utils/`) : Fonctions utilitaires et communes

## Documentation API

Lors de l'exécution de l'application, la documentation de l'API est disponible à :

- Swagger UI : `/api/docs`
- ReDoc : `/api/redoc`
- OpenAPI JSON : `/api/openapi.json`

## Points de terminaison

- `POST /api/v1/traits/extract` : Extrait les traits d'une description de personnage
- `GET /health` : Point de terminaison de vérification de santé

## Démarrage

Consultez les guides d'[Installation](./installation.md) et d'[Utilisation](./usage.md) pour commencer avec l'application.

## Développement

Référez-vous au [Guide de développement](./development.md) pour des informations sur la contribution au projet, l'exécution des tests et le flux de travail de développement.