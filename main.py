from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image
import io
import requests
import os
import tempfile

app = FastAPI(title="KYC Face Verification API")

COMPFACE_URL = os.getenv("COMPFACE_URL", "http://localhost:8000")
# 初始化 PaddleOCR（支持多语言，根据证件调整 lang='en' / 'ch' 等）
ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)  # GPU=True 如果有 GPU


@app.post("/kyc/verify")
async def verify_kyc(
    selfie: UploadFile = File(..., description="自拍照片"),
    id_photo: UploadFile = File(..., description="证件照片"),
):
    # 读取图像
    selfie_bytes = await selfie.read()
    id_bytes = await id_photo.read()

    selfie_np = cv2.imdecode(np.frombuffer(selfie_bytes, np.uint8), cv2.IMREAD_COLOR)
    id_np = cv2.imdecode(np.frombuffer(id_bytes, np.uint8), cv2.IMREAD_COLOR)

    if selfie_np is None or id_np is None:
        raise HTTPException(status_code=400, detail="无效图像文件")

    # PaddleOCR 提取证件信息（可选）
    try:
        ocr_result = ocr.ocr(id_np, cls=True)
        extracted_text = (
            [line[1][0] for line in ocr_result[0]]
            if ocr_result and ocr_result[0]
            else []
        )
    except Exception:
        extracted_text = ["OCR 处理失败"]

    # CompreFace 人脸验证
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f_selfie:
            f_selfie.write(selfie_bytes)
            selfie_path = f_selfie.name
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f_id:
            f_id.write(id_bytes)
            id_path = f_id.name

        # 注意：CompreFace 需要先在 UI[](http://localhost:8000) 创建 Application 和 Face Collection / Subject
        # 这里演示使用 verification 或 recognition endpoint（根据实际调整）
        # 推荐：先通过 UI 添加参考人脸，然后使用 recognition

        # 示例：使用 face verification（检查官方 docs 调整 endpoint）
        verify_url = f"{COMPFACE_URL}/api/v1/verification"  # 或 /recognition 等，参考 CompreFace Postman

        # 实际调用需根据 CompreFace API 调整（可能需要先 add subject）
        files = [
            ("file", ("selfie.jpg", open(selfie_path, "rb"), "image/jpeg")),
            ("file", ("id.jpg", open(id_path, "rb"), "image/jpeg")),
        ]

        # 简化示例：实际推荐分开调用 detect + compare 或使用 recognition service
        response = requests.post(verify_url, files=files[:1])  # 调整为正确调用

        os.unlink(selfie_path)
        os.unlink(id_path)

        if response.status_code == 200:
            result = response.json()
            # 根据实际响应结构提取 similarity
            similarity = (
                result.get("result", [{}])[0]
                .get("subjects", [{}])[0]
                .get("similarity", 0)
                if "result" in result
                else 0
            )
            is_match = similarity > 0.55  # 推荐阈值 0.5~0.7，根据模型调优
            return JSONResponse(
                {
                    "status": "success",
                    "is_same_person": is_match,
                    "similarity_score": float(similarity),
                    "ocr_extracted": extracted_text[:10],  # 前10个文本示例
                    "message": "人脸比对完成",
                }
            )
        else:
            raise HTTPException(
                status_code=500, detail=f"CompreFace 错误: {response.text}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "healthy", "compreface": COMPFACE_URL}
