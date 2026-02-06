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
  "directive": "Analyser les traits de leadership et de courage",
  "request_id": "abc-123-xyz",
  "model_name": "distilbert-base-uncased"
}
```

Paramètres :
- `text` (obligatoire) : La description du personnage à analyser. Doit comporter au moins 10 caractères.
- `request_id` (obligatoire) : Identifiant unique pour cette demande d'analyse.
- `directive` (optionnel) : Instructions supplémentaires pour guider l'analyse.
- `model_name` (optionnel) : Le modèle Hugging Face à utiliser pour l'extraction des traits. Par défaut : "distilbert-base-uncased".

### Format de la Réponse (pour la soumission)

```json
{
  "request_id": "abc-123-xyz",
  "status": "pending",
  "message": "Traitement lancé avec succès"
}
```

La réponse indique que le traitement a été pris en compte et est en cours. 
L'API renvoie immédiatement un code HTTP 202 (Accepted) pour indiquer que la demande a été acceptée mais n'est pas encore traitée.

## Récupération des Résultats

### Point de terminaison

```
GET /api/v1/traits/get_character/{request_id}
```

### Format de la Réponse (une fois le traitement terminé)

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
  "model_used": "distilbert-base-uncased",
  "request_id": "abc-123-xyz",
  "directive": "Analyser les traits de leadership et de courage",
  "status": "completed"
}
```

La réponse inclut :
- `traits` : Une liste de traits extraits du texte, chacun avec :
  - `trait` : Le nom du trait
  - `score` : Score de confiance (entre 0 et 1)
  - `category` : La catégorie du trait (Personnalité, Valeurs, Émotions)
- `summary` : Un résumé généré des principaux traits de caractère
- `model_used` : Le nom du modèle utilisé pour l'extraction

### Exemple de Requête cURL pour soumettre une analyse

```bash
curl -X POST "http://localhost:8000/api/v1/traits/extract" \
     -H "Content-Type: application/json" \
     -d '{
           "text": "Harry Potter est un jeune sorcier courageux et loyal qui fait constamment preuve de bravoure face au danger. Malgré son éducation difficile chez les Dursley, il maintient une forte boussole morale et valorise l\'amitié par-dessus tout.",
           "directive": "Analyser les traits de leadership et de courage",
           "request_id": "abc-123-xyz",
           "model_name": "distilbert-base-uncased"
         }'
```

### Exemple de Requête cURL pour récupérer les résultats

```bash
curl -X GET "http://localhost:8000/api/v1/traits/get_character/abc-123-xyz"
```

### Exemple complet en Python

```python
import requests
import time

# 1. Soumettre une analyse
submit_url = "http://localhost:8000/api/v1/traits/extract"
payload = {
    "text": "Harry Potter est un jeune sorcier courageux et loyal qui fait constamment preuve de bravoure face au danger. Malgré son éducation difficile chez les Dursley, il maintient une forte boussole morale et valorise l'amitié par-dessus tout.",
    "directive": "Analyser les traits de leadership",
    "request_id": "demo-123",
    "model_name": "distilbert-base-uncased"
}

response = requests.post(submit_url, json=payload)
print("Statut de soumission:", response.status_code)
print(response.json())

# 2. Récupérer les résultats (avec tentatives)
results_url = f"http://localhost:8000/api/v1/traits/get_character/demo-123"
max_attempts = 10

for attempt in range(max_attempts):
    response = requests.get(results_url)
    
    if response.status_code == 200:  # Traitement terminé
        print("\nRésultats obtenus:")
        print(response.json())
        break
    elif response.status_code == 202:  # Toujours en cours
        print(f"Traitement en cours... (tentative {attempt+1}/{max_attempts})")
        time.sleep(2)  # Attendre 2 secondes avant de réessayer
    elif response.status_code == 404 and response.text == '"inconnu"':  # ID inconnu
        print("ID de requête inconnu")
        break
    else:
        print(f"Erreur inattendue: {response.status_code} - {response.text}")
        break
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

- `200 OK` : Requête réussie, résultats disponibles
- `202 Accepted` : Requête acceptée, traitement en cours
- `400 Bad Request` : Format de requête invalide
- `404 Not Found` : ID de requête inconnu
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