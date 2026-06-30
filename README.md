# KYC 人脸核身验证 API（最简单 Docker 部署版）

使用 **FastAPI + DeepFace + PaddleOCR** 实现：
- 上传「自拍照片」 + 「证件照片」（身份证/驾照/护照等）
- AI 自动判断是否为**同一个人**
- 同时提取证件上的文字信息（姓名、身份证号等）
- 通过 API 返回 JSON 结果（verified + confidence + 提取文字）
- **Docker 一键部署**，Ubuntu 环境最简单方式

## 项目结构（最简）
```
kyc-api/
├── Dockerfile          # Docker 镜像定义（已预下载模型）
├── requirements.txt    # Python 依赖
├── main.py             # FastAPI 主程序（核心逻辑）
└── README.md
```

## 快速开始（Ubuntu + Docker）

### 1. 准备环境（Ubuntu）
```bash
# 更新系统
sudo apt update && sudo apt install -y docker.io docker-compose

# 启动 docker
sudo systemctl start docker
sudo usermod -aG docker $USER   # 退出终端重新登录使生效，或用 sudo
```

### 2. 构建并运行（最简单方式）

```bash
# 进入项目目录
cd kyc-api

# 构建镜像（首次会下载模型，耗时 5-15 分钟，取决于网速）
docker build -t kyc-api:latest .

# 运行容器（后台运行）
docker run -d --name kyc-api \
  -p 8000:8000 \
  --restart unless-stopped \
  kyc-api:latest

# 查看日志
docker logs -f kyc-api
```

### 3. 测试 API

浏览器打开：http://localhost:8000/docs  （Swagger UI 交互测试）

或用 curl 测试：

```bash
# 准备两张测试图片（自拍 + 证件照）
# 假设当前目录有 selfie.jpg 和 id_card.jpg

curl -X POST "http://localhost:8000/verify-kyc" \
  -F "selfie=@selfie.jpg" \
  -F "id_card=@id_card.jpg"
```

**返回示例（同一个人）：**
```json
{
  "success": true,
  "verified": true,
  "is_same_person": true,
  "confidence": 0.9234,
  "distance": 0.28,
  "threshold": 0.4,
  "model_used": "Facenet + opencv",
  "id_card_text": "姓名 张三 公民身份证号码 110101199001011234 ...",
  "message": "✅ 同一个人"
}
```

**返回示例（非同一个人或检测失败）：**
```json
{
  "success": false,
  "verified": false,
  "is_same_person": false,
  "error": "人脸检测失败",
  "message": "自拍或证件照中未检测到清晰人脸，请上传正脸清晰照片..."
}
```

## API 接口说明

| 方法 | 路径          | 说明                          | 参数                  |
|------|---------------|-------------------------------|-----------------------|
| POST | /verify-kyc   | 核心核身接口                  | selfie, id_card (文件) |
| GET  | /health       | 健康检查                      | -                     |
| GET  | /docs         | Swagger 在线文档              | -                     |

**参数说明**：
- `selfie`: 自拍照片（建议正脸、清晰、光线好）
- `id_card`: 证件照片（必须包含清晰的人脸小照片）

**注意事项（最重要）**：
- 证件照上的人脸照片要清晰可见（很多身份证复印件或手机拍摄模糊会导致失败）
- 自拍尽量正面、无墨镜、无口罩
- 首次请求如果模型未预热可能稍慢（已预下载）
- CPU 推理，图片处理约 1-3 秒（取决于图片大小）

## 进阶（可选）

### 使用 docker-compose（推荐生产）
创建 `docker-compose.yml`：
```yaml
version: "3.8"
services:
  kyc-api:
    build: .
    container_name: kyc-api
    ports:
      - "8000:8000"
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
```

然后：
```bash
docker compose up -d --build
```

### 修改模型（进阶）
在 `main.py` 第 88 行可更换：
- `model_name="ArcFace"` 或 `"Facenet512"` （更准但稍慢）
- `detector_backend="retinaface"` （更精准检测小脸，但需额外下载模型）

## 常见问题

1. **构建失败 / 内存不足**：Docker build 需要至少 4-8GB 内存，建议关闭其他程序。
2. **人脸检测失败**：换用更清晰的照片，或把 `enforce_detection=False`（不推荐，会降低安全性）。
3. **想支持 GPU**：换用 nvidia/cuda base image + paddlepaddle-gpu + deepface（较复杂，本项目为最简单 CPU 版）。
4. **生产建议**：加 Nginx 反向代理 + HTTPS + 限流 + 日志 + 异步任务队列（Celery）处理大量请求。

## 技术栈
- **FastAPI**：高性能异步 API 框架
- **DeepFace**：人脸识别（Facenet 模型 + cosine 距离）
- **PaddleOCR**：中文 OCR（提取身份证姓名/号码）
- **Docker**：一键部署，模型已预打包

---

**最简单的方式已完成**：只需 3 个文件 + 2 条命令即可在 Ubuntu 上跑起来！

有问题欢迎反馈。祝 KYC 项目顺利！🚀