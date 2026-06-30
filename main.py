#!/usr/bin/env python3
"""
KYC 人脸核身 API
FastAPI + DeepFace + PaddleOCR
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from deepface import DeepFace
from paddleocr import PaddleOCR

app = FastAPI(
    title="KYC 人脸核身验证 API",
    description="上传自拍 + 证件照，判断是否为同一个人",
    version="1.0.0"
)

print("正在初始化 PaddleOCR 模型...")

# 注意：新版 paddleocr 已移除 show_log 参数
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='ch'
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
    allowed = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if selfie.content_type not in allowed or id_card.content_type not in allowed:
        raise HTTPException(status_code=400, detail="只支持 jpg/png/webp 格式图片")

    with tempfile.TemporaryDirectory() as tmp:
        selfie_path = os.path.join(tmp, "selfie.jpg")
        id_path = os.path.join(tmp, "id_card.jpg")

        with open(selfie_path, "wb") as f:
            shutil.copyfileobj(selfie.file, f)
        with open(id_path, "wb") as f:
            shutil.copyfileobj(id_card.file, f)

        # OCR 提取文字
        id_text = ""
        try:
            result = ocr.ocr(id_path, cls=True)
            texts = []
            if result:
                for page in result:
                    if page:
                        for line in page:
                            if line and len(line) > 1 and line[1]:
                                texts.append(line[1][0])
            id_text = " ".join(texts)[:300]
        except Exception as e:
            id_text = f"OCR失败: {str(e)}"

        # 人脸比对
        try:
            res = DeepFace.verify(
                img1_path=selfie_path,
                img2_path=id_path,
                model_name="Facenet",
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=True
            )

            verified = bool(res.get("verified", False))
            distance = float(res.get("distance", 1.0))
            threshold = float(res.get("threshold", 0.4))
            confidence = max(0.0, min(1.0, 1.0 - (distance / max(threshold, 0.01))))

            return JSONResponse({
                "success": True,
                "verified": verified,
                "is_same_person": verified,
                "confidence": round(confidence, 4),
                "distance": round(distance, 4),
                "id_card_text": id_text,
                "message": "✅ 同一个人" if verified else "❌ 非同一个人"
            })

        except ValueError as ve:
            if "Face could not be detected" in str(ve):
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "message": "未检测到清晰人脸，请上传正脸清晰照片"
                })
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
