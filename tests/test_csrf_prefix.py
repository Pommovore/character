
from fastapi.testclient import TestClient
from src.api.api import create_application
import pytest
import re

def test_csrf_with_prefix():
    # Force environment variables for testing
    import os
    os.environ["SECRET_KEY"] = "test-secret"
    
    app = create_application(start_worker=False)
    client = TestClient(app)
    
    # Simulate prefix via X-Forwarded-Prefix
    prefix = "/character"
    
    # 1. GET /character/login
    response = client.get(f"{prefix}/login", headers={"X-Forwarded-Prefix": prefix})
    assert response.status_code == 200
    
    # Check if 'csrftoken' cookie is set
    assert "csrftoken" in response.cookies
    token = response.cookies["csrftoken"]
    print(f"Generated token: {token}")
    
    # 2. POST /character/login without token should fail with 403
    response = client.post(
        f"{prefix}/login", 
        data={"email": "test@example.com", "password": "pass"},
        headers={"X-Forwarded-Prefix": prefix}
    )
    assert response.status_code == 403
    assert "CSRF token verification failed" in response.text
    
    # 3. POST /character/login with correct token should pass CSRF
    # Note: we need to send BOTH the cookie and the form field
    response = client.post(
        f"{prefix}/login", 
        data={"email": "test@example.com", "password": "pass", "csrf_token": token}, 
        cookies={"csrftoken": token},
        headers={"X-Forwarded-Prefix": prefix}
    )
    
    # If CSRF passes, we might get 200 (login failure page) or 302 (redirect)
    # but NOT 403.
    assert response.status_code != 403
    print(f"Response status after CSRF: {response.status_code}")

def test_api_exempt_with_prefix():
    app = create_application(start_worker=False)
    client = TestClient(app)
    prefix = "/character"
    
    # GET /character/health should be exempt and return 200
    # (Previously it would 500 because it tried to match r"/health$" against "/character/health")
    response = client.get(f"{prefix}/health", headers={"X-Forwarded-Prefix": prefix})
    assert response.status_code == 200
    
    # GET /character/api/v1/queue/status without authentication
    # Should get 401 Unauthorized (from auth logic), not 403 CSRF or 500 error
    response = client.get(f"{prefix}/api/v1/queue/status", headers={"X-Forwarded-Prefix": prefix})
    assert response.status_code == 401
