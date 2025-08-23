# Minimal Dockerfile for Render deployment
# Uses the root requirements.txt and Python 3.11.9

FROM python:3.11.9-slim

# System deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       git \
    && rm -rf /var/lib/apt/lists/*

# Working dir
WORKDIR /app

# Copy project files
COPY . /app

# Upgrade pip and install trimmed runtime dependencies for Render (faster builds)
COPY requirements.render.txt /app/requirements.render.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.render.txt

# Create non-root user and fix permissions
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck for Render
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command (Render will use this). Adjust as needed.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
