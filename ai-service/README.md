# AI Service

Responsible for 3 core functions:
- OCR: read invoice images/PDFs into raw text
- Extraction: parse raw text into structured JSON (vendor, date, amount,
  tax ID...) via an LLM API
- Confidence scoring: return a confidence score for each extracted field

## Tech Stack
- Python 3.11+
- FastAPI — exposes a REST API for the backend to call
- Google Cloud Vision API or Tesseract OCR (offline fallback)
- LLM API (OpenAI/Claude) to parse text → JSON
- Pydantic — validates the output schema

## Environment variables
No local `.env` file — reads the single root `.env` (see `../SETUP.md`).

## Structure

```
ai-service/
├── app/
│   ├── main.py           # FastAPI entrypoint
│   ├── ocr/               # OCR-calling module
│   ├── extraction/        # LLM data-extraction module
│   └── schemas/           # Pydantic models
└── requirements.txt
```
