from fastapi import FastAPI

app = FastAPI(title="AI Invoice Accounting - AI Service")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# TODO: endpoint /ocr — nhận ảnh hóa đơn, trả về text thô
# TODO: endpoint /extract — nhận text thô, trả JSON có cấu trúc + confidence score
