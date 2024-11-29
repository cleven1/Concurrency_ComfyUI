# ComfyUI Proxy Service

A FastAPI-based proxy service for ComfyUI that provides seamless API forwarding and WebSocket support.

## Features

- Seamless proxy for ComfyUI REST APIs
- WebSocket support with bidirectional message forwarding
- High concurrency support through FastAPI and async operations
- File upload handling for images
- Cross-Origin Resource Sharing (CORS) support

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone this repository
2. Run the start script:
```bash
./start.sh
```

This will:
- Install all required dependencies
- Start the FastAPI server

## API Endpoints

### 1. Prompt Endpoint
- **URL:** `/prompt`
- **Method:** POST
- **Body:**
```json
{
    "client_id": "string",
    "prompt": {}
}
```

### 2. Image Upload
- **URL:** `/upload/image`
- **Method:** POST
- **Content-Type:** multipart/form-data
- **Body:** form-data with 'image' field containing the file

### 3. WebSocket Connection
- **URL:** `/ws?clientId=YOUR_CLIENT_ID`
- **Protocol:** WebSocket

## Usage Example

```python
# Prompt example
import requests

response = requests.post('http://localhost:8000/prompt', json={
    "client_id": "dgn",
    "prompt": {}
})

# Image upload example
files = {'image': open('image.png', 'rb')}
response = requests.post('http://localhost:8000/upload/image', files=files)

# WebSocket example
import websockets
import asyncio

async def connect_websocket():
    async with websockets.connect('ws://localhost:8000/ws?clientId=dgn') as websocket:
        # Handle messages
        async for message in websocket:
            print(message)

asyncio.run(connect_websocket())
```

## Configuration

The service is configured to connect to the ComfyUI instance at:
`https://u468885-8a31-33b3a142.yza1.seetacloud.com:8443`

## Running the Server

The server will start on `http://localhost:8000` by default.

To start manually:
```bash
python main.py
```

Or use the provided start script:
```bash
./start.sh
