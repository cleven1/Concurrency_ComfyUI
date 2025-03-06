import asyncio, json
import websockets
from urllib.parse import urlparse
from typing import List
from urllib.parse import urlparse
from utils import CACHES, find_value
from datetime import datetime

MAX_RETRIES=30

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[websockets.WebSocketClientProtocol] = []
        self.client_ws = None
        self.tasks = []

    async def connect_to_all_ports(self, base_urls, ports_range, client_id):
        """连接到所有指定端口"""
        connect_tasks = []
        for base_url in base_urls:
            for port in ports_range:
                task = asyncio.create_task(
                    self._create_connection(base_url, port, client_id)
                )
                connect_tasks.append(task)
        
        await asyncio.gather(*connect_tasks)
        return len(self.active_connections) > 0

    async def _create_connection(self, base_url, port, client_id):
        """创建单个ComfyUI连接"""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                url = self.build_ws_url(base_url, port, client_id)
                print(f"尝试连接 {url} (第 {attempt} 次)...")
                comfy_ws = await websockets.connect(url, timeout=5)
                self.active_connections.append(comfy_ws)
                print(f"✅ 成功连接到 {url}")
                # 为每个连接创建独立的接收任务
                self.tasks.append(asyncio.create_task(
                    self._forward_comfy_to_client(comfy_ws)
                ))
                return
            except Exception as e:
                print(f"连接 {url} 失败: {str(e)}")
                await asyncio.sleep(2)

    async def broadcast_to_comfy(self, message: str):
        """广播消息到所有ComfyUI连接"""
        send_tasks = []
        for conn in self.active_connections:
            if not conn.closed:
                send_tasks.append(conn.send(message))
        if send_tasks:
            await asyncio.gather(*send_tasks)

    async def _forward_comfy_to_client(self, comfy_ws: websockets.WebSocketClientProtocol):
        """从单个ComfyUI连接转发消息到客户端"""
        try:
            async for message in comfy_ws:
                if self.client_ws.client_state == "disconnected":
                    break
                
                result = json.loads(message)
                t = result.get("type")
                if t == "executed":
                    filename = find_value(result, "filename")
                    if filename is not None:
                        host, port = comfy_ws.remote_address
                        if host == "127.0.0.1":
                            host = f"http://{host}:{port}"
                        else:
                            host = f"https://{host}:{port}"
                        print(f"host: {host}")
                        CACHES[filename] = {"link": host, "timestamp": datetime.now()}
                
                await self.client_ws.send_text(message)
                print(f"转发 ComfyUI 消息: {message}")
        except Exception as e:
            print(f"ComfyUI 消息转发异常: {str(e)}")
        finally:
            await self._close_connection(comfy_ws)

    async def _close_connection(self, comfy_ws: websockets.WebSocketClientProtocol):
        """关闭单个连接并清理资源"""
        if not comfy_ws.closed:
            await comfy_ws.close()
        if comfy_ws in self.active_connections:
            self.active_connections.remove(comfy_ws)

    def build_ws_url(self, base_url, port, client_id):
        """构建WebSocket URL"""
        parsed = urlparse(base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        hostname = parsed.hostname or parsed.path.split(":")[0]
        return f"{scheme}://{hostname}:{port}/ws?clientId={client_id}"

    async def close_all(self):
        """关闭所有连接"""
        close_tasks = []
        for conn in self.active_connections:
            if not conn.closed:
                close_tasks.append(conn.close())
        if close_tasks:
            await asyncio.gather(*close_tasks)
        self.active_connections.clear()

    
    async def _handle_client_messages(self):
        """处理来自客户端的消息并广播"""
        try:
            while True:
                message = await self.client_ws.receive_text()
                print(f"收到客户端消息: {message}")
                await self.broadcast_to_comfy(message)
        except Exception as e:
            print(f"客户端消息接收异常: {str(e)}")