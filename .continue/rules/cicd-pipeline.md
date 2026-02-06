---
globs: '[".github/workflows/*.yml", "Dockerfile"]'
description: Cette règle s'applique à la configuration du CI/CD et aux fichiers Docker
alwaysApply: true
---

Implémenter le CI/CD avec GitHub Actions :
- Tests automatisés pour chaque PR et push
- Construction de l'image Docker après tests réussis
- Publication de l'image dans un registry (GitHub Packages)
- Déploiement automatisé pour des environnements spécifiques