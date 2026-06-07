# N.I.X — Network Intercom Xceeded

A real-time, account-synced virtual assistant platform that connects and manages devices over the internet — no LAN required. Built with **FastAPI**, **Jinja2**, and **SQLite**, with a companion **Flutter** [mobile app](https://github.com/arman29-dev/N.I.X-App).

---

## Features

- **Device Management** — Register, toggle, and delete devices via REST API or WebSocket
- **Real-Time Control** — WebSocket push for instant device status changes across all clients
- **Web Dashboard** — Browser-based UI for monitoring and managing devices
- **Mobile Client** — Flutter app for device control on the go
- **Two-Factor Authentication** — TOTP-based 2FA enabled by default for all new users
- **Email Notifications** — Password resets, account changes, and welcome emails via SMTP
- **QR Code Device Registration** — Scan a QR code from the web dashboard to link a device
- **Rate Limiting** — Login endpoint protected (5 req/min via `slowapi`)
- **Structured Logging** — Console + rotating file logs with sensitive data redaction
- **No LAN Requirement** — All communication routes through the central server

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Python 3.13, FastAPI |
| Database | SQLite via SQLModel / SQLAlchemy |
| Web UI | Jinja2, Tailwind CSS (CDN), vanilla JS |
| Auth | JWT (HS256), Starlette SessionMiddleware |
| 2FA | TOTP via `pyotp` |
| WS | `websockets` (via uvicorn[standard]) |
| Email | SMTP (Gmail) |
| Rate Limit | `slowapi` |
| Package Manager | `uv` |
| Mobile Client | Flutter / Dart (separate project at `../N.I.X-App/`) |

---

## Architecture

```
Browser ──HTTP──> FastAPI Server ──SQLite──> Database
   │                    │
   │     ┌──────────────┤
   ▼     ▼              ▼
 WebSocket           REST API
/ws/events/{uid}     /api/v1/*
   │
   │  WebSocket broadcast
   │
   └── /ws/device/{uid}/{did} (Flutter)
   └── /ws/comms/{uid}/{did}  (Legacy messaging)
```

- **Server** is the central hub — all clients connect to it
- **WebSocket** auth is validated on connect (JWT in `?token=` query param), not per-message
- **REST API** auth uses `Authorization: Bearer` header or `authToken` cookie
- **Web sessions** use Starlette `SessionMiddleware` for page rendering

---

## Project Structure

```
N.I.X/
├── nix.py                  # Server entrypoint (uvicorn runner)
├── pyproject.toml          # Python dependencies & metadata
├── uv.lock                 # Lock file (uv)
├── .env                    # Environment variables (gitignored)
├── .env.example            # Template for .env
│
├── app/
│   ├── main.py             # FastAPI app factory, middleware, router registration
│   ├── api/
│   │   ├── __init__.py     # APIRouters, WSConnectionManager, login()
│   │   ├── comms.py        # 3 WebSocket endpoints
│   │   ├── device.py       # Device CRUD endpoints
│   │   ├── forms.py        # Pydantic request models
│   │   └── user.py         # User auth endpoints
│   ├── core/
│   │   ├── auth.py         # JWT validation, 2FA, QR gen, login_required
│   │   ├── config.py       # Env loading, paths, rate limiter, Jinja2
│   │   ├── emailing.py     # SMTP email sender
│   │   ├── jwt_utility.py  # JWT encode/decode helpers
│   │   ├── middleware.py   # Request logging middleware
│   │   └── sLogger.py      # Logging setup with SensitiveDataFilter
│   ├── models/
│   │   ├── __init__.py     # SQLModel engine, session, all CRUD helpers
│   │   ├── devices.py      # Device SQLModel table
│   │   └── users.py        # User + Token SQLModel tables
│   └── web/
│       ├── __init__.py     # webApp APIRouter, session helpers
│       └── pages.py        # Web page route handlers
│
├── templates/              # Jinja2 HTML templates
│   ├── index.html          # Landing page
│   ├── home.html           # Login / Register page
│   ├── dashboard.html      # Device management dashboard
│   ├── account-center.html # Account settings & 2FA
│   ├── 2FA-setup.html      # 2FA QR code setup
│   ├── forgot-password.html
│   ├── password-reset.html
│   └── email/              # Email templates
│
├── static/
│   ├── css/                # Page-specific CSS
│   ├── js/                 # Page-specific JavaScript (WS, auth, UI)
│   └── images/             # Favicon, assets
│
├── Database/
│   └── database.db         # SQLite database (gitignored)
│
├── logs/                   # Rotating log files (gitignored)
│   ├── server.log          # INFO+ — all requests
│   ├── security.log        # WARNING+ — rate limits, auth events
│   └── errors.log          # ERROR+ — stack traces
│
└── README.md               # This file
```

---

## Getting Started

### Prerequisites

- **Python** >=3.13, <3.14
- **uv** (package manager)
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) for email sending

