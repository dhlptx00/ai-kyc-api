## 快速开始（Ubuntu + Docker）

### 1. 准备环境（Ubuntu）
```bash
sudo apt update && sudo apt install -y docker.io docker-compose

sudo systemctl start docker
sudo usermod -aG docker $USER   # 退出终端重新登录使生效

```

### 2. 构建并运行

```bash
cd kyc-api

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

## 常见问题
1. **构建失败 / 内存不足**：Docker build 需要至少 4-8GB 内存，建议关闭其他程序。
2. **人脸检测失败**：换用更清晰的照片，或把 `enforce_detection=False`（不推荐，会降低安全性）。
3. **想支持 GPU**：换用 nvidia/cuda base image + paddlepaddle-gpu + deepface（较复杂，本项目为最简单 CPU 版）。
4. **生产建议**：加 Nginx 反向代理 + HTTPS + 限流 + 日志 + 异步任务队列（Celery）处理大量请求。