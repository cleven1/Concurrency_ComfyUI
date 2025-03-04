#!/bin/bash

# 进入 ComfyUI 目录
cd /root/autodl-fs/ComfyUI || { echo "ComfyUI 目录不存在或无法访问"; exit 1; }

pip install -r requirements.txt || { echo "安装依赖失败"; exit 1; }

# 启动多个 ComfyUI 实例（后台运行）
for i in {2000..2005}
do
    python main.py --port $i &
    echo "ComfyUI 实例已启动，端口: $i"
done

# 等待所有后台任务完成
wait
echo "所有任务已完成"