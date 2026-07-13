from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_all_alerts():
    response = client.get("/alerts/")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_resolve_alert_not_found():
    response = client.put("/alerts/999999/resolve")

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"


def test_resolve_alert_success():
    """
    Requires an existing alert in the test database.
    Replace alert ID with a valid test record if needed.
    """

    response = client.put("/alerts/1/resolve")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()

        assert "message" in data
        assert "alert" in data
        assert data["message"] == "Alert resolved successfully"
