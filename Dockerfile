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

RUN python -c "
import os
print('>>> 正在预下载 DeepFace Facenet 模型 ...')
from deepface import DeepFace
DeepFace.build_model('Facenet')
print('>>> DeepFace Facenet 模型下载完成！')

print('>>> 正在预下载 PaddleOCR 中文模型 ...')
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
print('>>> PaddleOCR 模型下载完成！')
print('>>> 所有模型准备就绪，镜像构建完成。')
"

COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]