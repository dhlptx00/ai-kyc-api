# 1,安装系统依赖
# sudo apt update && sudo apt upgrade -y
# sudo apt install -y python3 python3-pip python3-venv git curl unzip ffmpeg libsm6 libxext6

# Docker & Docker Compose (可选)
# sudo apt install docker.io docker-compose -y
# sudo usermod -aG docker $USER  # 重新登录生效

# 2,部署CompreFace
# mkdir -p ~/compreface && cd ~/compreface
# wget -q -O CompreFace.zip https://github.com/exadel-inc/CompreFace/releases/latest/download/CompreFace_latest.zip
# unzip CompreFace.zip -d .
# cd CompreFace_*  # 根据实际解压目录调整
# docker-compose up -d
# 访问 http://your-server-ip:8000 登录（默认 admin/admin，立即改密码）
# 在 UI 中创建 Face Verification Service，复制生成的 API Key
