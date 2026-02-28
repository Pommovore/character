#!/usr/bin/env python3
"""Script de déploiement pour l'API d'extraction de traits de caractère.

Ce script lit la configuration depuis config/deploy.conf et déploie l'application
sur le serveur distant via rsync et SSH.
"""

import argparse
import os
import sys
import yaml
from fabric import Connection

def load_config(config_path="config/deploy.conf"):
    """Charge la configuration depuis le fichier YAML."""
    if not os.path.exists(config_path):
        print(f"Erreur : Le fichier de configuration {config_path} est introuvable.")
        sys.exit(1)
        
    with open(config_path, 'r') as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"Erreur lors de la lecture du fichier YAML : {exc}")
            sys.exit(1)

def deploy_dev():
    """Déploiement en environnement de développement (local)."""
    print("Déploiement en cours (Environnement: DEV)...")
    print("En dev, utilisez simplement `python run.py` ou `uvicorn src.api.api:app --reload`")
    sys.exit(0)

def deploy_prod(config):
    """Déploiement en environnement de production (distant)."""
    print("Déploiement en cours (Environnement: PROD)...")
    
    deploy_conf = config.get("deploy", {})
    host = deploy_conf.get("machine_name")
    target_dir = deploy_conf.get("target_directory")
    
    if not host or not target_dir:
        print("Erreur : machine_name et target_directory sont requis dans la configuration pour la production.")
        sys.exit(1)

    print(f"Synchronisation des fichiers vers {host}:{target_dir}...")
    
    # Exclure les fichiers inutiles ou sensibles
    exclude_args = [
        "--exclude=.git",
        "--exclude=.venv",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.env",  # Ne pas écraser le .env de prod
        "--exclude=data/db/*.db", # Ne pas écraser la base de prod
    ]
    
    # Commande rsync
    rsync_cmd = f"rsync -avz --delete {' '.join(exclude_args)} ./ {host}:{target_dir}"
    result = os.system(rsync_cmd)
    
    if result != 0:
        print("Erreur lors de la synchronisation des fichiers.")
        sys.exit(1)

    print("Exécution des commandes post-déploiement sur le serveur...")
    
    import getpass
    from fabric import Config
    
    sudo_pass = getpass.getpass(f"Mot de passe sudo pour {host} (appuyez sur Entrée si inutile) : ")
    config = Config(overrides={'sudo': {'password': sudo_pass}}) if sudo_pass else None
    
    try:
        # Connexion SSH pour exécuter les commandes à distance
        # Note: Suppose que l'authentification par clé SSH est configurée
        with Connection(host, config=config) as c:
            with c.cd(target_dir):
                print("1. Installation des dépendances avec uv...")
                # L'outil uv créera automatiquement le .venv et installera l'environnement de production
                # On exporte le PATH pour les sessions SSH non-interactives où uv (souvent dans ~/.local/bin ou ~/.cargo/bin) n'est pas reconnu
                c.run("export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync --no-dev")
                
            print("2. Redémarrage du service systemd...")
            # Note: Si le mot de passe est saisi au prompt, Fabric s'en charge.
            # On met à jour le fichier service système et on recharge le daemon
            c.sudo("cp /opt/character/config/character.service /etc/systemd/system/character.service")
            c.sudo("systemctl daemon-reload")
            c.sudo("systemctl restart character.service")
            
            print("3. Configuration de Nginx...")
            # Installation customisée de Nginx spécifiée par l'utilisateur
            c.sudo("cp /opt/character/config/nginx.conf /etc/nginx/apps/character.conf")
            # Test de la syntaxe puis rechargement (besoin de bash -c pour chainer avec sudo)
            c.sudo("bash -c 'nginx -t && systemctl reload nginx'")
                
        print("✅ Déploiement terminé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'exécution des commandes distantes : {e}")
        print("Note : Vérifiez que 'fabric' est installé et que votre clé SSH est configurée.")

def main():
    parser = argparse.ArgumentParser(description="Script de déploiement de l'application Character")
    parser.add_argument("--dev", action="store_true", help="Déployer en environnement de développement (local)")
    parser.add_argument("--prod", action="store_true", help="Déployer en environnement de production (distant)")
    args = parser.parse_args()

    if not args.dev and not args.prod:
        print("Veuillez spécifier l'environnement : --dev ou --prod")
        parser.print_help()
        sys.exit(1)

    if args.dev and args.prod:
        print("Erreur : Vous ne pouvez pas spécifier --dev et --prod simultanément.")
        sys.exit(1)

    config = load_config()

    if args.dev:
        deploy_dev()
    elif args.prod:
        deploy_prod(config)

if __name__ == "__main__":
    main()
