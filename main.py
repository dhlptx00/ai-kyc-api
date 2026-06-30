#!/usr/bin/env python3
"""
KYC 人脸核身 API
使用 FastAPI + DeepFace + PaddleOCR
上传自拍照片 + 证件照，判断是否为同一个人
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
    description="上传自拍图片(selfie)和证件图片(id_card)，AI自动判断是否为同一个人，并提取证件文字信息",
    version="1.0.0"
)

# 全局初始化 OCR（只加载一次模型，节省时间）
# lang='ch' 支持中文身份证
print("正在初始化 PaddleOCR 模型（首次会自动下载模型，请耐心等待）...")
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='ch',
    use_gpu=False,          # CPU 模式，最简单部署
    show_log=False
)
print("PaddleOCR 初始化完成！")

@app.get("/")
async def root():
    return {
        "message": "KYC 人脸核身 API 已启动",
        "docs": "/docs",
        "endpoint": "POST /verify-kyc"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/verify-kyc")
async def verify_kyc(
    selfie: UploadFile = File(..., description="自拍照片（清晰正脸）"),
    id_card: UploadFile = File(..., description="证件照片（包含人脸照片的身份证/护照等）")
):
    """
    KYC 核心接口：
    1. 使用 DeepFace 进行人脸比对（判断自拍与证件照是否同一个人）
    2. 使用 PaddleOCR 提取证件上的文字信息（姓名、身份证号等）
    3. 返回验证结果 + 置信度 + 提取的文字
    """
    # 支持的图片格式检查
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if selfie.content_type not in allowed_types or id_card.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 jpg/png/webp 格式图片")

    # 使用临时目录，请求结束后自动清理
    with tempfile.TemporaryDirectory() as tmp_dir:
        selfie_path = os.path.join(tmp_dir, "selfie.jpg")
        id_path = os.path.join(tmp_dir, "id_card.jpg")

        # 保存上传文件
        try:
            with open(selfie_path, "wb") as f:
                shutil.copyfileobj(selfie.file, f)
            with open(id_path, "wb") as f:
                shutil.copyfileobj(id_card.file, f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存图片失败: {str(e)}")

        # ========== 1. OCR 提取证件文字 ==========
        id_text = ""
        try:
            ocr_result = ocr.ocr(id_path, cls=True)
            texts = []
            if ocr_result:
                for page in ocr_result:
                    if page:
                        for line in page:
                            if line and len(line) > 1 and line[1]:
                                text = line[1][0]
                                if text and len(text) > 1:
                                    texts.append(text)
            id_text = " ".join(texts)[:300]  # 限制长度
        except Exception as e:
            id_text = f"OCR提取失败: {str(e)}"

        # ========== 2. DeepFace 人脸比对 ==========
        try:
            # 使用 Facenet 模型（在KYC场景中表现较好），detector 用 opencv（最轻量）
            result = DeepFace.verify(
                img1_path=selfie_path,
                img2_path=id_path,
                model_name="Facenet",           # 可选: VGG-Face, Facenet512, ArcFace 等
                detector_backend="opencv",      # 最简单快速，也可用 retinaface（更准但慢）
                distance_metric="cosine",
                enforce_detection=True,         # 必须检测到人脸，否则报错
                align=True
            )

            verified = bool(result.get("verified", False))
            distance = float(result.get("distance", 1.0))
            threshold = float(result.get("threshold", 0.4))

            # 简单置信度计算（距离越小越相似）
            confidence = max(0.0, min(1.0, 1.0 - (distance / max(threshold, 0.01))))

            return JSONResponse(content={
                "success": True,
                "verified": verified,
                "is_same_person": verified,
                "confidence": round(confidence, 4),
                "distance": round(distance, 4),
                "threshold": round(threshold, 4),
                "model_used": "Facenet + opencv",
                "id_card_text": id_text,
                "message": "✅ 同一个人" if verified else "❌ 非同一个人或照片质量不佳"
            })

        except ValueError as ve:
            # 人脸检测失败常见错误
            error_msg = str(ve)
            if "Face could not be detected" in error_msg or "no face" in error_msg.lower():
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "verified": False,
                        "is_same_person": False,
                        "error": "人脸检测失败",
                        "message": "自拍或证件照中未检测到清晰人脸，请上传正脸清晰照片（避免侧脸、遮挡、模糊、低光）",
                        "id_card_text": id_text
                    }
                )
            else:
                raise HTTPException(status_code=400, detail=f"人脸比对失败: {error_msg}")

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "message": "服务器处理异常，请检查图片或稍后重试"
                }
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)