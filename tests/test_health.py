from app.core.database import check_db_connection


def test_health_endpoint(client):
    """Verifies that the root /health endpoint returns HTTP 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "environment" in data


def test_api_v1_health(client):
    """Verifies the /api/v1/health route."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


def test_database_connection():
    """Verifies that the database health check helper can query the engine."""
    assert check_db_connection() is True


def test_public_homepage(client):
    """Verifies that the public homepage renders with HTTP 200 and expected branding."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "High-Integrity Forgings" in response.text
    assert "Closed-Die Hot Forging" in response.text


def test_security_headers(client):
    """Verifies that the security middleware attaches all standard security headers."""
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
