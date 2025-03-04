# 进入 FastAPI 目录
cd /root/fastapi_comfyUI || { echo "FastAPI 目录不存在或无法访问"; exit 1; }

# 安装依赖（确保使用正确的 pip 版本和虚拟环境）
pip install -r requirements.txt || { echo "依赖安装失败"; exit 1; }

# 启动 FastAPI 服务器（后台运行）
python main.py &
echo "FastAPI 服务器已启动"