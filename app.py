"""API REST do TriQuest."""

import os
from pathlib import Path

import requests
from flask import Flask, jsonify, request

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key and not key.startswith("#"):
                os.environ.setdefault(key, value)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
TIMEOUT = 15
DEFAULT_FRONTEND_ORIGINS = {
    "https://frontend-matquest.vercel.app",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
}


def allowed_frontend_origins():
    configured_origins = os.getenv("FRONTEND_ORIGINS", "").split(",")
    return DEFAULT_FRONTEND_ORIGINS | {origin.strip() for origin in configured_origins if origin.strip()}


def supabase_is_configured():
    invalid_url = not SUPABASE_URL or "seu-projeto.supabase.co" in SUPABASE_URL
    invalid_key = not SUPABASE_KEY or SUPABASE_KEY == "sua_chave_publicavel"
    return not invalid_url and not invalid_key


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    allowed_origins = allowed_frontend_origins()
    if origin and ("*" in allowed_origins or origin in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers.add("Vary", "Origin")
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


def supabase_headers(*, token=None, prefer=None, admin=False):
    api_key = SUPABASE_SERVICE_ROLE_KEY if admin else SUPABASE_KEY
    headers = {"apikey": api_key, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if prefer:
        headers["Prefer"] = prefer
    return headers


def access_token():
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def upstream(method, path, *, token=None, params=None, json=None, prefer=None, admin=False):
    if not supabase_is_configured():
        return None, (jsonify(error="O Supabase não foi configurado no back-end."), 503)
    try:
        response = requests.request(
            method,
            f"{SUPABASE_URL}{path}",
            headers=supabase_headers(token=token, prefer=prefer, admin=admin),
            params=params,
            json=json,
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        app.logger.exception("Falha de conexão com o Supabase")
        return None, (jsonify(error="Não foi possível acessar o banco de dados."), 502)

    try:
        payload = response.json() if response.content else None
    except requests.JSONDecodeError:
        payload = None

    if not response.ok:
        error_payload = payload if isinstance(payload, dict) else {}
        message = (
            error_payload.get("msg")
            or error_payload.get("message")
            or error_payload.get("error_description")
        )
        return None, (jsonify(error=message or "A operação não pôde ser concluída."), response.status_code)

    return payload, None


def require_token():
    token = access_token()
    if not token:
        return None, (jsonify(error="Autenticação necessária."), 401)
    return token, None


def current_user(token):
    return upstream("GET", "/auth/v1/user", token=token)


@app.get("/api/health")
def health():
    return jsonify(app="TriQuest API", status="ok")


@app.get("/")
def index():
    return jsonify(
        app="TriQuest API",
        status="online",
        health="/api/health",
        message="API do TriQuest funcionando corretamente.",
    )


@app.post("/api/auth/signup")
def signup():
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify(error="Envie os dados de cadastro em formato JSON."), 400

    email = str(body.get("email", "")).strip()
    password = body.get("password")
    if not email or not isinstance(password, str) or not password:
        return jsonify(error="Informe um e-mail e uma senha."), 400

    display_name = str(body.get("name", "")).strip()
    if SUPABASE_SERVICE_ROLE_KEY:
        user, error = upstream("POST", "/auth/v1/admin/users", token=SUPABASE_SERVICE_ROLE_KEY, json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": display_name},
        }, admin=True)
        if error:
            return error
        payload, error = upstream("POST", "/auth/v1/token", params={"grant_type": "password"}, json={
            "email": email,
            "password": password,
        })
    else:
        payload, error = upstream("POST", "/auth/v1/signup", json={
            "email": email,
            "password": password,
            "data": {"display_name": display_name},
        })
    return error or jsonify(payload)


@app.post("/api/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    payload, error = upstream("POST", "/auth/v1/token", params={"grant_type": "password"}, json={
        "email": str(body.get("email", "")).strip(),
        "password": body.get("password", ""),
    })
    return error or jsonify(payload)


@app.get("/api/auth/me")
def me():
    token, error = require_token()
    if error:
        return error
    payload, error = current_user(token)
    return error or jsonify(payload)


@app.get("/api/questions")
def questions():
    topic = request.args.get("topic")
    params = {
        "select": "id,topic,prompt,options,correct_answer,hint,explanation",
        "is_active": "eq.true",
    }
    if topic in {"seno", "cosseno", "tangente", "razoes"}:
        params["topic"] = f"eq.{topic}"
    payload, error = upstream("GET", "/rest/v1/questions", params=params)
    return error or jsonify(payload)


@app.get("/api/dashboard")
def dashboard():
    token, error = require_token()
    if error:
        return error
    user, error = current_user(token)
    if error:
        return error
    user_id = user["id"]
    progress, error = upstream("GET", "/rest/v1/user_progress", token=token, params={
        "select": "score,total_correct,current_streak", "user_id": f"eq.{user_id}", "limit": 1,
    })
    if error:
        return error
    questions_data, error = upstream("GET", "/rest/v1/questions", params={"select": "id,topic", "is_active": "eq.true"})
    if error:
        return error
    attempts, error = upstream("GET", "/rest/v1/attempts", token=token, params={
        "select": "question_id,is_correct", "user_id": f"eq.{user_id}",
    })
    if error:
        return error
    return jsonify(user=user, progress=(progress or [{}])[0], questions=questions_data or [], attempts=attempts or [])


@app.post("/api/attempts")
def create_attempt():
    token, error = require_token()
    if error:
        return error
    user, error = current_user(token)
    if error:
        return error
    body = request.get_json(silent=True) or {}
    record = {
        "user_id": user["id"],
        "question_id": body.get("question_id"),
        "selected_answer": body.get("selected_answer"),
        "is_correct": bool(body.get("is_correct")),
        "points_earned": body.get("points_earned", 0),
        "response_time_seconds": body.get("response_time_seconds", 0),
    }
    payload, error = upstream("POST", "/rest/v1/attempts", token=token, json=record, prefer="return=representation")
    return error or (jsonify(payload), 201)


@app.errorhandler(404)
def not_found(_error):
    return jsonify(error="Endpoint não encontrado."), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
