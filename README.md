# TriQuest API

API REST do TriQuest, desenvolvida com Flask. Esta aplicação concentra o acesso ao Supabase e entrega respostas JSON para o front-end.

## Responsabilidades

- cadastrar e autenticar usuários;
- consultar o usuário autenticado;
- fornecer as perguntas ativas do jogo;
- consultar progresso e tentativas;
- registrar novas tentativas;
- controlar CORS para os endereços autorizados do front-end.

## Requisitos

- Python 3.12 ou superior;
- projeto configurado no Supabase;
- `pip` disponível no ambiente.

## Configuração local

Entre na pasta do back-end:

```powershell
cd backend
```

Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha as variáveis:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_PUBLISHABLE_KEY=sua_chave_publicavel
FRONTEND_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
FLASK_DEBUG=1
PORT=5000
```

`FRONTEND_ORIGINS` aceita múltiplas origens separadas por vírgula. Não coloque uma chave `service_role` nesse arquivo.

## Executar

```powershell
python app.py
```

A API estará disponível, por padrão, em `http://127.0.0.1:5000`.

Teste o estado da aplicação acessando:

```text
GET http://127.0.0.1:5000/api/health
```

## Publicar na Vercel

Crie um projeto da Vercel usando o repositório do back-end. A raiz configurada na Vercel deve ser a pasta que contém `app.py` e `pyproject.toml`.

Não configure Build Command nem Output Directory. A Vercel detecta automaticamente a instância Flask chamada `app` exportada por `app.py`.

Cadastre estas variáveis em **Settings → Environment Variables**:

- `SUPABASE_URL`;
- `SUPABASE_PUBLISHABLE_KEY`;
- `FRONTEND_ORIGINS`, contendo o endereço público do front-end.

Depois de salvar as variáveis, faça um novo deploy. O endpoint de verificação será:

```text
https://seu-backend.vercel.app/api/health
```

## Endpoints

| Método | Endpoint | Autenticação | Finalidade |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Não | Verifica se a API está ativa |
| `POST` | `/api/auth/signup` | Não | Cadastra um usuário |
| `POST` | `/api/auth/login` | Não | Autentica um usuário |
| `GET` | `/api/auth/me` | Bearer token | Retorna o usuário atual |
| `GET` | `/api/questions` | Não | Retorna as perguntas ativas |
| `GET` | `/api/dashboard` | Bearer token | Retorna progresso e domínio |
| `POST` | `/api/attempts` | Bearer token | Registra uma tentativa |

## Testes

Instale o executor de testes e execute a suíte:

```powershell
pip install pytest
python -m pytest
```

## Estrutura

```text
backend/
├── tests/
│   └── test_app.py
├── .env.example
├── .gitignore
├── app.py
├── pyproject.toml
├── requirements.txt
└── README.md
```
