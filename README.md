# 测试用ubuntu容器模拟ubuntu部署流程
# docker run -d --name ubuntu-server -p 8000:8000 ubuntu tail -f /dev/null

# 1，安装 Docker & Docker Compose
# sudo apt update && sudo apt install docker.io docker-compose-v2 -y
# sudo usermod -aG docker $USER  # 重启终端

# 2，启动服务
# docker-compose up -d --build

# 3，访问
# CompreFace 管理界面：http://IP:8000（默认 admin / admin，创建 Application → Face Collection → 添加参考证件人脸）
# FastAPI API：http://IP:8001/docs
# Health: http://IP:8001/health
