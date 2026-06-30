#!/usr/bin/env python3
"""
KYC 人脸核身 API
使用 FastAPI + DeepFace + PaddleOCR
"""

import os
import shutil
import tempfile
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from deepface import DeepFace
from paddleocr import PaddleOCR

app = FastAPI(
    title="KYC 人脸核身验证 API",
    description="上传自拍照片 + 证件照片，AI 判断是否为同一个人",
    version="1.0.0"
)

# 全局初始化 OCR（新版 paddleocr 已移除 use_gpu 参数）
print("正在初始化 PaddleOCR 模型...")
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='ch',
    show_log=False
    # 注意：新版 paddleocr 已不需要 use_gpu 参数
)
print("PaddleOCR 初始化完成！")

@app.get("/")
async def root():
    return {"message": "KYC API 已启动", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/verify-kyc")
async def verify_kyc(
    selfie: UploadFile = File(...),
    id_card: UploadFile = File(...)
):
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if selfie.content_type not in allowed_types or id_card.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 jpg/png/webp 格式")

    with tempfile.TemporaryDirectory() as tmp_dir:
        selfie_path = os.path.join(tmp_dir, "selfie.jpg")
        id_path = os.path.join(tmp_dir, "id_card.jpg")

        with open(selfie_path, "wb") as f:
            shutil.copyfileobj(selfie.file, f)
        with open(id_path, "wb") as f:
            shutil.copyfileobj(id_card.file, f)

        # OCR 提取文字
        id_text = ""
        try:
            ocr_result = ocr.ocr(id_path, cls=True)
            texts = []
            if ocr_result:
                for page in ocr_result:
                    if page:
                        for line in page:
                            if line and len(line) > 1 and line[1]:
                                texts.append(line[1][0])
            id_text = " ".join(texts)[:300]
        except Exception as e:
            id_text = f"OCR失败: {str(e)}"

        # DeepFace 人脸比对
        try:
            result = DeepFace.verify(
                img1_path=selfie_path,
                img2_path=id_path,
                model_name="Facenet",
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=True,
                align=True
            )

            verified = bool(result.get("verified", False))
            distance = float(result.get("distance", 1.0))
            threshold = float(result.get("threshold", 0.4))
            confidence = max(0.0, min(1.0, 1.0 - (distance / max(threshold, 0.01))))

            return JSONResponse({
                "success": True,
                "verified": verified,
                "is_same_person": verified,
                "confidence": round(confidence, 4),
                "distance": round(distance, 4),
                "threshold": round(threshold, 4),
                "id_card_text": id_text,
                "message": "✅ 同一个人" if verified else "❌ 非同一个人"
            })

        except ValueError as ve:
            if "Face could not be detected" in str(ve):
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "verified": False,
                    "message": "未检测到清晰人脸，请上传正脸清晰照片"
                })
            raise HTTPException(status_code=400, detail=str(ve))

        except Exception as e:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": str(e)
            })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
