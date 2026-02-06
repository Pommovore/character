# Installation Guide

This guide explains how to install and set up the Character Traits Extractor application.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Docker (optional, for containerization)

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/character-traits-extractor.git
cd character-traits-extractor
```

### 2. Create a virtual environment (recommended)

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running with Docker

### 1. Build the Docker image

```bash
docker build -t character-traits-extractor .
```

### 2. Run the container

```bash
docker run -p 8000:8000 character-traits-extractor
```

The API will be available at `http://localhost:8000`.

## Environment Variables

The application can be configured using the following environment variables:

| Variable   | Description                          | Default     |
|------------|--------------------------------------|-------------|
| `HOST`     | Host to bind the server to          | `0.0.0.0`   |
| `PORT`     | Port to run the server on           | `8000`      |
| `LOG_LEVEL`| Logging level (INFO, DEBUG, etc.)   | `INFO`      |

## Verifying Installation

To verify that the application is running correctly:

1. Access the health check endpoint:
   ```
   GET http://localhost:8000/health
   ```

2. Check the API documentation:
   ```
   http://localhost:8000/api/docs
   ```

## Next Steps

Once the application is installed and running, see the [Usage Guide](./usage.md) for information on how to use the API.