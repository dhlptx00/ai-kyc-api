FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

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
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# 预下载 DeepFace + RetinaFace 模型
RUN printf "from deepface import DeepFace\n\
print('>>> Downloading DeepFace Facenet model...')\n\
DeepFace.build_model('Facenet')\n\
print('>>> Downloading RetinaFace model...')\n\
DeepFace.build_model('retinaface')\n\
print('>>> All models ready')\n" > /tmp/dl_models.py && \
    python /tmp/dl_models.py

COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
