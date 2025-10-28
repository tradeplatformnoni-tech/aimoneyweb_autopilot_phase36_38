FROM python:3.12-slim
WORKDIR /app
COPY ai/observer/autoheal_observer.py /app/autoheal_observer.py
RUN pip install --no-cache-dir requests docker pyyaml kubernetes
CMD ["python","autoheal_observer.py"]
