from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import os, shutil, tempfile

app = FastAPI(title="KYC 人脸核身 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ocr = None

def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        print("首次请求，初始化 PaddleOCR 模型中...")
        _ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        print("PaddleOCR 初始化完成")
    return _ocr

@app.post("/verify-kyc")
async def verify_kyc(selfie: UploadFile = File(...), id_card: UploadFile = File(...)):
    allowed = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if selfie.content_type not in allowed or id_card.content_type not in allowed:
        raise HTTPException(status_code=400, detail="只支持 jpg/png/webp")

    with tempfile.TemporaryDirectory() as tmp:
        sp = os.path.join(tmp, "selfie.jpg")
        ip = os.path.join(tmp, "id_card.jpg")
        with open(sp, "wb") as f: shutil.copyfileobj(selfie.file, f)
        with open(ip, "wb") as f: shutil.copyfileobj(id_card.file, f)

        ocr = get_ocr()
        id_text = ""
        try:
            res = ocr.ocr(ip, cls=True)
            texts = []
            if res:
                for page in res:
                    if page:
                        for line in page:
                            if line and len(line) > 1 and line[1]:
                                texts.append(line[1][0])
            id_text = " ".join(texts)[:300]
        except Exception as e:
            id_text = f"OCR失败: {str(e)}"

        try:
            r = DeepFace.verify(sp, ip, model_name="Facenet", detector_backend="opencv", distance_metric="cosine", enforce_detection=True)
            verified = bool(r.get("verified", False))
            dist = float(r.get("distance", 1.0))
            th = float(r.get("threshold", 0.4))
            conf = max(0.0, min(1.0, 1.0 - (dist / max(th, 0.01))))

            return JSONResponse({
                "success": True,
                "verified": verified,
                "is_same_person": verified,
                "confidence": round(conf, 4),
                "distance": round(dist, 4),
                "id_card_text": id_text,
                "message": "✅ 同一个人" if verified else "❌ 非同一个人"
            })
        except Exception as e:
            return JSONResponse(status_code=400, content={"success": False, "message": str(e)})

@app.get("/")
async def root():
    return {"message": "KYC API 运行中", "docs": "/docs"}
