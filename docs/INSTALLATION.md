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

### 2. Configurer l'environnement

```bash
# Installer les dépendances et créer l'environnement virtuel automatiquement
uv sync
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

## Déploiement sur serveur distant (Production)

Pour un déploiement hors-Docker sur un serveur (ex: VPS sous Linux) utilisant Nginx et Systemd.

### 1. Configuration préalable

1.  Modifiez le fichier `config/deploy.conf` avec vos paramètres de serveur :
    ```yaml
    deploy:
      machine_name: "votre.serveur.com"
      port: 8886
      target_directory: "/opt/character/"
      app_prefix: "/character"
    ```
2.  Assurez-vous que l'authentification par clé SSH (sans mot de passe) est configurée depuis votre machine vers le serveur cible (`machine_name`).
3.  Assurez-vous que les paquets de base Python sont installés sur le serveur (`python3`, `python3-venv`).

### 2. Configuration du Serveur (Une seule fois)

Des modèles de configuration sont fournis dans le dossier `config/`. Vous devez les copier et les adapter sur votre serveur.

1.  **Service Systemd** : Copiez le contenu de `config/character.service` dans `/etc/systemd/system/character.service` sur votre serveur.
2.  **Reverse Proxy Nginx** : Intégrez le contenu de `config/nginx.conf` dans votre configuration Nginx (`/etc/nginx/sites-available/default` ou votre config de domaine).
3.  Activez et démarrez les services sur le serveur :
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable character
    sudo systemctl restart character
    sudo systemctl restart nginx
    ```

### 3. Exécuter le déploiement

Depuis votre machine de développement, choisissez la commande de déploiement (utilisant `rsync` et `fabric`) :

**Plutôt pour le code au quotidien (plus sécure et rapide) :**
```bash
python deploy.py --update
```
Ce script va uniquement se baser sur les fichiers suivis par git (`git ls-files`) pour pousser votre code de façon sélective et recharger l'application Python (`uvicorn`). Il ignore tout fichier local parasite et les modifications de configuration de serveur (Systemd, Nginx). 

**Pour le tout premier déploiement complet ou mise à jour Serveur :**
```bash
python deploy.py --prod
```
Ce script va automatiquement :
- Vous demander interactivement de configurer ou vérifier les identifiants administrateur de production (Email, Mot de passe sécurisé, Token Hugging Face, et Webhook Discord).
- Générer votre fichier `.env` distant et le PIN d'installation (`SETUP_PIN_CODE`)
- Synchroniser tout le code vers le `target_directory`.
- Installer/Configurer Nginx et Systemd.
- Forcer les redémarrages complets (Systemd daemon reload + Nginx reload).

**Note sur le Reverse Proxy :**
L'application gère nativement le sous-dossier défini dans `deploy.conf` (`app_prefix: "/character"`). Nginx transmet ce chemin via `X-Forwarded-Prefix`, et l'application prefix automatiquement tous ses liens internes. Lors du premier déploiement, vous devez vous rendre à l'adresse fournie (ex: `https://votre-domaine.com/character/setup`) et renseigner le **Code PIN d'installation** indiqué par le terminal pour finaliser la création du compte administrateur.

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