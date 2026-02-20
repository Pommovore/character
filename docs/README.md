# Extracteur de Traits de Caractère

Une API moderne pour analyser des descriptions de personnages et extraire leurs traits de caractère principaux grâce à l'intelligence artificielle.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95.1-green)

## 🌟 Présentation

L'Extracteur de Traits de Caractère est une application qui utilise des modèles de traitement du langage naturel (NLP) pour analyser des descriptions textuelles de personnages. En quelques secondes, l'application identifie et extrait les principaux traits de personnalité, valeurs et caractéristiques émotionnelles.

**Cas d'utilisation :**
- Analyse de personnages pour la création littéraire
- Aide à la caractérisation pour les scénaristes
- Outil pédagogique pour l'étude de personnages
- Support pour les jeux de rôle et la création de personnages

## ✨ Fonctionnalités

- **Extraction asynchrone** des traits de caractère
- **Catégorisation** des traits (personnalité, valeurs, émotions)
- **Directives personnalisées** pour orienter l'analyse
- **Architecture API moderne** avec FastAPI
- **Traitement en arrière-plan** pour les textes longs
- **Génération automatique** de résumés de personnage
- **Documentation interactive** via Swagger UI

## 🚀 Démarrage Rapide

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-utilisateur/extracteur-traits-caractere.git
cd extracteur-traits-caractere

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### Lancement

```bash
# Lancer l'application
python -m src.main
```

L'API sera disponible à l'adresse `http://localhost:8000`.
Documentation interactive: `http://localhost:8000/api/docs`

## 📊 Exemple d'Utilisation

### Soumettre une analyse

```python
import requests

# 1. Soumission d'une analyse
url = "http://localhost:8000/api/v1/traits/extract"
payload = {
    "text": "Harry Potter est un jeune sorcier courageux et loyal qui fait constamment preuve de bravoure face au danger. Malgré son éducation difficile chez les Dursley, il maintient une forte boussole morale et valorise l'amitié par-dessus tout.",
    "directive": "Analyser les traits de leadership",
    "request_id": "harry-potter-001",
    "model_name": "distilbert-base-uncased"
}

response = requests.post(url, json=payload)
print(response.json())
# {'request_id': 'harry-potter-001', 'status': 'pending', 'message': 'Traitement lancé avec succès'}
```

### Récupérer les résultats

```python
# 2. Récupération des résultats
url = "http://localhost:8000/api/v1/traits/get_character/harry-potter-001"
response = requests.get(url)

# Si le traitement est terminé (HTTP 200)
if response.status_code == 200:
    results = response.json()
    print("Résumé:", results["summary"])
    print("Traits principaux:")
    for trait in results["traits"]:
        print(f"- {trait['trait']} ({trait['category']}): {trait['score']:.2f}")
```

## 🔧 Technologies

- **FastAPI** : Framework API hautes performances
- **Pydantic** : Validation des données et sérialisation
- **HuggingFace Transformers** : Modèles NLP pré-entraînés
- **Uvicorn** : Serveur ASGI pour FastAPI
- **Docker** : Conteneurisation et déploiement
- **GitHub Actions** : CI/CD automatisé

## 📚 Documentation

Pour une documentation plus détaillée, consultez les guides suivants:

- [Guide d'Installation](installation.md)
- [Guide d'Utilisation](usage.md)
- [Architecture](../ARCHITECTURE.md)
- [Guide de Développement](development.md)

## 🔒 Considérations de sécurité

L'application utilise le stockage en mémoire pour les résultats. Dans un environnement de production, envisagez d'implémenter:
- Authentification et autorisation
- Stockage persistant des résultats
- Limitation de débit (rate-limiting)
- HTTPS pour toutes les communications

## 📄 Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.