import cv2
import numpy as np
from paddleocr import PaddleOCR
from compreface import CompreFace
from compreface.service import VerificationService
from fastapi import UploadFile
import shutil
import os

# 初始化 PaddleOCR（中文支持）
ocr = PaddleOCR(use_angle_cls=True, lang="ch")

def preprocess_image(file: UploadFile, target_size=(640, 640)):
    """OpenCV 预处理"""
    contents = file.file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Resize & 质量检查（简单 blur 检测）
    img = cv2.resize(img, target_size)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    if blur < 100:
        raise ValueError("图片模糊度过高，请重新上传清晰照片")
    
    # 保存临时文件供 SDK 使用
    temp_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    cv2.imwrite(temp_path, img)
    return temp_path, img

def extract_id_info(image_path: str):
    """PaddleOCR 提取证件信息"""
    result = ocr.ocr(image_path, cls=True)
    text_lines = []
    for line in result:
        if line:
            for word in line:
                text_lines.append(word[1][0])
    return "\n".join(text_lines)

def compare_faces(selfie_path: str, id_path: str, api_key: str, compreface_url="http://localhost", port="8000"):
    """CompreFace 人脸比对"""
    compre_face = CompreFace(compreface_url, port)
    verification: VerificationService = compre_face.init_face_verification(api_key)
    
    result = verification.verify(
        source_image_path=selfie_path,   # 自拍（source）
        target_image_path=id_path,       # 证件（target）
        options={"det_prob_threshold": 0.7}
    )
    
    # result 结构示例：包含 similarity 等
    similarity = result.get("result", [{}])[0].get("similarity", 0) if isinstance(result.get("result"), list) else 0
    return {
        "match": similarity > 0.5,   # 阈值可调整（官方推荐 ~0.5）
        "similarity": float(similarity),
        "details": result
    }