#!/bin/bash

# 进入 ComfyUI 目录
cd /root/autodl-fs/ComfyUI || { echo "ComfyUI 目录不存在或无法访问"; exit 1; }

# 启动多个 ComfyUI 实例（后台运行）
for i in {2000..2009}
do
    python main.py --port $i &
    echo "ComfyUI 实例已启动，端口: $i"
done

# 进入 FastAPI 目录
cd /root/autodl-tmp/fastapi_comfyUI || { echo "FastAPI 目录不存在或无法访问"; exit 1; }

# 安装依赖（确保使用正确的 pip 版本和虚拟环境）
pip install -r requirements.txt || { echo "依赖安装失败"; exit 1; }

# 启动 FastAPI 服务器（后台运行）
python main.py &
echo "FastAPI 服务器已启动"

# 等待所有后台任务完成
wait
echo "所有任务已完成"