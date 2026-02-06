# Guide de Développement

Ce guide fournit des informations pour les développeurs qui souhaitent contribuer au projet Extracteur de Traits de Caractère.

## Configuration de l'Environnement de Développement

### 1. Cloner le dépôt

```bash
git clone https://github.com/yourusername/character-traits-extractor.git
cd character-traits-extractor
```

### 2. Créer un environnement virtuel

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

### 3. Installer les dépendances de développement

```bash
pip install -r requirements-dev.txt
```

Cela inclut toutes les dépendances régulières plus les outils de développement comme pytest, black et isort.

## Structure du Projet

```
extracteur-traits-caractere/
├── .github/            # Workflows GitHub pour CI/CD
├── docs/               # Documentation
├── src/                # Code source
│   ├── api/            # Points de terminaison API
│   ├── models/         # Modèles Pydantic
│   ├── services/       # Logique métier
│   └── utils/          # Utilitaires et assistants
├── tests/              # Fichiers de test
├── Dockerfile          # Configuration Docker
├── requirements.txt    # Dépendances de production
└── requirements-dev.txt # Dépendances de développement
```

## Exécution de l'Application en Local

Pour exécuter l'application en mode développement :

```bash
uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

L'option `--reload` permet le rechargement automatique lors des modifications du code.

## Tests

### Exécution des Tests

Exécuter tous les tests avec pytest :

```bash
pytest
```

Exécuter les tests avec rapport de couverture :

```bash
pytest --cov=src tests/
```

### Ajout de Tests

Lors de l'ajout de nouvelles fonctionnalités, veuillez également ajouter les tests correspondants :

- Les tests unitaires doivent être placés dans le répertoire `tests/`
- Les fichiers de test doivent correspondre au modèle `test_*.py`
- Utilisez les fixtures pytest pour les configurations de test communes
- Moquez les dépendances externes pour garantir que les tests s'exécutent rapidement et de manière fiable

## Style de Code

Ce projet suit les directives de style PEP 8. Nous utilisons les outils suivants pour maintenir la qualité du code :

- **Black** : Formateur de code
  ```bash
  black src/ tests/
  ```

- **isort** : Trieur d'imports
  ```bash
  isort src/ tests/
  ```

- **Flake8** : Linter
  ```bash
  flake8 src/ tests/
  ```

## Workflow Git

1. Créez une nouvelle branche pour votre fonctionnalité ou correction de bug :
   ```bash
   git checkout -b feature/nom-de-votre-fonctionnalite
   ```

2. Effectuez vos modifications et committez avec des messages descriptifs :
   ```bash
   git commit -m "Ajouter l'extraction de traits pour les caractéristiques émotionnelles"
   ```

3. Poussez votre branche :
   ```bash
   git push origin feature/nom-de-votre-fonctionnalite
   ```

4. Créez une pull request sur GitHub

## Pipeline CI/CD

Le projet utilise GitHub Actions pour l'intégration et le déploiement continus :

1. **Tests** : Exécute tous les tests et vérifie le style de code
2. **Construction** : Construit l'image Docker
3. **Publication** : Publie l'image sur GitHub Packages
4. **Déploiement** : Déploie dans l'environnement cible (le cas échéant)

La configuration CI/CD se trouve dans `.github/workflows/`.

## Ajout de Nouveaux Modèles

Pour ajouter la prise en charge d'un nouveau modèle Hugging Face :

1. Assurez-vous que le modèle est compatible avec la classification de séquences
2. Ajoutez toute tokenisation ou prétraitement spécial dans la classe `TraitsExtractor`
3. Mettez à jour la documentation pour refléter la nouvelle option de modèle
4. Ajoutez des tests pour vérifier que le modèle fonctionne correctement

## Documentation

Veuillez mettre à jour la documentation lorsque vous apportez des modifications significatives :

- Les modifications de l'API doivent être reflétées dans le schéma OpenAPI
- Les nouvelles fonctionnalités doivent être documentées dans le guide approprié
- Mettez à jour le README.md si nécessaire