# Guide d'Installation

Ce guide explique comment installer et configurer l'application Extracteur de Traits de Caractère.

## Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Docker (optionnel, pour la conteneurisation)

## Installation locale

### 1. Cloner le dépôt

```bash
git clone https://github.com/yourusername/character-traits-extractor.git
cd character-traits-extractor
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv
```

Activer l'environnement virtuel :

- Sur Windows :
  ```bash
  venv\Scripts\activate
  ```

- Sur macOS/Linux :
  ```bash
  source venv/bin/activate
  ```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## Exécution avec Docker

### 1. Construire l'image Docker

```bash
docker build -t extracteur-traits-caractere .
```

### 2. Exécuter le conteneur

```bash
docker run -p 8000:8000 extracteur-traits-caractere
```

L'API sera disponible à l'adresse `http://localhost:8000`.

## Variables d'Environnement

L'application peut être configurée à l'aide des variables d'environnement suivantes :

| Variable   | Description                                | Valeur par défaut |
|------------|--------------------------------------------|-------------------|
| `HOST`     | Hôte sur lequel lier le serveur           | `0.0.0.0`         |
| `PORT`     | Port sur lequel exécuter le serveur       | `8000`            |
| `LOG_LEVEL`| Niveau de journalisation (INFO, DEBUG, etc.) | `INFO`          |

## Vérification de l'Installation

Pour vérifier que l'application fonctionne correctement :

1. Accédez au point de terminaison de vérification de santé :
   ```
   GET http://localhost:8000/health
   ```

2. Consultez la documentation de l'API :
   ```
   http://localhost:8000/api/docs
   ```

## Étapes suivantes

Une fois l'application installée et en cours d'exécution, consultez le [Guide d'utilisation](./usage.md) pour obtenir des informations sur l'utilisation de l'API.