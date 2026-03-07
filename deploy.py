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
    print("Démarrage du serveur local de développement...")
    try:
        import run
        run.run_server()
    except ImportError:
        print("Erreur: Impossible de charger run.py. Assurez-vous d'être à la racine du projet.")
        import os
        os.system("uv run run.py")
    sys.exit(0)

def deploy_prod(config):
    """Déploiement en environnement de production (distant)."""
    print("Déploiement en cours (Environnement: PROD)...")
    
    import random
    setup_pin = f"{random.randint(0, 9999):04d}"
    
    print("\n" + "="*50)
    print("INSTALLATION WEB SÉCURISÉE")
    print(f"Code PIN pour l'installation web : {setup_pin}")
    print("Veuillez conserver ce code. Il vous sera demandé sur la page web.")
    print("="*50 + "\n")

    deploy_conf = config.get("deploy", {})
    host = deploy_conf.get("machine_name")
    target_dir = deploy_conf.get("target_directory")
    
    if not host or not target_dir:
        print("Erreur : machine_name et target_directory sont requis dans la configuration pour la production.")
        sys.exit(1)

    remote_user = os.environ.get('REMOTE_USER')
    remote_pwd = os.environ.get('REMOTE_PWD')
    host_str = f"{remote_user}@{host}" if remote_user else host

    print(f"⚠️ ATTENTION : Vous êtes sur le point de faire une INSTALLATION PROPRE sur {host_str}:{target_dir}.")
    print("Cela EFFACERA TOTALEMENT le répertoire distant (Y COMPRIS LA BASE DE DONNÉES).")
    print("Seul le fichier .env distant sera conservé.")
    print("La base de données locale NE SERA PAS copiée vers le serveur distant.")
    confirm = input("Êtes-vous sûr de vouloir effacer le serveur distant et continuer ? (O/n) : ")
    
    if confirm.lower() not in ('o', 'oui', 'y', 'yes', ''):
        print("Opération annulée.")
        sys.exit(0)

    import getpass
    from fabric import Config
    
    sudo_pass = remote_pwd or getpass.getpass(f"Mot de passe sudo pour {host} (appuyez sur Entrée si inutile) : ")
    fabric_config = Config(overrides={'sudo': {'password': sudo_pass}}) if sudo_pass else None
    connect_kwargs = {"password": remote_pwd} if remote_pwd else {}

    print(f"Nettoyage du répertoire distant {target_dir} (conservation de .env)...")
    try:
        with Connection(host, user=remote_user, connect_kwargs=connect_kwargs, config=fabric_config) as c:
            c.run(f"mkdir -p {target_dir}")
            with c.cd(target_dir):
                c.run("find . -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +")
    except Exception as e:
        print(f"Erreur lors du nettoyage distant : {e}")
        sys.exit(1)

    print(f"Synchronisation des fichiers vers {host}:{target_dir}...")
    
    # Exclure les fichiers inutiles ou sensibles
    exclude_args = [
        "--exclude=.git",
        "--exclude=.venv",
        "--exclude=.venv_tools",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.env",  # Ne pas écraser le .env de prod
        "--exclude=data/db/*.db", # Ne PAS copier la base locale
        "--exclude=*.sqlite3",
        "--exclude=*.db",
    ]
    
    # Commande rsync (Mode Nominal : synchronise tout sauf exclusions)
    rsync_cmd = f"rsync -avz --delete {' '.join(exclude_args)} ./ {host_str}:{target_dir}"
    result = os.system(rsync_cmd)
    
    if result != 0:
        print("Erreur lors de la synchronisation des fichiers.")
        sys.exit(1)

    print("Exécution des commandes post-déploiement sur le serveur...")
    
    try:
        # Connexion SSH pour exécuter les commandes à distance
        # Note: Suppose que l'authentification par clé SSH est configurée
        with Connection(host, user=remote_user, connect_kwargs=connect_kwargs, config=fabric_config) as c:
            with c.cd(target_dir):
                print("1. Installation des dépendances avec uv...")
                # L'outil uv créera automatiquement le .venv et installera l'environnement de production
                # On exporte le PATH pour les sessions SSH non-interactives où uv (souvent dans ~/.local/bin ou ~/.cargo/bin) n'est pas reconnu
                c.run("export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync --no-dev")
                
                print("1.b Configuration de l'environnement de sécurité...")
                import secrets
                
                existing_env = {}
                try:
                    res = c.run("cat .env", hide=True)
                    for line in res.stdout.splitlines():
                        if '=' in line:
                            k, v = line.split("=", 1)
                            existing_env[k] = v
                except Exception:
                    pass
                
                if "ADMIN_EMAIL" not in existing_env:
                    existing_env["SETUP_PIN_CODE"] = setup_pin
                else:
                    print("L'application est déjà configurée (ADMIN_EMAIL trouvé). Ignorer le code PIN.")
                
                if "SECRET_KEY" not in existing_env:
                    existing_env["SECRET_KEY"] = secrets.token_hex(32)
                if "DATABASE_URL" not in existing_env:
                    existing_env["DATABASE_URL"] = "sqlite:///data/db/character.db"
                    
                existing_env["PORT"] = deploy_conf.get("port", 8000)
                existing_env["HOST"] = "127.0.0.1"
                existing_env["RELOAD"] = "False"
                    
                new_env = "\n".join([f"{k}={v}" for k, v in existing_env.items()])
                c.run("cat << 'EOF' > .env\n" + new_env + "\nEOF")
                
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

