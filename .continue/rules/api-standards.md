---
globs: '["src/**/*.py", "src/api/**/*", "src/models/**/*"]'
description: Appliquer cette règle pour toute implémentation d'API et de
  validation de données
alwaysApply: true
---

L'API doit utiliser FastAPI, Uvicorn et Pydantic :
- Utiliser FastAPI pour le framework de l'API
- Uvicorn comme serveur ASGI
- Pydantic pour la validation des données
- Documentation auto-générée avec Swagger UI
- Versionnement des endpoints (/api/v1/...)