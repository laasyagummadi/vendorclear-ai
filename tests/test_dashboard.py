from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dashboard_endpoint():
    response = client.get("/dashboard/")

    assert response.status_code == 200

    data = response.json()

    assert "total_vendor_policies" in data
    assert "total_diversity_certificates" in data
    assert "expired_vendor_policies" in data
    assert "expired_diversity_certificates" in data
    assert "total_alerts" in data


def test_dashboard_response_types():
    response = client.get("/dashboard/")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["total_vendor_policies"], int)
    assert isinstance(data["total_diversity_certificates"], int)
    assert isinstance(data["expired_vendor_policies"], int)
    assert isinstance(data["expired_diversity_certificates"], int)
    assert isinstance(data["total_alerts"], int)
