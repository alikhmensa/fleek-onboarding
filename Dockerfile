# Fleek Sourcing Copilot — one container serves the API and the frontend.
# Build from the repo root:  docker build -t fleek-copilot .
FROM python:3.13-slim

WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY frontend frontend

WORKDIR /srv/backend
EXPOSE 8000
# PORT is injected by Render/Railway/Fly; DB_DIR should point at a mounted
# volume in production so SQLite (users, profiles, tokens) survives deploys.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
