# Multi-stage Docker build for production deployment
# Optimized for AI model loading and FastAPI serving

FROM python:3.11.9-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy application code
COPY app/ app/
COPY ai_models/ ai_models/
COPY templates/ templates/
COPY alembic/ alembic/
COPY alembic.ini .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Create directories for models and storage
RUN mkdir -p /app/models /app/storage

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]