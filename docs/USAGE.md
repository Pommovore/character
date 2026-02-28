# Guide d'Utilisation

Ce guide explique comment utiliser l'API d'Extracteur de Traits de Caractère.

## Bases de l'API

L'Extracteur de Traits de Caractère fournit une API RESTful avec des formats de requête et de réponse JSON. L'URL de base pour tous les points de terminaison de l'API est :

```
http://<hôte>:<port>/api/v1
```

## Authentification

L'API nécessite une authentification par token pour le point de terminaison d'extraction. Le token peut être fourni de deux manières dans les headers de la requête :

1. **Header standard** : `Authorization: Bearer <votre_token>`
2. **Header spécifique** : `token: <votre_token>`

Les tokens sont générés par l'administrateur via l'interface d'administration.

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
- `text` (obligatoire) : La description du personnage à analyser. Doit comporter au moins 10 caractères. **Si ce champ contient une URL (http/https), le contenu textuel pointé par l'URL sera automatiquement téléchargé et utilisé pour l'analyse.**
- `request_id` (obligatoire) : Identifiant unique pour cette demande d'analyse.
- `directive` (optionnel) : Instructions supplémentaires pour guider l'analyse.
- `model_name` (optionnel) : Le modèle Hugging Face à utiliser pour l'extraction des traits. Par défaut : "distilbert-base-uncased".

> **Note** : Lorsqu'une URL est fournie, seuls les contenus textuels (text/*, application/json, application/xml) sont acceptés. La taille maximale du contenu téléchargé est de 1 Mo.

### Format de la Réponse (pour la soumission)

```json
{
  "request_id": "abc-123-xyz",
  "status": "pending",
  "message": "Traitement lancé avec succès"
}
```

La réponse indique que le traitement a été pris en compte et est en cours. 
### Webhook de Notification (Optionnel)

Si vous souhaitez être notifié automatiquement de la fin d'une extraction, vous pouvez inclure un header HTTP `webhook` pointant vers l'URL de votre choix.

```bash
curl -X POST "http://localhost:8000/api/v1/traits/extract" \
     ...
     -H "webhook: https://votre-domaine.com/callback" \
     ...
```

Une fois le traitement terminé, l'application enverra une requête `POST` à cette URL avec le payload JSON suivant :

```json
{
  "request_id": "abc-123-xyz",
  "status": "completed",
  "user_email": "votre@email.com",
  "result_url": "http://localhost:8000/api/v1/traits/get_character/abc-123-xyz"
}
```
Vous pourrez alors appeler l'URL `result_url` (toujours en fournissant un mot de passe ou sans, selon la route) pour récupérer l'analyse finale. En cas d'erreur de traitement, le statut sera `failed` et une clé `error` sera incluse à la place de `result_url`.

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

### 1. Démarrer le serveur
```bash
uv run run.py
```
*Le serveur utilisera le `HOST` et le `PORT` définis dans votre fichier `.env`.*

### 2. Exemples de Requête cURL pour soumettre une analyse

**Option A : Utilisation du header `token` (Recommandé)**

```bash
curl -X POST "http://localhost:8000/api/v1/traits/extract" \
     -H "Content-Type: application/json" \
     -H "token: VOTRE_TOKEN_ICI" \
     -d '{
           "text": "Harry Potter est un jeune sorcier courageux et loyal...",
           "request_id": "abc-123-xyz"
         }'
```

**Option B : Utilisation du header standard `Authorization`**

```bash
curl -X POST "http://localhost:8000/api/v1/traits/extract" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer VOTRE_TOKEN_ICI" \
     -d '{
           "text": "Harry Potter est un jeune sorcier courageux et loyal...",
           "request_id": "abc-123-xyz"
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

### Exemple avec Webhook en Python

Cet exemple s'appuie sur `FastAPI` (ou `Flask`) pour créer un serveur local très simple capable de recevoir le Callback de l'API.

**1. Le Serveur Webhook (le receveur)**
```python
# Fichier: webhook_receiver.py
# Lancer avec: fastapi run webhook_receiver.py --port 8001
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/mon-callback")
async def handle_callback(request: Request):
    payload = await request.json()
    print("\n--- WEBHOOK REÇU ! ---")
    print(f"La requête {payload.get('request_id')} est terminée (Statut: {payload.get('status')})")
    
    # 3. Dès la réception, on peut aller chercher le résultat directement
    if payload.get('status') == 'completed':
        import requests
        result_response = requests.get(payload.get('result_url'))
        print("Résultat final :", result_response.json().get('summary'))
    
    return {"message": "Webhook bien reçu"}
```

**2. Le Script Client (l'expéditeur)**
```python
import requests

submit_url = "http://localhost:8000/api/v1/traits/extract"

# On précise notre propre serveur comme webhook de destination
headers = {
    "webhook": "http://localhost:8001/mon-callback"
}

payload = {
    "text": "Gandalf le Gris est un sage, puissant et bienveillant magicien...",
    "request_id": "gandalf-webhook-01",
    "model_name": "distilbert-base-uncased"
}

response = requests.post(submit_url, json=payload, headers=headers)
print("Statut de soumission:", response.status_code)
print("Réponse:", response.json())
print("Vous pouvez maintenant fermer ce script. Le serveur Webhook recevra la notification quand ce sera prêt.")
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