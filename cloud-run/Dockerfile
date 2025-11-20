# ╔══════════════════════════════════════════════════════════════════╗
# ║ NeoLight Cloud Run Dockerfile - Hybrid Production Edition       ║
# ║ Combines Claude's security + Auto's efficiency                 ║
# ╚══════════════════════════════════════════════════════════════════╝

FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    gnupg \
    procps \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install gcloud SDK (for gsutil)
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts
ENV PATH="/root/google-cloud-sdk/bin:${PATH}"

# Create non-root user (Claude's security)
RUN useradd -m -u 1000 -s /bin/bash neolight
RUN mkdir -p /app && chown -R neolight:neolight /app

# App directory
WORKDIR /app

# Copy requirements first (Auto's efficiency)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install additional dependencies for Cloud Run
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic

# Copy only necessary files (Auto's selective copy)
COPY trader/ /app/trader/
COPY agents/ /app/agents/
COPY backend/ /app/backend/
COPY analytics/ /app/analytics/
COPY cloud-run/ /app/cloud-run/
COPY scripts/ /app/scripts/

# Create necessary directories
RUN mkdir -p /app/state /app/runtime /app/logs /app/snapshots && \
    chown -R neolight:neolight /app

# Make scripts executable
RUN chmod +x /app/cloud-run/sync-state.sh /app/scripts/*.sh || true

# Switch to non-root user (Claude's security)
USER neolight

# Environment
ENV PORT=8080
ENV PYTHONPATH=/app
ENV TRADING_MODE=PAPER_TRADING_MODE

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start command
CMD ["/bin/bash", "-lc", "/app/cloud-run/sync-state.sh; python -m uvicorn cloud-run.app:app --host 0.0.0.0 --port ${PORT}"]

