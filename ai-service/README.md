# AI Service

Chịu trách nhiệm 3 nghiệp vụ cốt lõi:
- OCR: đọc ảnh/PDF hóa đơn thành văn bản thô
- Trích xuất dữ liệu: parse văn bản thô thành JSON có cấu trúc (nhà cung cấp, ngày,
  số tiền, MST...) qua LLM API
- Confidence score: trả về độ tin cậy cho từng trường dữ liệu

## Công nghệ dự kiến
- Python 3.11+
- FastAPI — expose REST API cho backend gọi vào
- Google Cloud Vision API hoặc Tesseract OCR (offline fallback)
- LLM API (OpenAI/Claude) để parse text → JSON
- Pydantic — validate schema đầu ra

## Cấu trúc dự kiến

```
ai-service/
├── app/
│   ├── main.py           # FastAPI entrypoint
│   ├── ocr/               # module gọi OCR
│   ├── extraction/        # module gọi LLM parse dữ liệu
│   └── schemas/           # Pydantic models
├── requirements.txt
└── .env.example