def deploy_update(config):
    """Mise à jour légère : Uniquement les fichiers suivis par git, pas de config Nginx/Systemd."""
    print("Mise à jour en cours (Environnement: PROD)...")
    
    deploy_conf = config.get("deploy", {})
    host = deploy_conf.get("machine_name")
    target_dir = deploy_conf.get("target_directory")
    
    if not host or not target_dir:
        print("Erreur : machine_name et target_directory sont requis.")
        sys.exit(1)

    remote_user = os.environ.get('REMOTE_USER')
    remote_pwd = os.environ.get('REMOTE_PWD')
    host_str = f"{remote_user}@{host}" if remote_user else host

    print(f"Synchronisation (fichiers git uniquement) vers {host_str}:{target_dir}...")
    
    # Exporte la liste des fichiers Git vers un fichier temporaire pour rsync
    os.system("git ls-files > .git_files_list.txt")
    
    # Exclusions explicites pour être sûr de ne pas envoyer la BDD locale même si elle s'est retrouvée dans git
    exclude_args = [
        "--exclude=*.db",
        "--exclude=*.sqlite3",
        "--exclude=data/db/*.db"
    ]
    
    # Rsync utilise --files-from pour NE COPIER QUE ce qui est dans .git_files_list.txt
    rsync_cmd = f"rsync -avz {' '.join(exclude_args)} --files-from=.git_files_list.txt ./ {host_str}:{target_dir}"
    result = os.system(rsync_cmd)
    
    os.system("rm .git_files_list.txt") # Nettoyage
    
    if result != 0:
        print("Erreur lors de la synchronisation de la mise à jour.")
        sys.exit(1)

    print("Exécution des commandes post-mise-à-jour sur le serveur...")
    import getpass
    from fabric import Config
    
    sudo_pass = remote_pwd or getpass.getpass(f"Mot de passe sudo pour {host} (appuyez sur Entrée si inutile) : ")
    fabric_config = Config(overrides={'sudo': {'password': sudo_pass}}) if sudo_pass else None
    connect_kwargs = {"password": remote_pwd} if remote_pwd else {}
    
    try:
        with Connection(host, user=remote_user, connect_kwargs=connect_kwargs, config=fabric_config) as c:
            with c.cd(target_dir):
                print("1. Installation des NOUVELLES dépendances avec uv (si pyproject a changé)...")
                c.run("export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync --no-dev")
                
            print("2. Redémarrage du service systemd...")
            # Pas de cp /etc/systemd... ou de reload du daemon, juste un restart basique
            c.sudo("systemctl restart character.service")
                
        print("✅ Mise à jour validée et relancée !")
    except Exception as e:
        print(f"Erreur lors de l'exécution : {e}")

def main():
    parser = argparse.ArgumentParser(description="Script de déploiement de l'application Character")
    parser.add_argument("--dev", action="store_true", help="Déployer en environnement de développement (local)")
    parser.add_argument("--prod", action="store_true", help="Déployer complétement (fichiers + config serveur)")
    parser.add_argument("--update", action="store_true", help="Mise à jour légère (uniquement fichiers git, restart simple)")
    args = parser.parse_args()

    if sum([args.dev, args.prod, args.update]) != 1:
        print("Veuillez spécifier EXACTEMENT UN environnement : --dev, --prod ou --update")
        parser.print_help()
        sys.exit(1)

    config = load_config()

    if args.dev:
        deploy_dev()
    elif args.prod:
        deploy_prod(config)
    elif args.update:
        deploy_update(config)

if __name__ == "__main__":
    main()
