from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import os
import shutil
import tempfile

app = FastAPI(title="KYC 人脸核身 API（RetinaFace版）")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/verify-kyc")
async def verify_kyc(
    selfie: UploadFile = File(...),
    id_card: UploadFile = File(...)
):
    allowed = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if selfie.content_type not in allowed or id_card.content_type not in allowed:
        raise HTTPException(status_code=400, detail="只支持 jpg/png/webp 格式")

    with tempfile.TemporaryDirectory() as tmp:
        selfie_path = os.path.join(tmp, "selfie.jpg")
        id_path = os.path.join(tmp, "id_card.jpg")

        with open(selfie_path, "wb") as f:
            shutil.copyfileobj(selfie.file, f)
        with open(id_path, "wb") as f:
            shutil.copyfileobj(id_card.file, f)

        try:
            result = DeepFace.verify(
                img1_path=selfie_path,
                img2_path=id_path,
                model_name="Facenet",
                detector_backend="retinaface",      # ← 已改成 retinaface
                distance_metric="cosine",
                enforce_detection=True
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
                "message": "✅ 同一个人" if verified else "❌ 非同一个人"
            })

        except ValueError as ve:
            if "Face could not be detected" in str(ve):
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "message": "未检测到清晰人脸，请上传正脸清晰照片"
                })
            return JSONResponse(status_code=400, content={"success": False, "error": str(ve)})

        except Exception as e:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": str(e)
            })


@app.get("/")
async def root():
    return {"message": "KYC 人脸核身 API（RetinaFace版）已启动", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
