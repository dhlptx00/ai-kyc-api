from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import os
from utils import preprocess_image, extract_id_info, compare_faces

app = FastAPI(title="KYC Face + OCR Verification")

# 从环境变量获取 CompreFace API Key
COMPFACE_API_KEY = os.getenv("COMPFACE_API_KEY")
if not COMPFACE_API_KEY:
    raise Exception("请设置环境变量 COMPFACE_API_KEY")

@app.post("/kyc/verify")
async def kyc_verify(
    selfie: UploadFile = File(...),
    id_photo: UploadFile = File(...)
):
    try:
        # 预处理并保存临时文件
        selfie_path, _ = preprocess_image(selfie)
        id_path, _ = preprocess_image(id_photo)
        
        # OCR 提取证件信息
        id_text = extract_id_info(id_path)
        
        # 人脸比对
        face_result = compare_faces(selfie_path, id_path, COMPFACE_API_KEY)
        
        # 清理临时文件
        for p in [selfie_path, id_path]:
            if os.path.exists(p):
                os.remove(p)
        
        return JSONResponse({
            "status": "success",
            "face_match": face_result["match"],
            "similarity_score": face_result["similarity"],
            "face_details": face_result["details"],
            "extracted_id_text": id_text,
            "recommendation": "通过" if face_result["match"] else "人工复核"
        })
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)