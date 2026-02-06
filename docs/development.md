# Development Guide

This guide provides information for developers who want to contribute to the Character Traits Extractor project.

## Development Environment Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/character-traits-extractor.git
cd character-traits-extractor
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:
  ```bash
  venv\Scripts\activate
  ```

- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### 3. Install development dependencies

```bash
pip install -r requirements-dev.txt
```

This includes all regular dependencies plus development tools like pytest, black, and isort.

## Project Structure

```
character-traits-extractor/
├── .github/            # GitHub workflows for CI/CD
├── docs/               # Documentation
├── src/                # Source code
│   ├── api/            # API endpoints
│   ├── models/         # Pydantic models
│   ├── services/       # Business logic
│   └── utils/          # Utilities and helpers
├── tests/              # Test files
├── Dockerfile          # Docker configuration
├── requirements.txt    # Production dependencies
└── requirements-dev.txt # Development dependencies
```

## Running the Application Locally

To run the application in development mode:

```bash
uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-reload on code changes.

## Testing

### Running Tests

Run all tests with pytest:

```bash
pytest
```

Run tests with coverage report:

```bash
pytest --cov=src tests/
```

### Adding Tests

When adding new features, please also add corresponding tests:

- Unit tests should go in the `tests/` directory
- Test files should match the pattern `test_*.py`
- Use pytest fixtures for common test setups
- Mock external dependencies to ensure tests run quickly and reliably

## Code Style

This project follows PEP 8 style guidelines. We use the following tools to maintain code quality:

- **Black**: Code formatter
  ```bash
  black src/ tests/
  ```

- **isort**: Import sorter
  ```bash
  isort src/ tests/
  ```

- **Flake8**: Linter
  ```bash
  flake8 src/ tests/
  ```

## Git Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit with descriptive messages:
   ```bash
   git commit -m "Add trait extraction for emotional characteristics"
   ```

3. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request on GitHub

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

1. **Testing**: Runs all tests and checks code style
2. **Building**: Builds the Docker image
3. **Publishing**: Publishes the image to GitHub Packages
4. **Deployment**: Deploys to the target environment (if applicable)

The CI/CD configuration is located in `.github/workflows/`.

## Adding New Models

To add support for a new Hugging Face model:

1. Ensure the model is compatible with sequence classification
2. Add any special tokenization or preprocessing in the `TraitsExtractor` class
3. Update the documentation to reflect the new model option
4. Add tests to verify the model works correctly

## Documentation

Please update the documentation when making significant changes:

- API changes should be reflected in the OpenAPI schema
- New features should be documented in the appropriate guide
- Update the README.md if necessary