Render Deployment Notes

Summary
- This repo now includes a root `Dockerfile` that installs dependencies from the root `requirements.txt` and uses Python 3.11.9 (matches `runtime.txt`).
- The `infra/Dockerfile` was also adjusted to install from the root `requirements.txt` for consistency.

Quick steps to deploy on Render (free tier)
1. Create a new Web Service on Render and connect your GitHub repo (or link by manual deploy).
2. For "Environment", choose "Docker" (Render will build using the `Dockerfile` at the repository root).
3. Build & Run command (Render will use the CMD in the `Dockerfile`):
   - The Docker CMD defaults to: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Health check: leave default or set to `http://$PORT/health`.

Important notes and recommendations
- Python version: The project declares Python 3.11 in `pyproject.toml` and `runtime.txt` (3.11.9). The Dockerfiles use `python:3.11.9-slim` to match the environment and avoid incompatibilities.

- Large ML deps: `requirements.txt` contains heavy ML libraries (examples: `torch`, `bitsandbytes`, `transformers` commented out but may be installed if you add them). The Render free service has resource limits and may fail or be very slow installing or running these packages. Recommended options:
  - Remove heavy ML libraries from the base `requirements.txt` and keep them in an optional `requirements-ai.txt` for local/production GPU hosts.
  - Use a lightweight inference API (Hugging Face Inference, Replicate, or a separate VM/managed GPU instance) and keep this service as the API proxy.
  - If you must include `torch`, pin a CPU-only wheel compatible with Python 3.11 and ensure build time fits Render's build timeout.

- Database and background services: The repo uses Postgres and Redis in `docker-compose.yml` for local development. Render's free tier supports managed Postgres (Paid) or you can use a hosted DB (Supabase, Neon). Configure `DATABASE_URL` and `REDIS_URL` in Render Environment settings.

Troubleshooting
- Build fails on dependency install:
  - Check the Render deploy logs for the pip error. Common causes: incompatible Python version, binary wheels not available for platform, or lack of system libs (e.g., `libssl-dev`, `libxml2-dev`).
  - Consider adding extra apt packages to the root `Dockerfile` (only if necessary).

Follow-ups (optional)
- Add a trimmed `requirements.render.txt` with only runtime deps (no dev/test/AI heavy libs) and point the Dockerfile at that for faster builds on Render.
- Add a separate CI step to build a smaller image and push to a registry.


