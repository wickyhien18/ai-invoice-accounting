import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI

# Root .env is two levels up from this file: ai-service/app/main.py -> project root
ROOT_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

app = FastAPI(title="AI Invoice Accounting - AI Service")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# TODO: /ocr endpoint — receive an invoice image, return raw text
# TODO: /extract endpoint — receive raw text, return structured JSON + confidence score
