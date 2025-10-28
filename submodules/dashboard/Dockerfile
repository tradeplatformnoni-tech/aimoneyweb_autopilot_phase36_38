FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pm2 psutil
COPY . .
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# PM2 will run both backend and agent
CMD ["pm2-runtime", "ecosystem.config.cjs"]
