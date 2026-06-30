#!/usr/bin/env python3
"""
KYC 自拍 + 证件照 人脸比对 + OCR 服务
使用 FastAPI + PaddleOCR + CompreFace + OpenCV

部署方式：Docker (最简单)
"""

import os
import re
import base64
import logging
from io import BytesIO
from typing import Optional

import cv2
import numpy as np
import requests
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR
from PIL import Image

# ==================== 配置 ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMPREFACE_URL = os.getenv("COMPREFACE_URL", "http://localhost:8000").rstrip("/")
COMPREFACE_API_KEY = os.getenv("COMPREFACE_API_KEY", "")
OCR_LANG = os.getenv("OCR_LANG", "ch")
VERIFY_ENDPOINT = f"{COMPREFACE_URL}/api/v1/verification/verify"

# 全局初始化 PaddleOCR（启动时加载模型，节省请求时间）
logger.info(f"正在初始化 PaddleOCR (lang={OCR_LANG}) ...")
ocr = PaddleOCR(
    use_angle_cls=True,
    lang=OCR_LANG,
    show_log=False,
    use_gpu=False,          # CPU 模式，最简单部署。如有 GPU 可改为 True 并安装 paddlepaddle-gpu
    enable_mkldnn=False     # CPU 加速，可根据需要开启
)
logger.info("PaddleOCR 初始化完成！")

app = FastAPI(
    title="KYC 人脸比对 + OCR API",
    description="上传自拍和证件照，自动OCR提取证件信息 + CompreFace 人脸比对，判断是否同一个人。Docker 一键部署。",
    version="1.0.0"
)

