from backend.app import app


def test_health_endpoint():
    response = app.test_client().get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"app": "TriQuest API", "status": "ok"}


def test_protected_endpoint_requires_token():
    response = app.test_client().get("/api/dashboard")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Autenticação necessária."}


def test_unknown_endpoint_returns_json():
    response = app.test_client().get("/api/inexistente")
    assert response.status_code == 404
    assert response.is_json
