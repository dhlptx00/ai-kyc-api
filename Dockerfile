# KYC 人脸核身 API - Docker 镜像
# 基于 Python slim + 系统依赖 + 预下载模型（最简单部署方式）
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（OpenCV + PaddleOCR + DeepFace 必需）
# libgl1, libglib 等用于 cv2 和 paddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 DeepFace 和 PaddleOCR 模型（构建时下载，运行时无需网络）
# 这样首次请求极快，且支持离线部署
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

# 复制应用代码
COPY main.py .

# 暴露端口
EXPOSE 8000

# 启动命令（生产可用 gunicorn + uvicorn workers，但最简单用 uvicorn）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]