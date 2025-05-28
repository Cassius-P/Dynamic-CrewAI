# Multi-stage production-ready Dockerfile for CrewAI Backend
# Stage 1: Build dependencies and compile stage
FROM python:3.11-slim as builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libc6-dev \
        libffi-dev \
        libssl-dev \
        curl \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Stage 2: Production runtime stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        dumb-init \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user with specific UID for security
RUN groupadd -r -g 1000 appgroup \
    && useradd -r -u 1000 -g appgroup -m -d /app -s /bin/bash appuser

# Set work directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=appuser:appgroup . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/tmp /app/data \
    && chown -R appuser:appgroup /app \
    && chmod -R 755 /app \
    && chmod 750 /app/logs /app/tmp /app/data

# Switch to non-root user
USER appuser

# Add labels for metadata
LABEL maintainer="CrewAI Backend Team" \
      version="1.0.0" \
      description="Production CrewAI Backend with comprehensive monitoring" \
      org.opencontainers.image.source="https://github.com/your-org/crewai-backend" \
      org.opencontainers.image.title="CrewAI Backend" \
      org.opencontainers.image.description="Production-ready CrewAI backend with monitoring"

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/readiness || exit 1

# Expose port
EXPOSE 8000

# Set default command with dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--access-log"]

# Stage 3: Development stage (for local development)
FROM production as development

# Switch back to root for development dependencies
USER root

# Install development tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        vim \
        htop \
        postgresql-client \
        redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN /opt/venv/bin/pip install --no-cache-dir \
        pytest-xdist \
        pytest-cov \
        black \
        isort \
        mypy \
        pre-commit

# Switch back to appuser
USER appuser

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 4: Testing stage
FROM builder as testing

ENV TESTING=1

# Copy test files
COPY tests/ ./tests/
COPY pytest.ini ./

# Run tests
RUN python -m pytest tests/ -v --cov=app --cov-report=xml --cov-report=term-missing

# Default target is production
FROM production 