# NeoLight Fly.io Production Dockerfile
# =====================================
# Complete deployment with all dependencies for 24/7 operation
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        git \
        build-essential \
        gcc \
        g++ \
        && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt* ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir \
            fastapi==0.104.1 \
            uvicorn[standard]==0.24.0 \
            pandas==2.1.3 \
            numpy==1.26.2 \
            yfinance==0.2.32 \
            requests==2.31.0 \
            psutil==5.9.6 \
            plotly==5.18.0 \
            starlette==0.27.0 \
            python-dateutil==2.8.2 \
            anyio==4.2.0 \
            click==8.1.7 \
            scikit-learn==1.3.2 \
            scipy==1.11.4 \
            httpx==0.25.2 \
            tenacity==8.2.3 \
            pillow==10.1.0; \
    fi

# Copy application code
COPY agents/ ./agents/
COPY ai/ ./ai/
COPY analytics/ ./analytics/
COPY backend/ ./backend/
COPY dashboard/ ./dashboard/
COPY phases/ ./phases/
COPY trader/ ./trader/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p state runtime logs data snapshots && \
    chmod -R 755 state runtime logs data snapshots

# Copy startup script
COPY scripts/flyio_startup.sh /app/scripts/flyio_startup.sh
RUN chmod +x /app/scripts/flyio_startup.sh

# Create health check script
RUN echo '#!/usr/bin/env python3\n\
from fastapi import FastAPI\n\
from fastapi.responses import PlainTextResponse\n\
import uvicorn\n\
app = FastAPI()\n\
@app.get("/health")\n\
@app.get("/")\n\
def health():\n\
    return PlainTextResponse("OK - NeoLight Cloud Active")\n\
if __name__ == "__main__":\n\
    uvicorn.run(app, host="0.0.0.0", port=8090)\n\
' > /app/health_check.py && chmod +x /app/health_check.py

# Expose ports
EXPOSE 8090 8100 8500

# Start the system
CMD ["/app/scripts/flyio_startup.sh"]
