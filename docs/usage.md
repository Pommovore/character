# Usage Guide

This guide explains how to use the Character Traits Extractor API.

## API Basics

The Character Traits Extractor provides a RESTful API with JSON request and response formats. The base URL for all API endpoints is:

```
http://<host>:<port>/api/v1
```

## Authentication

The API currently does not require authentication. For production deployments, it is recommended to implement an authentication mechanism.

## Extracting Character Traits

### Endpoint

```
POST /api/v1/traits/extract
```

### Request Format

```json
{
  "text": "Harry Potter is a brave and loyal young wizard who consistently shows courage in the face of danger. Despite his difficult upbringing with the Dursleys, he maintains a strong moral compass and values friendship above all else.",
  "model_name": "distilbert-base-uncased"
}
```

Parameters:
- `text` (required): The character description to analyze. Must be at least 10 characters long.
- `model_name` (optional): The Hugging Face model to use for trait extraction. Defaults to "distilbert-base-uncased".

### Response Format

```json
{
  "traits": [
    {
      "trait": "Courageous",
      "score": 0.92,
      "category": "Personality"
    },
    {
      "trait": "Loyal",
      "score": 0.85,
      "category": "Personality"
    },
    {
      "trait": "Moral",
      "score": 0.78,
      "category": "Values"
    }
  ],
  "summary": "This character is primarily characterized by Courageous (Personality), Loyal (Personality) and Moral (Values).",
  "model_used": "distilbert-base-uncased"
}
```

The response includes:
- `traits`: A list of traits extracted from the text, each with:
  - `trait`: The name of the trait
  - `score`: Confidence score (between 0 and 1)
  - `category`: The category of the trait (Personality, Values, Emotions)
- `summary`: A generated summary of the main character traits
- `model_used`: The name of the model used for extraction

### Example cURL Request

```bash
curl -X POST "http://localhost:8000/api/v1/traits/extract" \
     -H "Content-Type: application/json" \
     -d '{
           "text": "Harry Potter is a brave and loyal young wizard who consistently shows courage in the face of danger. Despite his difficult upbringing with the Dursleys, he maintains a strong moral compass and values friendship above all else.",
           "model_name": "distilbert-base-uncased"
         }'
```

### Example Python Request

```python
import requests

url = "http://localhost:8000/api/v1/traits/extract"
payload = {
    "text": "Harry Potter is a brave and loyal young wizard who consistently shows courage in the face of danger. Despite his difficult upbringing with the Dursleys, he maintains a strong moral compass and values friendship above all else.",
    "model_name": "distilbert-base-uncased"
}

response = requests.post(url, json=payload)
print(response.json())
```

## Health Check

### Endpoint

```
GET /health
```

### Response Format

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## Error Handling

The API returns standard HTTP status codes to indicate success or failure:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request format
- `422 Unprocessable Entity`: Validation error (e.g., text too short)
- `500 Internal Server Error`: Server-side error

Error responses include a detail message:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## API Documentation

The API documentation is available at:

- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`