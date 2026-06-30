# KYC 人脸核身 API - 最终修复版
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 DeepFace 模型
RUN printf "from deepface import DeepFace\n\
print('>>> Downloading DeepFace Facenet model...')\n\
DeepFace.build_model('Facenet')\n\
print('>>> DeepFace model ready')\n" > /tmp/dl_deepface.py && \
    python /tmp/dl_deepface.py

# 预下载 PaddleOCR 模型
RUN printf "from paddleocr import PaddleOCR\n\
print('>>> Downloading PaddleOCR Chinese model...')\n\
ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)\n\
print('>>> PaddleOCR model ready')\n" > /tmp/dl_paddleocr.py && \
    python /tmp/dl_paddleocr.py

COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
