# Build tu THU MUC GOC cua repo:  docker build -f backend/Dockerfile -t invoice-backend .
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY database database
COPY data_test data_test
WORKDIR /app/backend
RUN chmod +x start.sh
CMD ["./start.sh"]