### Installation

```sh
git clone <repo-url>
cd N.I.X
uv sync
```

### Configuration

Create a `.env` file (or copy from `.env.example`):

```env
SECRET_KEY = 'your-server-secret-key'
EMAIL_HOST = "your-email@gmail.com"
EMAIL_HOST_PASSWORD = "your-16-char-app-password"
```

### Run

```sh
python nix.py
# or: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server starts at `http://0.0.0.0:8000`.

---

## Configuration Reference

| Env Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Session encryption + JWT signing |
| `EMAIL_HOST` | Yes | Gmail address used for sending emails |
| `EMAIL_HOST_PASSWORD` | Yes | Gmail App Password (not your account password) |

---

## API Reference

### Web Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Landing page |
| GET | `/web/home` | Login / Register page |
| GET | `/web/dashboard/{uid}` | Device management dashboard (auth required) |
| GET | `/web/account/{uid}` | Account center & 2FA settings (auth required) |
| GET | `/web/auth/setup-2FA/{uid}` | 2FA QR code setup |
| GET | `/web/account/logout/` | Logout (auth required) |
| GET | `/web/account/security/forgot-password` | Password reset form |
| GET | `/web/account/security/password-reset/{uid}` | Password reset page |
| POST | `/web/auth/login/` | Login form handler (rate limited: 5/min) |
| POST | `/web/auth/register/` | Registration form handler |
| POST | `/web/auth/2FA/verify` | 2FA verification during login |
| PUT | `/web/account/security/password-reset/{uid}` | Password reset submission |

### REST API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ping` | None | Health check (`{"status": "Online"}`) |
| POST | `/api/v1/user/auth/login` | None | API login (returns JWT + token_uid) |
| POST | `/api/v1/user/auth/2FA/setup` | None | Verify & enable 2FA |
| GET | `/api/v1/user/auth/2FA/toggle-setting` | JWT | Toggle 2FA on/off |
| POST | `/api/v1/user/account/security/forgot-password` | None | Request password reset code |
| DELETE | `/api/v1/user/account/manage/delete-account` | JWT | Delete account (requires 2FA) |
| POST | `/api/v1/device/util/generate-qr` | JWT | Generate device registration QR |
| POST | `/api/v1/device/manage/add-device` | JWT | Register a new device |
| GET | `/api/v1/device/manage/toggle-status` | JWT | Toggle device active status |
| POST | `/api/v1/device/manage/logout` | JWT | Deregister & unlink a device |
| DELETE | `/api/v1/device/manage/delete-all` | JWT | Delete all devices (requires 2FA) |

### REST API Auth

- **Bearer token**: Add `Authorization: Bearer <jwt>` header
- **Cookie**: Server also reads `authToken` cookie as fallback

### WebSocket Endpoints

| Path | Purpose | Auth |
|------|---------|------|
| `/ws/events/{user_id}` | Dashboard events stream | JWT `?token=` |
| `/ws/device/{user_id}/{device_id}` | Device control (Flutter app) | JWT `?token=` |
| `/ws/comms/{user_id}/{device_id}` | Legacy messaging | JWT `?token=` |

All WS endpoints require JWT as `?token=` query parameter on connection.

---

## WebSocket Architecture

### WSConnectionManager

A singleton (`app/api/__init__.py:WSConnectionManager`) manages three data structures:

- **`user_connections`** — `dict[str, list[WebSocket]]` — Maps user UUID to browser WS connections. Multiple browser tabs each get their own entry.
- **`device_connections`** — `dict[str, WebSocket]` — Maps device UUID to its Flutter WS connection. One device = one connection.
- **`device_to_user`** — `dict[str, str]` — Maps device UUID → user UUID, enabling reverse lookup.

### Event Flow

```
Flutter App                    Server                         Browser
    │                            │                               │
    │── toggle_status ──────>  /ws/device/{uid}/{did}           │
    │                           │                               │
    │                           ├── DB: toggle device           │
    │                           │                               │
    │<── response ─────────────┘                               │
    │                           │                               │
    │                           └── send_to_user() ──────────> /ws/events/{uid}
    │                                                           │
    │                                                    handleDeviceStatusChange()
```

### Events

