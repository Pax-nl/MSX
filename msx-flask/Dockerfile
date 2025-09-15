# Lightweight Alpine-based image for the MSX Flask Directory Server
# Multi-stage not required (pure-Python dependency: Flask)

FROM python:3.12-alpine

# Set environment (avoid .pyc, ensure unbuffered logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Security: add non-root user
RUN addgroup -S app && adduser -S app -G app

WORKDIR /app

# Install runtime deps (none needed for Flask itself, but keep build tools easy to add)
# RUN apk add --no-cache build-base

# Requirements first for layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt


# Copy application and .env file
COPY flask_directory_server.py ./
COPY .env ./

# Create (empty) msx directory; mount a volume at runtime to populate
RUN mkdir -p msx && chown -R app:app msx

USER app

EXPOSE 5001

# Basic healthcheck hits root (fast). Adjust interval as needed.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:5001/ || exit 1

CMD ["python", "flask_directory_server.py"]
