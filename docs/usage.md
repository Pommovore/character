# Guide d'Utilisation

Ce guide explique comment utiliser l'API d'Extracteur de Traits de Caractère.

## Bases de l'API

L'Extracteur de Traits de Caractère fournit une API RESTful avec des formats de requête et de réponse JSON. L'URL de base pour tous les points de terminaison de l'API est :

```
http://<hôte>:<port>/api/v1
```

## Authentification

L'API ne nécessite actuellement pas d'authentification. Pour les déploiements en production, il est recommandé de mettre en place un mécanisme d'authentification.

## Extraction des Traits de Caractère

### Point de terminaison

```
POST /api/v1/traits/extract
```

### Format de la Requête

```json
{
  "text": "Harry Potter est un jeune sorcier courageux et loyal qui fait constamment preuve de bravoure face au danger. Malgré son éducation difficile chez les Dursley, il maintient une forte boussole morale et valorise l'amitié par-dessus tout.",
  "model_name": "distilbert-base-uncased"
}
```

Paramètres :
- `text` (obligatoire) : La description du personnage à analyser. Doit comporter au moins 10 caractères.
- `model_name` (optionnel) : Le modèle Hugging Face à utiliser pour l'extraction des traits. Par défaut : "distilbert-base-uncased".

### Format de la Réponse

```json
{
  "traits": [
    {
      "trait": "Courageux",
      "score": 0.92,
      "category": "Personnalité"
    },
    {
      "trait": "Loyal",
      "score": 0.85,
      "category": "Personnalité"
    },
    {
      "trait": "Moral",
      "score": 0.78,
      "category": "Valeurs"
    }
  ],
  "summary": "Ce personnage est principalement caractérisé par Courageux (Personnalité), Loyal (Personnalité) et Moral (Valeurs).",
  "model_used": "distilbert-base-uncased"
}
```

La réponse inclut :
- `traits` : Une liste de traits extraits du texte, chacun avec :
  - `trait` : Le nom du trait
  - `score` : Score de confiance (entre 0 et 1)
  - `category` : La catégorie du trait (Personnalité, Valeurs, Émotions)
- `summary` : Un résumé généré des principaux traits de caractère
- `model_used` : Le nom du modèle utilisé pour l'extraction

### Exemple de Requête cURL

```bash
curl -X POST "http://localhost:8000/api/v1/traits/extract" \
     -H "Content-Type: application/json" \
     -d '{
           "text": "Harry Potter est un jeune sorcier courageux et loyal qui fait constamment preuve de bravoure face au danger. Malgré son éducation difficile chez les Dursley, il maintient une forte boussole morale et valorise l\'amitié par-dessus tout.",
           "model_name": "distilbert-base-uncased"
         }'
```

### Exemple de Requête Python

```python
import requests

url = "http://localhost:8000/api/v1/traits/extract"
payload = {
    "text": "Harry Potter est un jeune sorcier courageux et loyal qui fait constamment preuve de bravoure face au danger. Malgré son éducation difficile chez les Dursley, il maintient une forte boussole morale et valorise l'amitié par-dessus tout.",
    "model_name": "distilbert-base-uncased"
}

response = requests.post(url, json=payload)
print(response.json())
```

## Vérification de Santé

### Point de terminaison

```
GET /health
```

### Format de la Réponse

```json
{
  "status": "en bonne santé",
  "version": "0.1.0"
}
```

## Gestion des Erreurs

L'API renvoie des codes d'état HTTP standard pour indiquer le succès ou l'échec :

- `200 OK` : Requête réussie
- `400 Bad Request` : Format de requête invalide
- `422 Unprocessable Entity` : Erreur de validation (ex : texte trop court)
- `500 Internal Server Error` : Erreur côté serveur

Les réponses d'erreur incluent un message détaillé :

```json
{
  "detail": "Message d'erreur décrivant ce qui s'est mal passé"
}
```

## Documentation API

La documentation de l'API est disponible à :

- Swagger UI : `/api/docs`
- ReDoc : `/api/redoc`
- OpenAPI JSON : `/api/openapi.json`