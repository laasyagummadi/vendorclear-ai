from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_compliance_vendor_not_found():
    response = client.get(
        "/compliance/evaluate/non_existing_vendor"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Vendor Policy not found"
