# KYC 人脸核身 API - Docker 镜像（修正版）
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========== 关键修复：分两次执行，彻底解决多行解析问题 ==========
# 预下载 DeepFace 模型
RUN python -c "
from deepface import DeepFace
print('>>> 正在下载 DeepFace Facenet 模型...')
DeepFace.build_model('Facenet')
print('>>> DeepFace Facenet 模型下载完成！')
"

# 预下载 PaddleOCR 中文模型
RUN python -c "
from paddleocr import PaddleOCR
print('>>> 正在下载 PaddleOCR 中文模型...')
ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
print('>>> PaddleOCR 模型下载完成！')
print('>>> 所有模型已准备就绪')
"

# 复制应用代码
COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]