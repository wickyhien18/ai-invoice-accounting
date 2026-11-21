# Danh cho Hugging Face Spaces (SDK Docker, cong 7860, RAM 16 GB mien phi).
# Chay duoc o noi khac: docker build -t invoice-ai ai-service && docker run -p 7860:7860 --env-file .env invoice-ai
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1 PORT=7860
WORKDIR /app
COPY --chown=user requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
    && pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt
COPY --chown=user . .
RUN mkdir -p /app/.cache && chown -R user:user /app /home/user
USER user
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
