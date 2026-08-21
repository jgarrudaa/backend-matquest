from backend.app import app


def test_health_endpoint():
    response = app.test_client().get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"app": "TriQuest API", "status": "ok"}


def test_api_root():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "online"
    assert response.get_json()["health"] == "/api/health"


def test_protected_endpoint_requires_token():
    response = app.test_client().get("/api/dashboard")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Autenticação necessária."}


def test_unknown_endpoint_returns_json():
    response = app.test_client().get("/api/inexistente")
    assert response.status_code == 404
    assert response.is_json


def test_production_frontend_is_allowed_by_cors():
    response = app.test_client().options(
        "/api/auth/login",
        headers={
            "Origin": "https://frontend-matquest.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://frontend-matquest.vercel.app"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]


def test_unknown_origin_is_not_allowed_by_cors():
    response = app.test_client().options(
        "/api/auth/login",
        headers={"Origin": "https://site-nao-autorizado.example"},
    )
    assert "Access-Control-Allow-Origin" not in response.headers
