# KYC 人脸核身 API - 干净版 Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 DeepFace 模型
RUN python -c "
from deepface import DeepFace
print('>>> Downloading DeepFace Facenet model...')
DeepFace.build_model('Facenet')
print('>>> DeepFace model ready')
"

# 预下载 PaddleOCR 中文模型
RUN python -c "
from paddleocr import PaddleOCR
print('>>> Downloading PaddleOCR Chinese model...')
ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
print('>>> PaddleOCR model ready')
"

COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
