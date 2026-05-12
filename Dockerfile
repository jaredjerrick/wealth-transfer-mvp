# Self-host fallback. Builds the FastAPI backend; the frontend can be served
# separately on Vercel/Netlify/static-host. To run both behind one container,
# build the Next.js app to static export and copy /out into FastAPI's static
# mount — left as a follow-up for the MVP.
FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend
COPY backend/pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]" || \
    pip install pydantic fastapi 'uvicorn[standard]' reportlab httpx pytest pytest-asyncio

COPY backend/ ./
RUN python -m pytest tests/ -q

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
