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


def test_signup_requests_email_confirmation_with_frontend_redirect(monkeypatch):
    calls = []

    def fake_upstream(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"id": "user-1", "email": "aluno@example.com"}, None

    monkeypatch.setattr(
        "app.EMAIL_CONFIRMATION_REDIRECT_URL",
        "https://frontend-matquest.vercel.app/email-confirmado.html",
    )
    monkeypatch.setattr("app.upstream", fake_upstream)

    response = app.test_client().post("/api/auth/signup", json={
        "email": "aluno@example.com",
        "password": "senha-segura",
        "name": "Aluno",
    })

    assert response.status_code == 200
    assert response.get_json() == {"id": "user-1", "email": "aluno@example.com"}
    assert calls[0][1] == "/auth/v1/signup"
    assert calls[0][2]["params"] == {
        "redirect_to": "https://frontend-matquest.vercel.app/email-confirmado.html",
    }
    assert calls[0][2]["json"]["data"] == {"display_name": "Aluno"}


def test_signup_rejects_unapproved_confirmation_redirect(monkeypatch):
    calls = []

    def fake_upstream(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {}, None

    monkeypatch.setattr("app.EMAIL_CONFIRMATION_REDIRECT_URL", "https://attacker.example/confirm")
    monkeypatch.setattr("app.upstream", fake_upstream)

    response = app.test_client().post("/api/auth/signup", json={
        "email": "aluno@example.com",
        "password": "senha-segura",
    })

    assert response.status_code == 503
    assert response.get_json() == {"error": "Configure uma URL de confirmação permitida para o front-end."}
    assert calls == []


def test_resend_confirmation_uses_supabase_signup_resend(monkeypatch):
    calls = []

    def fake_upstream(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {}, None

    monkeypatch.setattr("app.upstream", fake_upstream)

    response = app.test_client().post("/api/auth/resend-confirmation", json={
        "email": "aluno@example.com",
    })

    assert response.status_code == 200
    assert calls[0][1] == "/auth/v1/resend"
    assert calls[0][2]["params"]["redirect_to"].endswith("/email-confirmado.html")
    assert calls[0][2]["json"] == {"type": "signup", "email": "aluno@example.com"}
    assert "Se houver" in response.get_json()["message"]


def test_signup_rejects_missing_email_or_password():
    response = app.test_client().post("/api/auth/signup", json={"email": "aluno@example.com"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Informe um e-mail e uma senha."}


def test_resend_confirmation_rejects_invalid_email():
    response = app.test_client().post("/api/auth/resend-confirmation", json={"email": "invalido"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Informe um e-mail válido."}
