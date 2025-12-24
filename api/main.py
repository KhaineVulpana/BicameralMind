"""FastAPI backend for BicameralMind UI"""
import webbrowser
import asyncio
import yaml
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import core system
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import, but don't fail if not available
try:
    from core.bicameral_mind import BicameralMind
    from config.config_loader import load_config
    BICAMERAL_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] BicameralMind import failed: {e}")
    print("[INFO] Running in test mode without full system")
    BICAMERAL_AVAILABLE = False
    BicameralMind = None
    load_config = None

app = FastAPI(title="BicameralMind UI")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
bicameral_mind: Optional[BicameralMind] = None
active_connections: list[WebSocket] = []

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Request models
class ChatMessage(BaseModel):
    text: str


@app.on_event("startup")
async def startup():
    """Initialize bicameral mind on startup"""
    global bicameral_mind

    if not BICAMERAL_AVAILABLE:
        print("[INFO] Running in TEST MODE - UI only, no bicameral mind")
        bicameral_mind = None
        return

    try:
        # Load configuration
        config = load_config()

        # Initialize bicameral mind
        bicameral_mind = BicameralMind(config)

        print("[OK] BicameralMind initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize BicameralMind: {e}")
        # Create a minimal mock for testing
        print("[INFO] Running in test mode without full bicameral mind")
        bicameral_mind = None


@app.get("/")
async def root():
    """Serve main UI"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    return {"message": "BicameralMind UI - Static files not found"}


@app.get("/api/system/status")
async def get_status():
    """Get current system status"""
    if bicameral_mind is None:
        return {
            "mode": "offline",
            "tick_rate": 0.0,
            "hemisphere": "none",
            "memory": {"left": 0, "right": 0, "shared": 0}
        }

    try:
        # Get memory counts
        memory_left = len(bicameral_mind.memory.store.get(
            collection_name="procedural_left",
            include=["metadatas"]
        )["metadatas"] or [])

        memory_right = len(bicameral_mind.memory.store.get(
            collection_name="procedural_right",
            include=["metadatas"]
        )["metadatas"] or [])

        memory_shared = len(bicameral_mind.memory.store.get(
            collection_name="procedural_shared",
            include=["metadatas"]
        )["metadatas"] or [])

        return {
            "mode": bicameral_mind.meta_controller.current_mode.value,
            "tick_rate": bicameral_mind.meta_controller.consciousness_tick,
            "hemisphere": bicameral_mind.meta_controller.active_hemisphere,
            "memory": {
                "left": memory_left,
                "right": memory_right,
                "shared": memory_shared
            }
        }
    except Exception as e:
        print(f"[ERROR] Status error: {e}")
        return {
            "mode": "error",
            "tick_rate": 0.0,
            "hemisphere": "none",
            "memory": {"left": 0, "right": 0, "shared": 0}
        }


@app.post("/api/chat/message")
async def send_message(message: ChatMessage):
    """Process chat message through bicameral mind"""
    if bicameral_mind is None:
        # Test mode response
        import random
        return {
            "response": f"[TEST MODE] You said: '{message.text}' - This is a test response. The full bicameral mind is not initialized yet.",
            "mode": "test",
            "tick_rate": random.uniform(0.3, 0.9),
            "hemisphere": random.choice(["left", "right"]),
            "bullets_used": random.randint(0, 5)
        }

    try:
        # Process through bicameral mind
        response = await bicameral_mind.process_input(message.text)

        # Broadcast to WebSocket clients
        await broadcast({
            "type": "chat_response",
            "message": response
        })

        return {
            "response": response,
            "mode": bicameral_mind.meta_controller.current_mode.value,
            "tick_rate": bicameral_mind.meta_controller.consciousness_tick,
            "hemisphere": bicameral_mind.meta_controller.active_hemisphere,
            "bullets_used": 0  # TODO: Track bullets used
        }
    except Exception as e:
        print(f"[ERROR] Chat error: {e}")
        import traceback
        traceback.print_exc()

        return {
            "response": f"Error processing message: {str(e)}",
            "mode": "error",
            "tick_rate": 0.0,
            "hemisphere": "none",
            "bullets_used": 0
        }


@app.get("/api/mcp/servers")
async def get_mcp_servers():
    """Get MCP server status"""
    # Load config to get server list
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_file.exists():
        return {"servers": []}

    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        servers = config.get('mcp', {}).get('servers', [])

        # Format for UI
        result = []
        for server in servers:
            result.append({
                "name": server['name'],
                "status": "connected" if server.get('enabled') else "disabled",
                "tools": 0,  # TODO: Get actual tool count
                "description": server.get('description', ''),
                "category": server.get('category', 'other')
            })

        return {"servers": result}
    except Exception as e:
        print(f"[ERROR] MCP servers error: {e}")
        return {"servers": []}


@app.get("/api/mcp/config")
async def get_mcp_config():
    """Get current MCP configuration"""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"

    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        servers = config.get('mcp', {}).get('servers', [])
        return {"servers": servers}
    except Exception as e:
        print(f"[ERROR] Get MCP config error: {e}")
        return {"servers": []}


@app.post("/api/mcp/config")
async def update_mcp_config(config_update: dict):
    """Update MCP server configuration"""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"

    try:
        import yaml

        # Load current config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Update server enabled states
        servers = config.get('mcp', {}).get('servers', [])
        for server in servers:
            server_name = server['name']
            if server_name in config_update:
                server['enabled'] = config_update[server_name].get('enabled', False)

                # Update API keys/tokens if provided
                if 'api_key' in config_update[server_name]:
                    if 'env' not in server:
                        server['env'] = {}
                    # Store securely (for now just in config, should use env vars)
                    key_name = list(server.get('env', {}).keys())[0] if server.get('env') else 'API_KEY'
                    server['env'][key_name] = config_update[server_name]['api_key']

                if 'token' in config_update[server_name]:
                    if 'env' not in server:
                        server['env'] = {}
                    token_name = list(server.get('env', {}).keys())[0] if server.get('env') else 'TOKEN'
                    server['env'][token_name] = config_update[server_name]['token']

        # Write back to config
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print("[INFO] MCP configuration updated")
        return {"status": "success"}

    except Exception as e:
        print(f"[ERROR] Update MCP config error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        # Send initial status
        if bicameral_mind:
            await websocket.send_json({
                "type": "status_update",
                "mode": bicameral_mind.meta_controller.current_mode.value,
                "tick_rate": bicameral_mind.meta_controller.consciousness_tick
            })

        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds

            if bicameral_mind:
                await websocket.send_json({
                    "type": "status_update",
                    "mode": bicameral_mind.meta_controller.current_mode.value,
                    "tick_rate": bicameral_mind.meta_controller.consciousness_tick
                })
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass


def launch_ui():
    """Launch UI and open browser"""
    # Open browser after short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Run server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False  # Reduce console spam
    )


if __name__ == "__main__":
    launch_ui()
