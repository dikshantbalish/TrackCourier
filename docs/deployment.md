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

### Deploying to Render

The repository includes [`render.yaml`](../render.yaml), a Render Blueprint for
one Python web service. It uses the repository root as the service root and runs
build/start commands from `backend/`; this lets the existing FastAPI app serve
the `frontend/` directory from the same origin.

1. Push the repository to GitHub.
2. In Render, create a new **Blueprint** and select the repository. Render reads
   `render.yaml`; review and create the `trackcourier` web service.
3. Supply `DATABASE_URL` when prompted. Use a production PostgreSQL connection
   URL with TLS enabled. The Blueprint generates a random `SESSION_SECRET`.
4. After the service is created, open its Environment settings and set
   `CORS_ORIGINS` to the exact origin(s) that host the frontend. For this
   same-origin deployment, use the Render service's HTTPS URL; add the custom
   domain's HTTPS origin after attaching it. Separate origins must be
   comma-separated. Do not use `*`.
5. Wait for the first deploy to complete, then create the first admin as
   described below.

The resulting commands (also suitable for a manually configured Render
service) are:

**Build Command**

```sh
pip install uv && cd backend && uv sync --no-dev --frozen
```

**Start Command**

```sh
cd backend && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set the health-check path to `/health`. The app binds to all interfaces and
uses the hosting platform's `PORT`; local development can continue using port
8000. The frontend is served by the same FastAPI process, so no separate
frontend build or API URL is required.

### Environment variables

Configure these in the hosting platform's secret/environment settings; do not
commit their values:

| Variable | Required | Production value |
| --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL connection URL from the database provider, with TLS enabled |
| `SESSION_SECRET` | Yes | Persistent random secret of at least 32 characters; Render Blueprint generates one |
| `CORS_ORIGINS` | Yes | Exact HTTPS frontend origin(s), comma-separated |
| `ENVIRONMENT` | Yes | `production` |
| `SESSION_COOKIE_SECURE` | Yes | `true` |
| `SESSION_MAX_AGE_SECONDS` | No | Defaults to `28800` (8 hours) |

Keep the generated `SESSION_SECRET` stable across deploys; rotating it
invalidates existing admin sessions. Production startup rejects an insecure
session-cookie setting.

### First admin and schema changes

After the initial deploy, use the platform's one-off shell/command feature in
the `backend/` directory to run:

```sh
uv run --no-sync python -m app.cli create-admin
```

This command prompts for the administrator credentials; use an interactive
shell. Do not put passwords in a build/start command or source control. The
app creates missing database tables at startup, but `create_all` does not
alter existing tables. For schema changes to existing production data, use an
explicit migration and take a verified database backup first.

### Custom domain and HTTPS

Attach the chosen domain in the Render service's **Settings → Custom Domains**
page. Render will provide the DNS record values for that domain; configure
those exact records with the DNS provider, remove conflicting records if
Render instructs you to, and wait for DNS verification and TLS certificate
provisioning. HTTPS is required because production admin sessions use secure
cookies. After HTTPS works on the custom domain, add its exact origin to
`CORS_ORIGINS` and redeploy/restart if required. No domain is hard-coded in the
application.

For another provider, deploy the repository root as one web service, use the
same `uv` build/start commands, provide the required environment variables,
and configure the health check at `/health`. Configure TLS and domain DNS
through that provider.

Serve the static frontend over HTTPS from an origin listed in `CORS_ORIGINS`.
The frontend API wrapper defaults to same-origin requests; if frontend and API
have different origins, set `settings.baseUrl` in `frontend/js/api.js` to the
API origin. Requests include cookies for allowlisted origins. The public
endpoint is `GET /api/tracking/{tracking_id}`. Admin login uses
`POST /api/auth/login`; shipment CRUD uses `/api/admin/shipments` and signed,
HTTP-only session cookies. `GET /health` is a lightweight process health check
and does not verify database connectivity.

### Database, storage, and operations

The application is configured for PostgreSQL through `DATABASE_URL`; do not
use an ephemeral local SQLite file for production shipment/admin data. Use a
managed PostgreSQL service and configure its automated backups, retention, and
restore procedure. No user uploads or persistent local-file data are used by
the app; frontend files are static files deployed with the repository.

The health check confirms that the web process responds, not that PostgreSQL is
reachable. Configure platform/database monitoring and alerts, and test
database recovery before relying on production data. Protect the public service
with platform-level request/rate controls as appropriate; the app has no
application-level rate limiter.

### Troubleshooting

- **Service fails during startup:** confirm `DATABASE_URL` and
  `SESSION_SECRET` are set, `ENVIRONMENT=production`, and
  `SESSION_COOKIE_SECURE=true`. Check deploy logs for database connectivity
  errors.
- **Static page or assets return 404:** deploy from the repository root and
  keep the `frontend/` directory in the deployment.
- **Browser requests fail across origins:** set `CORS_ORIGINS` to exact
  `https://` origins with no trailing paths; check the browser console. For a
  same-origin frontend and API, no separate API base URL is needed.
- **Admin login does not persist:** access the site over HTTPS, keep
  `SESSION_SECRET` stable, and ensure the browser accepts cookies.
- **Health check fails:** verify the platform is using `/health`, the start
  command binds to `0.0.0.0`, and the platform-provided `PORT` is used.

Run backend tests from `backend/` with:

```sh
uv run pytest -c pyproject.toml ../tests
```

Tests forcibly use an isolated in-memory SQLite database and never connect to Neon.
