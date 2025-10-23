FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask gunicorn requests plotly pandas numpy pyyaml
ENV PYTHONPATH=/app
EXPOSE 5050
CMD ["gunicorn","-w","2","-b","0.0.0.0:5050","flask_app:app"]
