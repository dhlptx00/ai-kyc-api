# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Install system dependencies for OpenCV, PaddleOCR, PaddlePaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Use Tsinghua mirror for faster download in China (optional, remove if not needed)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Pre-download PaddleOCR models during build (saves time on first container start)
# This will download ~1GB+ models for Chinese
ENV OCR_LANG=ch
RUN python -c "
import os
os.environ['PADDLEOCR_LOG_LEVEL'] = 'ERROR'
from paddleocr import PaddleOCR
print('Downloading PaddleOCR models for lang=ch ...')
ocr = PaddleOCR(use_angle_cls=True, lang=os.getenv('OCR_LANG', 'ch'), show_log=False, use_gpu=False)
print('PaddleOCR models ready!')
" 

# Copy application code
COPY app/ ./app/
COPY .env.example .env.example

# Expose port
EXPOSE 8080

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]