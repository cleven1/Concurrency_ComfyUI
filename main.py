import asyncio, requests
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx, random
from typing import Dict, Any
from datetime import datetime, timedelta
from utils import find_value, CACHES
from socket_handler import ConnectionManager


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 清理过期数据的协程
async def cleanup_expired_prompt_ids():
    while True:
        now = datetime.now()
        expired_prompt_ids = [
            prompt_id for prompt_id, details in CACHES.items()
            if now - details["timestamp"] > timedelta(minutes=30)
        ]
        for prompt_id in expired_prompt_ids:
            del CACHES[prompt_id]
        await asyncio.sleep(600)  # 每10分钟检查一次

# ComfyUI base URL
COMFYUI_BASE_URLS = ["http://127.0.0.1"]
PORTS_RANGE = range(2000, 2006) # 2000-2005
PORTS = random.choice(PORTS_RANGE) 
COMFYUI_BASE_URL = random.choice(COMFYUI_BASE_URLS) + ":" + str(PORTS)

# Create an async HTTP client
http_client = httpx.AsyncClient(verify=False)  # disable SSL verification since it's using self-signed cert


@app.post("/prompt")
async def proxy_prompt(data: Dict[Any, Any]):
    """
    Proxy the prompt request to ComfyUI
    """
    try:
        url = COMFYUI_BASE_URL
        file_name = find_value(data, 'image')
        if file_name is not None:
            link = CACHES.get(file_name)
            if link is not None:
                url = link.get('link')
        print("url == ", url)
        response = await http_client.post(
            f"{url}/prompt",
            json=data,
            timeout=30.0
        )
        result = response.json()
        print("*" * 20)
        print(result)
        print("*" * 20)
        # 提取 prompt_id 字段
        prompt_id = result.get("prompt_id")
        # 保存连接和时间戳
        CACHES[prompt_id] = {"link": url, "timestamp": datetime.now()}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/view")
async def view(filename: str, type: str):
    retries = 0
    max_retries = 15
    retry_interval = 1  # 重试间隔时间，单位为秒

    while retries < max_retries:
        detail = CACHES.get(filename)
        print("detail == ", detail)

        if detail is None:
            await asyncio.sleep(retry_interval)  # 异步等待
            retries += 1
            continue

        url = detail.get('link')
        if url is None:
            await asyncio.sleep(retry_interval)  # 异步等待
            retries += 1
            continue
        
        retries = max_retries
        try:
            response = requests.get(f"{url}/view?filename={filename}&type={type}")
            print("response == ", response)
            if response.status_code == 200:
                # 返回图片流
                return StreamingResponse(response.iter_content(chunk_size=1024), media_type=response.headers.get("Content-Type"))
            else:
                return response.json()
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            await asyncio.sleep(retry_interval)  # 异步等待
            retries += 1

    raise HTTPException(status_code=404, detail="File not found")
            

@app.get("/history/{prompt_id}")
async def proxy_prompt(prompt_id: str):
    """
    Proxy the prompt request to ComfyUI
    """
    try:
        details = CACHES.get(prompt_id)
        if not details:
            raise HTTPException(status_code=404, detail="Prompt ID not found or expired")
        url = details["link"]
        response = await http_client.get(
            f"{url}/history/{prompt_id}",
            timeout=30.0
        )
        result = response.json()
        file_name = find_value(result, 'filename')
        if file_name is not None:
            CACHES[file_name] = {"link": url, "timestamp": datetime.now()}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/image")
async def proxy_upload_image(image: UploadFile):
    """
    Proxy image upload to ComfyUI
    """
    try:
        file_content = await image.read()
        files = {"image": (image.filename, file_content)}
        url = COMFYUI_BASE_URL
        response = await http_client.post(
            f"{url}/upload/image",
            files=files,
            timeout=30.0
        )
        result = response.json()
        file_name = result.get("name")
        CACHES[file_name] = {"link": url, "timestamp": datetime.now()}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/mask")
async def proxy_upload_mask(image: UploadFile):
    """
    Proxy image upload to ComfyUI
    """
    try:
        files = {"image": (image.filename, await image.read())}
        url = COMFYUI_BASE_URL
        response = await http_client.post(
            f"{url}/upload/mask",
            files=files,
            timeout=30.0
        )
        result = response.json()
        file_name = result.get("name")
        CACHES[file_name] = {"link": url, "timestamp": datetime.now()}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def proxy_websocket(websocket: WebSocket):
    manager = ConnectionManager()
    manager.client_ws = websocket
    
    try:
        await websocket.accept()
        client_id = websocket.query_params.get("clientId")

        if not client_id:
            await websocket.close(code=4000, reason="Missing clientId")
            return

        # 连接到所有目标端口
        connected = await manager.connect_to_all_ports(
            COMFYUI_BASE_URLS,
            PORTS_RANGE,
            client_id
        )

        if not connected:
            print("❌ 所有连接尝试均失败")
            await websocket.close(code=1011, reason="All connection attempts failed")
            return

        # 创建客户端消息接收任务
        client_receive_task = asyncio.create_task(manager._handle_client_messages())

        # 等待所有任务完成
        await asyncio.gather(
            client_receive_task,
            *manager.tasks,
            return_exceptions=True
        )

    except Exception as e:
        print(f"WebSocket 处理异常: {str(e)}")
    finally:
        await manager.close_all()
        if not websocket.client_state == "disconnected":
            await websocket.close()
        print("WebSocket 连接已关闭")


@app.on_event("startup")
async def startup_event():
    """
    启动时启动清理过期数据的协程
    """
    asyncio.create_task(cleanup_expired_prompt_ids())

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown
    """
    await http_client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=6006, reload=True)
