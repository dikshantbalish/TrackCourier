# TrackCourier

FastAPI shipment-tracking application with an HTML/CSS/JavaScript frontend and
PostgreSQL-backed admin and shipment data.

## Local development

Requires Python 3.13 and [`uv`](https://docs.astral.sh/uv/).

```sh
cd backend
uv sync --all-groups
cp -n .env.example ../.env
```

Set `DATABASE_URL` and a random `SESSION_SECRET` in the root `.env`. Then run:

```sh
uv run python -m app.cli create-admin
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. The API documentation is available at
<http://localhost:8000/docs>.

## Deployment

See [the deployment guide](docs/deployment.md) for environment variables,
Render setup, database requirements, custom-domain/HTTPS steps, and
troubleshooting. A Render Blueprint is provided in [`render.yaml`](render.yaml).

Run backend tests from `backend/` with:

```sh
uv run pytest -c pyproject.toml ../tests
```