# ==================== 工具函数 ====================
def preprocess_image(image_bytes: bytes, max_dim: int = 1200) -> bytes:
    """
    使用 OpenCV 预处理图片：
    - 解码
    - 限制最大尺寸（减小体积，加快 CompreFace 处理）
    - 统一转成高质量 JPG
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("图片解码失败，返回原始数据")
            return image_bytes

        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 转 JPG 减小体积
        encode_param = [cv2.IMWRITE_JPEG_QUALITY, 88]
        success, encoded = cv2.imencode('.jpg', img, encode_param)
        if success:
            return encoded.tobytes()
        return image_bytes
    except Exception as e:
        logger.error(f"预处理图片异常: {e}")
        return image_bytes


def extract_id_info(texts: list) -> dict:
    """
    从 OCR 结果中简单提取常见证件字段（中文身份证为主）
    生产环境建议使用更专业的结构化提取或微调模型
    """
    extracted = {}
    full_text = " ".join([t.get("text", "") for t in texts])

    # 姓名（常见格式：姓名：张三 或 姓名 张三）
    name_patterns = [
        r'姓名[：:\s]*([^\s，,。\d]{2,5})',
        r'Name[：:\s]*([A-Za-z\u4e00-\u9fa5\s]{2,10})'
    ]
    for pattern in name_patterns:
        match = re.search(pattern, full_text)
        if match:
            extracted["name"] = match.group(1).strip()
            break

    # 身份证号（18位，最后一位可能是X）
    id_pattern = r'([1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx])'
    id_match = re.search(id_pattern, full_text)
    if id_match:
        extracted["id_number"] = id_match.group(1).upper()

    # 可扩展：出生日期、地址、签发机关等
    # birth_match = re.search(r'出生[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)', full_text)
    # if birth_match: extracted["birth_date"] = birth_match.group(1)

    return extracted


def ocr_id_card(image_bytes: bytes) -> dict:
    """对证件照进行 OCR 文字识别"""
    try:
        processed = preprocess_image(image_bytes)
        nparr = np.frombuffer(processed, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "证件图片解码失败", "raw_texts": [], "extracted_info": {}}

        # PaddleOCR 推理
        result = ocr.ocr(img, cls=True)

        texts = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2 and line[1]:
                    text = line[1][0]
                    conf = float(line[1][1])
                    texts.append({"text": text, "confidence": round(conf, 4)})

        extracted = extract_id_info(texts)
        return {
            "raw_texts": texts,
            "extracted_info": extracted,
            "full_text_sample": " ".join([t["text"] for t in texts])[:300]
        }
    except Exception as e:
        logger.error(f"OCR 处理失败: {e}")
        return {"error": str(e), "raw_texts": [], "extracted_info": {}}


def verify_face_with_compreface(selfie_bytes: bytes, id_card_bytes: bytes, threshold: float = 0.75) -> dict:
    """
    调用 CompreFace Face Verification API 进行 1:1 人脸比对
    需要先在 CompreFace UI 创建 Face Verification 服务并获取 x-api-key
    """
    if not COMPREFACE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="CompreFace API Key 未配置。请在 .env 或环境变量中设置 COMPREFACE_API_KEY"
        )

    # 预处理图片（减小体积 + 统一格式）
    selfie_proc = preprocess_image(selfie_bytes)
    id_proc = preprocess_image(id_card_bytes)

    # 使用 Base64 JSON 方式调用（文档推荐）
    source_b64 = base64.b64encode(selfie_proc).decode("utf-8")
    target_b64 = base64.b64encode(id_proc).decode("utf-8")

    headers = {
        "x-api-key": COMPREFACE_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "source_image": source_b64,
        "target_image": target_b64
    }

    try:
        resp = requests.post(
            VERIFY_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=90  # CompreFace 推理可能较慢
        )
        resp.raise_for_status()
        data = resp.json()

        result_list = data.get("result", [])
        if not result_list:
            return {
                "match": False,
                "similarity": 0.0,
                "message": "未检测到人脸（自拍或证件照中无人脸）",
                "raw": data
            }

        # 取第一个结果中的最佳匹配相似度
        face_matches = result_list[0].get("face_matches", [])
        if not face_matches:
            return {
                "match": False,
                "similarity": 0.0,
                "message": "证件照中未检测到人脸",
                "raw": data
            }

        similarity = float(face_matches[0].get("similarity", 0.0))
        match = similarity >= threshold

        return {
            "match": match,
            "similarity": round(similarity, 4),
            "message": "人脸匹配成功" if match else f"人脸不匹配（相似度 {similarity:.2%} < 阈值 {threshold:.0%}）",
            "raw": data   # 调试用，生产可删除或只保留关键字段
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="CompreFace 请求超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        logger.error(f"CompreFace 调用失败: {e}")
        raise HTTPException(status_code=502, detail=f"CompreFace 服务异常: {str(e)}")
    except Exception as e:
        logger.error(f"人脸比对异常: {e}")
        raise HTTPException(status_code=500, detail=f"人脸比对内部错误: {str(e)}")


# ==================== API 接口 ====================
@app.post("/api/v1/kyc/verify", summary="KYC 自拍 + 证件照 验证", tags=["KYC"])
async def kyc_verify(
    selfie: UploadFile = File(..., description="自拍图片（真人现场拍摄）"),
    id_card: UploadFile = File(..., description="证件照片（身份证/护照等正面照）"),
    threshold: float = Form(0.78, description="人脸相似度阈值（0~1），建议 0.75~0.85， 默认 0.78"),
    return_raw: bool = Form(False, description="是否返回 CompreFace 原始详细结果（调试用）")
):
    """
    **核心接口**：上传两张图片，自动完成：
    1. PaddleOCR 提取证件信息（姓名、身份证号等）
    2. CompreFace 人脸比对（判断自拍与证件照是否为同一个人）
    3. 返回综合结果
    """
    # 基础校验
    if not selfie.content_type or not selfie.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="selfie 必须是图片文件")
    if not id_card.content_type or not id_card.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="id_card 必须是图片文件")

    selfie_bytes = await selfie.read()
    id_card_bytes = await id_card.read()

    if len(selfie_bytes) < 100 or len(id_card_bytes) < 100:
        raise HTTPException(status_code=400, detail="图片文件过小或损坏")

    # OCR 证件
    ocr_result = ocr_id_card(id_card_bytes)

    # 人脸比对
    verify_result = verify_face_with_compreface(selfie_bytes, id_card_bytes, threshold)

    is_same = verify_result.get("match", False)

    response_data = {
        "success": True,
        "is_same_person": is_same,
        "face_similarity": verify_result.get("similarity", 0.0),
        "threshold": threshold,
        "face_verification_message": verify_result.get("message"),
        "id_card_ocr": ocr_result,
        "note": "本结果为AI辅助判断，生产环境请结合人工审核 + 活体检测(liveness) 使用。"
    }

    if return_raw:
        response_data["compreface_raw"] = verify_result.get("raw")

    return JSONResponse(content=response_data)


@app.get("/health", summary="健康检查", tags=["System"])
def health_check():
    """检查服务状态"""
    return {
        "status": "healthy",
        "compreface_url": COMPREFACE_URL,
        "ocr_lang": OCR_LANG,
        "api_key_configured": bool(COMPREFACE_API_KEY),
        "message": "服务正常运行"
    }


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "KYC Verification API is running. Visit /docs for Swagger UI.",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)