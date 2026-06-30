# KYC 自拍 + 证件照 人脸比对 + OCR 服务

使用 **FastAPI + PaddleOCR + CompreFace + OpenCV** 实现的简洁 KYC 图片识别方案。

**功能**：
- 通过 API 上传自拍图片 + 证件图片
- PaddleOCR 自动提取证件上的文字信息（姓名、身份证号等）
- CompreFace AI 人脸比对，判断自拍与证件照是否为同一个人
- 返回相似度分数 + 是否匹配 + OCR 结果
- Docker 一键部署（Ubuntu 推荐）

---

## 1. 最简单部署方式（推荐）

### 前置条件
- Ubuntu 服务器（或本地）
- 已安装 Docker + Docker Compose
- 至少 8GB+ RAM（PaddleOCR + CompreFace 模型较大）
- 推荐：有公网 IP 或内网可访问的服务器

### 步骤 1: 部署 CompreFace（人脸识别服务）

CompreFace 是独立的服务，我们先部署它。

```bash
# 1. 下载最新版 CompreFace
wget https://github.com/exadel-inc/CompreFace/releases/latest/download/CompreFace-latest.zip
unzip CompreFace-latest.zip
cd CompreFace

# 2. 启动（首次会下载大镜像，耐心等待）
docker compose up -d

# 3. 查看日志确认启动成功
docker compose logs -f
```

启动成功后访问：
- **UI 地址**: `http://你的服务器IP:8000`
- 默认端口 8000

**重要操作**（必须做）：
1. 打开 UI，注册/登录账号
2. 创建一个 **Application**（应用）
3. 在该应用下添加 **Service** → 选择 **Face Verification**（人脸验证）
4. 创建后，复制生成的 **API Key**（x-api-key），后面要用！

---

### 步骤 2: 部署本 KYC 服务

```bash
# 克隆或下载本项目代码到服务器
git clone <你的仓库> kyc-verifier
cd kyc-verifier

# 或者直接把整个文件夹 scp 上传到服务器

# 复制环境变量文件
cp .env.example .env

# 编辑 .env，填入从 CompreFace UI 复制的 API Key
nano .env
# 把 COMPREFACE_API_KEY= 后面的值改成你复制的 key
```

启动服务：

```bash
# 构建并启动（首次构建会下载 PaddleOCR 模型，比较慢）
docker compose up --build -d

# 查看日志
docker compose logs -f kyc-verifier
```

服务启动后访问：
- **API 文档 (Swagger)**: `http://你的服务器IP:8080/docs`
- **健康检查**: `http://你的服务器IP:8080/health`

---

## 2. 使用 API

### 接口地址
`POST http://你的服务器IP:8080/api/v1/kyc/verify`

### 请求参数（form-data）

| 参数       | 类型     | 必填 | 说明                              |
|------------|----------|------|-----------------------------------|
| selfie     | file     | 是   | 自拍图片（jpg/png）               |
| id_card    | file     | 是   | 证件照片（身份证正面等）          |
| threshold  | float    | 否   | 相似度阈值，默认 0.78（0.75~0.85 推荐） |
| return_raw | boolean  | 否   | 是否返回 CompreFace 原始结果（调试用） |

### 返回示例（匹配成功）

```json
{
  "success": true,
  "is_same_person": true,
  "face_similarity": 0.9123,
  "threshold": 0.78,
  "face_verification_message": "人脸匹配成功",
  "id_card_ocr": {
    "raw_texts": [
      {"text": "姓名", "confidence": 0.998},
      {"text": "张三", "confidence": 0.995},
      {"text": "公民身份证号码", "confidence": 0.99},
      {"text": "110101199001011234", "confidence": 0.97}
    ],
    "extracted_info": {
      "name": "张三",
      "id_number": "110101199001011234"
    },
    "full_text_sample": "姓名 张三 公民身份证号码 110101199001011234 ..."
  },
  "note": "本结果为AI辅助判断..."
}
```

### 返回示例（不匹配）

```json
{
  "success": true,
  "is_same_person": false,
  "face_similarity": 0.6234,
  "threshold": 0.78,
  "face_verification_message": "人脸不匹配（相似度 62.34% < 阈值 78%）",
  ...
}
```

---

## 3. 常见问题 & 注意事项

1. **CompreFace API Key 错误** → 401 Unauthorized
   - 确认在 CompreFace UI 里创建的是 **Face Verification** 服务
   - Key 复制完整，没有多余空格

2. **首次启动很慢**
   - CompreFace + PaddleOCR 模型下载 + 加载需要 5-15 分钟（取决于网络）
   - 建议后台运行 `docker compose up -d`

3. **人脸检测失败**
   - 自拍或证件照光线太暗、角度太大、遮挡
   - 建议用户上传清晰、正脸、无遮挡的图片
   - 可适当降低 `threshold` 到 0.7 测试

4. **OCR 提取不准**
   - 当前使用简单正则提取，适合标准中国身份证
   - 护照、港澳台证件、外国证件效果可能一般
   - 生产环境可后续接入更专业的身份证 OCR 模型

5. **性能优化建议**
   - 生产部署推荐使用 **GPU** 版本（CompreFace 支持 GPU 模型，PaddleOCR 改用 paddlepaddle-gpu）
   - 当前为 CPU 模式，适合测试/低并发
   - 可增加 `network_mode: host` 已开启（Linux）

6. **安全建议**
   - 生产环境务必加 **API 鉴权**（JWT / API Key）
   - 图片上传后及时删除或加密存储
   - 强烈建议增加 **活体检测 (Liveness Detection)** 防止照片/视频攻击

---

## 4. 项目结构（最简版）

```
kyc-verifier/
├── Dockerfile              # 包含 PaddleOCR 模型预下载
├── docker-compose.yml      # 一键启动（使用 host 网络连接 CompreFace）
├── .env.example
├── requirements.txt
├── README.md
└── app/
    └── main.py             # FastAPI 主程序 + 全部逻辑
```

---

## 5. 扩展建议（进阶）

- 增加用户会话管理 + 结果持久化（PostgreSQL）
- 接入活体检测（可再加一个 CompreFace mask/pose 插件或独立 liveness 服务）
- 前端上传页面（React / Vue + 图片预览 + 压缩）
- 多语言支持（修改 OCR_LANG=en 并重启）
- Kubernetes 部署 + 自动扩缩容
- 日志 + 监控（Prometheus + Grafana）

---

**本方案已尽量简化**，核心代码全部放在一个 `main.py` 里，方便理解和修改。

有问题欢迎提 Issue 或联系作者。

祝 KYC 项目部署顺利！🚀