# Character Traits Extractor

A FastAPI application that extracts character traits from textual descriptions using Hugging Face transformer models.

## Overview

This service analyzes character descriptions and identifies key personality traits, values, and emotional characteristics. It uses pre-trained transformer models from Hugging Face to perform zero-shot classification of character traits.

## Features

- Extract character traits from text descriptions
- Categorize traits into personality traits, values, and emotional states
- Generate a summary of the character based on extracted traits
- API documented with OpenAPI/Swagger UI
- Docker containerization for easy deployment
- CI/CD pipeline using GitHub Actions

## Architecture

The application follows a modular architecture:

- **API Layer** (`src/api/`): FastAPI endpoints for handling requests
- **Service Layer** (`src/services/`): Core business logic for trait extraction
- **Model Layer** (`src/models/`): Pydantic models for input/output validation
- **Utils** (`src/utils/`): Helper utilities and shared functions

## API Documentation

When running the application, API documentation is available at:

- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`

## Endpoints

- `POST /api/v1/traits/extract`: Extract traits from a character description
- `GET /health`: Health check endpoint

## Getting Started

See the [Installation](./installation.md) and [Usage](./usage.md) guides to get started with the application.

## Development

Refer to the [Development Guide](./development.md) for information on contributing to the project, running tests, and the development workflow.