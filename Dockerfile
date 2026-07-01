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

# 只预下载 DeepFace 模型
RUN printf "from deepface import DeepFace\n\
print('>>> Downloading DeepFace Facenet model...')\n\
DeepFace.build_model('Facenet')\n\
print('>>> DeepFace model ready')\n" > /tmp/dl_deepface.py && \
    python /tmp/dl_deepface.py

COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
