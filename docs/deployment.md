## Backend setup

The API reads `DATABASE_URL`, `SESSION_SECRET`, `CORS_ORIGINS`, and session-cookie settings from the environment. It uses `backend/.env` if present, otherwise the workspace-root `.env`. Keep the real `.env` file local; the repository ignores it. Do not put database URLs, secrets, or administrator credentials in source control.

If the workspace-root `.env` does not already exist, copy the safe template from the repository root and replace its placeholders with the Neon connection URL and a randomly generated session secret:

```sh
cp backend/.env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `SESSION_COOKIE_SECURE=false` only for local HTTP development. Set `ENVIRONMENT=production` and `SESSION_COOKIE_SECURE=true` in production; the application rejects production settings that disable secure cookies. Configure `CORS_ORIGINS` with the exact deployed frontend origin(s), comma-separated. Do not use `*` when cookies are enabled.

Install dependencies and explicitly create the first administrator. On startup, SQLAlchemy creates tables that do not exist yet and leaves existing tables and rows untouched. The setup command prompts for the username and password; it does not accept credentials as command-line arguments and stores only an Argon2 password hash. Passwords must be 12-128 characters.

```sh
uv sync --all-groups
uv run python -m app.cli create-admin
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`create_all` does not alter existing columns. If a future change requires modifying a live table, make that change explicitly and back up Neon first. The API never drops tables or shipment data at startup.

### Hosting on a custom domain

Deploy the repository root as one web service so the API and static frontend share an origin. Configure `DATABASE_URL`, a persistent random `SESSION_SECRET`, `ENVIRONMENT=production`, `SESSION_COOKIE_SECURE=true`, and the deployed origin in `CORS_ORIGINS`. Use the platform's HTTPS certificate and map the custom domain through its domain/DNS settings.

For a host with `uv` available, use these commands from `backend/`:

```sh
uv sync --no-dev --frozen
uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Set the platform health-check path to `/health`. The frontend is served by the same FastAPI process, so no separate frontend build or API URL is required.

Serve the static frontend over HTTP from an origin listed in `CORS_ORIGINS`. The frontend API wrapper defaults to same-origin requests; if frontend and API have different origins, set `settings.baseUrl` in `frontend/js/api.js` to the API origin. Requests include cookies for allowlisted origins. The public endpoint is `GET /api/tracking/{tracking_id}`. Admin login uses `POST /api/auth/login`; shipment CRUD uses `/api/admin/shipments` and signed, HTTP-only session cookies. `GET /health` is a lightweight process health check and does not verify database connectivity.

Run backend tests from `backend/` with:

```sh
uv run pytest -c pyproject.toml ../tests
```

Tests forcibly use an isolated in-memory SQLite database and never connect to Neon.
