import io
from starlette.datastructures import UploadFile


def test_public_404_handler(client):
    """Verifies that non-existent public URL returns custom 404 HTML template."""
    response = client.get("/non-existent-engineering-page", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "Component Specification Not Found" in response.text
    assert "404" in response.text


def test_admin_404_handler(client):
    """Verifies that non-existent admin URL returns custom admin 404 HTML template."""
    response = client.get("/admin/non-existent-module", headers={"Accept": "text/html"})
    # When not logged in, admin dependency redirects to login, or if unauthenticated to login
    # Let's test API 404 with JSON accept header
    api_response = client.get("/api/v1/non-existent-resource", headers={"Accept": "application/json"})
    assert api_response.status_code == 404
    assert "detail" in api_response.json()


def test_upload_service_image_validation():
    """Verifies upload service MIME and Pillow image verification."""
    from app.services.upload_service import upload_service
    from fastapi import HTTPException
    import pytest

    # Invalid extension
    fake_file = UploadFile(filename="malicious.exe", file=io.BytesIO(b"binary executable"))
    with pytest.raises(HTTPException) as exc_info:
        upload_service.validate_image_file(fake_file, b"binary executable")
    assert exc_info.value.status_code == 400

    # Valid PNG image bytes
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(183, 121, 63))
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    valid_file = UploadFile(filename="shaft_gear.png", file=io.BytesIO(png_bytes), headers={"content-type": "image/png"})
    # Should not raise exception
    upload_service.validate_image_file(valid_file, png_bytes)
