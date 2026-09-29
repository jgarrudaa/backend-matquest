from app import app


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


def test_signup_confirms_user_and_returns_session_when_admin_key_is_configured(monkeypatch):
    calls = []

    def fake_upstream(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/auth/v1/admin/users":
            return {"id": "user-1"}, None
        return {"access_token": "session-token"}, None

    monkeypatch.setattr("app.SUPABASE_SERVICE_ROLE_KEY", "server-secret")
    monkeypatch.setattr("app.upstream", fake_upstream)

    response = app.test_client().post("/api/auth/signup", json={
        "email": "aluno@example.com",
        "password": "senha-segura",
        "name": "Aluno",
    })

    assert response.status_code == 200
    assert response.get_json() == {"access_token": "session-token"}
    assert calls[0][1] == "/auth/v1/admin/users"
    assert calls[0][2]["json"]["email_confirm"] is True
    assert calls[0][2]["json"]["user_metadata"] == {"display_name": "Aluno"}
    assert calls[0][2]["admin"] is True
    assert calls[0][2]["token"] == "server-secret"
    assert calls[1][1] == "/auth/v1/token"


def test_signup_uses_public_signup_when_admin_key_is_missing(monkeypatch):
    calls = []

    def fake_upstream(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"user": {"id": "user-1"}}, None

    monkeypatch.setattr("app.SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setattr("app.upstream", fake_upstream)

    response = app.test_client().post("/api/auth/signup", json={
        "email": "aluno@example.com",
        "password": "senha-segura",
    })

    assert response.status_code == 200
    assert calls[0][1] == "/auth/v1/signup"
    assert calls[0][2]["json"]["email"] == "aluno@example.com"


def test_signup_rejects_missing_email_or_password():
    response = app.test_client().post("/api/auth/signup", json={"email": "aluno@example.com"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Informe um e-mail e uma senha."}


def test_signup_returns_admin_creation_error_without_attempting_login(monkeypatch):
    calls = []

    def fake_upstream(method, path, **kwargs):
        calls.append(path)
        return None, (app.response_class(
            response='{"error":"E-mail já cadastrado."}',
            status=422,
            mimetype="application/json",
        ), 422)

    monkeypatch.setattr("app.SUPABASE_SERVICE_ROLE_KEY", "server-secret")
    monkeypatch.setattr("app.upstream", fake_upstream)

    response = app.test_client().post("/api/auth/signup", json={
        "email": "aluno@example.com",
        "password": "senha-segura",
    })

    assert response.status_code == 422
    assert response.get_json() == {"error": "E-mail já cadastrado."}
    assert calls == ["/auth/v1/admin/users"]
