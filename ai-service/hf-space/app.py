"""Diem vao cho Hugging Face Spaces (SDK Gradio): chay thang FastAPI cua ai-service tren cong 7860."""
import os

import uvicorn

from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
