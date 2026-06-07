# N.I.X — Agent Guide

Python server + Web Dashboard. See root `AGENTS.md` for cross-project context.

## Commands

```sh
python nix.py                      # dev server with hot reload (uvicorn)
uv sync                            # sync dependencies (uv.lock)
```

Python `>=3.13,<3.14`. Server listens on `http://0.0.0.0:8000`.

## Architecture

- **Framework**: FastAPI with Jinja2 templates, SQLModel (SQLite)
- **Auth**: Starlette `SessionMiddleware` (web) + JWT HS256 (API), TOTP 2FA via `pyotp`
- **Rate limiting**: login endpoint limited to 5 requests/min via `slowapi`
- **Logging**: 3 rotating files (10MB each) — `server.log` (INFO+), `security.log` (WARNING+), `errors.log` (ERROR+); `SensitiveDataFilter` redacts passwords/tokens/keys

## Key files

| File | Role |
|------|------|
| `nix.py` | Entrypoint: runs uvicorn |
| `app/main.py` | FastAPI app factory, middleware, router registration |
| `app/models/__init__.py` | SQLModel session, CRUD helpers for User/Device/Token |
| `app/models/users.py` | `User` + `Token` SQLModel tables |
| `app/models/devices.py` | `Device` SQLModel table |
| `app/web/pages.py` | Web page route handlers (Jinja2 templates) |
| `app/api/user.py` | Auth endpoints (login, register, 2FA, password reset) + preferences (notification_email) |
| `app/api/device.py` | Device management (add, toggle, QR gen, delete) |
| `app/api/comms.py` | Three WS endpoints: `/ws/comms/{uid}/{did}`, `/ws/events/{uid}`, `/ws/device/{uid}/{did}` |
| `app/api/cmd_requests.py` | CMD/terminal request handlers |
| `app/core/auth.py` | JWT validation, `login_required` decorator, 2FA verify, QR gen, `verify_ws_token()` |
| `app/core/config.py` | Env loading, paths, limiter, Jinja2 templates |
| `app/core/jwt_utility.py` | JWT encode/decode helpers |
| `app/core/sLogger.py` | Logging config with rotating files + sensitive data filter |
| `app/core/middleware.py` | Request logging middleware |
| `templates/connect.html` | CMD Line terminal interface (Jinja2) |
| `static/js/connect.js` | CMD Line WS client |
| `.env` | Required: `SECRET_KEY`, `EMAIL_HOST`, `EMAIL_HOST_PASSWORD`, `ADMIN_EMAIL` |

## DB

SQLite file at `Database/database.db`. Tables: `user`, `device`, `token`.

Relationships: `User 1─N Device` (via `Device.owner`), `User 1─N Token` (via `Token.owner`), `Token 0..1─1 Device` (via `Token.linked_device`).

> When adding new columns to the `User` model, delete `Database/database.db` to recreate schema.

User model fields: `uid`, `email`, `username`, `password`, `verification_code`, `code_expires_at`, `twoFA_secret`, `is_2FA_enabled`, `notification_email` (nullable).

## WebSocket architecture

- `WSConnectionManager` routes by `user_id` — three dicts: `user_connections`, `device_connections`, `device_to_user`
- All WS endpoints require JWT `?token=` query param on connect
- `/ws/events/{uid}` — receives typed JSON commands, broadcasts events (`device_status_change`, `2fa_toggled`, etc.)
- `/ws/device/{uid}/{did}` — receives `toggle_status`, `refresh` commands, broadcasts status changes
- `/ws/comms/{uid}/{did}` — legacy device-to-device messaging

## Known issues

- No token refresh mechanism — 30-day JWT expiry
- User model doc in old code still mentions `language` field (removed)
