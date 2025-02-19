import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import httpx, random
from typing import Dict, Any
import websockets

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ComfyUI base URL
COMFYUI_BASE_URL = "http://127.0.0.1"
PORTS = random.randint(2000, 2009)

# Create an async HTTP client
http_client = httpx.AsyncClient(verify=False)  # disable SSL verification since it's using self-signed cert

@app.post("/prompt")
async def proxy_prompt(data: Dict[Any, Any]):
    """
    Proxy the prompt request to ComfyUI
    """
    try:
        response = await http_client.post(
            f"{COMFYUI_BASE_URL}:{PORTS}/prompt",
            json=data,
            timeout=30.0
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/image")
async def proxy_upload_image(file: UploadFile):
    """
    Proxy image upload to ComfyUI
    """
    try:
        files = {"image": (file.filename, await file.read())}
        response = await http_client.post(
            f"{COMFYUI_BASE_URL}:{PORTS}/upload/image",
            files=files,
            timeout=30.0
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/mask")
async def proxy_upload_mask(file: UploadFile):
    """
    Proxy image upload to ComfyUI
    """
    try:
        files = {"image": (file.filename, await file.read())}
        response = await http_client.post(
            f"{COMFYUI_BASE_URL}:{PORTS}/upload/mask",
            files=files,
            timeout=30.0
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def proxy_websocket(websocket: WebSocket):
    """
    Proxy WebSocket connections to ComfyUI with retry mechanism.
    """
    await websocket.accept()

    # 获取客户端 ID
    client_id = websocket.query_params.get("clientId")
    if not client_id:
        await websocket.close(code=4000, reason="Missing clientId")
        return

    # 连接到 ComfyUI WebSocket 的端口范围和重试次数
    max_retries = 3  # 每个端口重试次数
    ports = range(2000, 2010)

    # 定义消息转发协程
    async def forward_to_client(comfy_ws):
        try:
            while True:
                message = await comfy_ws.recv()
                await websocket.send_text(message)
        except Exception:
            pass

    async def forward_to_comfy(comfy_ws):
        try:
            while True:
                message = await websocket.receive_text()
                await comfy_ws.send(message)
        except Exception:
            pass

    # 尝试连接端口并添加重试机制
    for port in ports:
        for attempt in range(max_retries):
            try:
                async with websockets.connect(
                    f"ws://127.0.0.1:{port}/ws?clientId={client_id}"
                ) as comfy_ws:
                    # 使用 asyncio.gather 进行双向消息转发
                    forward_tasks = asyncio.gather(
                        forward_to_client(comfy_ws),
                        forward_to_comfy(comfy_ws)
                    )

                    try:
                        await forward_tasks
                    except Exception:
                        pass
                    finally:
                        forward_tasks.cancel()
                    return  # 成功连接后，结束函数

            except Exception as e:
                print(f"Connection to port {port} failed on attempt {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(1)  # 在重试之间等待 1 秒

    # 如果所有端口和重试均失败，则关闭连接
    await websocket.close(code=1011, reason="All port connection attempts failed")



@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown
    """
    await http_client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=6006, reload=True)