| Event | Payload | Trigger |
|-------|---------|---------|
| `device_added` | `{uid, name, type, ip, is_active}` | Device registered via `manage/add-device` |
| `device_status_change` | `{uid, is_active}` | Device toggled via WS or `toggle-status` |
| `device_removed` | `{uid}` | Device deregistered |
| `2fa_toggled` | `{is_enabled}` | 2FA toggled via WS or API |

### Commands (sent to server)

| Endpoint | Action | Payload |
|----------|--------|---------|
| `/ws/events/{uid}` | `toggle_2fa` | `{action: "toggle_2fa"}` |
| `/ws/device/{uid}/{did}` | `toggle_status` | `{action: "toggle_status"}` |
| `/ws/device/{uid}/{did}` | `refresh` | `{action: "refresh"}` |

---

## Authentication Flow

### Web Login
1. Submit email + password to `POST /web/auth/login/`
2. If 2FA enabled → redirect to 2FA verification → `POST /web/auth/2FA/verify`
3. Server creates session (cookie) and returns JWT in JSON body
4. Client stores JWT as `authToken` cookie via JavaScript
5. JS uses `authToken` cookie for WS connection and API calls

### API Login (Flutter)
1. Submit email + password + 2FA code to `POST /api/v1/user/auth/login`
2. Server returns `access_token` (JWT) + `access_token_uid`
3. Flutter stores token and uses it for all subsequent API calls + WS auth
4. Token is registered in DB as a `Token` record (linked to a device later)

### Device Registration (QR Code)
1. Web dashboard generates QR via `POST /api/v1/device/util/generate-qr`
2. QR encodes: `{device_uid, secret, user_access_token}`
3. Flutter scans QR, decodes both stored JWT and QR token using `secret`
4. If tokens match, calls `POST /api/v1/device/manage/add-device`
5. On success, establishes WS connection to `/ws/device/{uid}/{did}`

---

## Database

**File:** `Database/database.db` (SQLite)

### Tables

#### `user`
| Column | Type | Notes |
|--------|------|-------|
| uid | str (PK) | UUID v4 |
| email | str | Unique |
| username | str | |
| password | str | pbkdf2_sha256 hash |
| twoFA_secret | str | Base32 for TOTP |
| is_2FA_enabled | bool | Default: `true` |
| verification_code | str | 6-digit reset code |
| code_expires_at | datetime | Code expiry |

#### `device`
| Column | Type | Notes |
|--------|------|-------|
| uid | UUID (PK) | |
| name | str | Device model / friendly name |
| type | str | `smartphone`, `laptop`, `embedded` |
| ip | str | IPv4 address |
| is_active | bool | Online/offline status |
| is_revoked | bool | |
| owner | str (FK) | References `user.uid` |

#### `token`
| Column | Type | Notes |
|--------|------|-------|
| uid | UUID (PK) | |
| owner | str (FK) | References `user.uid` |
| access_token | str | JWT string |
| created_at | datetime | |
| expires_at | datetime | 30 days from creation |
| linked_device | str (FK) | References `device.uid` |

### Relationships
- `User` 1→N `Device` (via `device.owner`)
- `User` 1→N `Token` (via `token.owner`)
- `Token` 0..1→1 `Device` (via `token.linked_device`)

---

## Logging

Three rotating file handlers (10 MB each, multiple backups) in `logs/`:

| File | Level | Content |
|------|-------|---------|
| `server.log` | INFO+ | All requests, WS events, general operation |
| `security.log` | WARNING+ | Rate limit events, auth failures, 2FA toggles |
| `errors.log` | ERROR+ | Stack traces, database errors, unhandled exceptions |

A `SensitiveDataFilter` automatically redacts:
- 6-digit codes (2FA, password reset)
- Passwords in log messages
- Tokens, keys, and secrets

---

## Security

| Layer | Implementation |
|-------|---------------|
| Password hashing | `pbkdf2_sha256` (via `passlib`) |
| 2FA | TOTP (via `pyotp`) — enabled by default |
| JWT | HS256, 30-day expiry |
| Web session | Signed cookie via `SessionMiddleware` |
| WS auth | JWT validated on connect, per-route user/device ownership check |
| Rate limiting | Login: 5 requests/minute via `slowapi` |
| Headers | `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `HSTS` |
| CORS | Not configured (all origins from same server) |
| Trusted hosts | `localhost`, `127.0.0.1`, ngrok URL whitelisted |

---

## Known Issues

- **No token refresh**: JWT expires after 30 days with no refresh mechanism

---

## License

MIT License — Copyright (c) 2025 Arman Das. See `LICENSE` for details.
>>>>>>> e0df7de (Document Project Architecture and APIs)
