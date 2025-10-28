FROM python:3.12-slim
WORKDIR /app
COPY ai/agent_core.py /app/agent_core.py
RUN pip install --no-cache-dir requests
CMD ["python","agent_core.py"]
