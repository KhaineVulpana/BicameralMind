"""FastAPI backend for BicameralMind UI"""
import webbrowser
import asyncio
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
    from config.config_loader import load_config, save_config
    BICAMERAL_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] BicameralMind import failed: {e}")
    print("[INFO] Running in test mode without full system")
    BICAMERAL_AVAILABLE = False
    BicameralMind = None
    load_config = None
    save_config = None

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
procedural_memory = None
active_connections: list[WebSocket] = []

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Request models
class ChatMessage(BaseModel):
    text: str
    mode: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class MCPServerModel(BaseModel):
    name: str
    type: str = "stdio"
    command: str
    args: list[str] = []
    enabled: bool = True
    description: str = ""
    category: str = "other"
    env: Optional[dict] = None


class MCPServerUpdate(BaseModel):
    type: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list[str]] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    category: Optional[str] = None
    env: Optional[dict] = None


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
        global procedural_memory
        procedural_memory = getattr(bicameral_mind, "memory", None)

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
            "memory": {"left": 0, "right": 0, "shared": 0},
            "model": "offline",
            "health": "OFFLINE"
        }

    try:
        stats = None
        if procedural_memory:
            stats = procedural_memory.get_stats().get("collections", {})
        memory_left = stats.get("left", {}).get("count", 0) if stats else 0
        memory_right = stats.get("right", {}).get("count", 0) if stats else 0
        memory_shared = stats.get("shared", {}).get("count", 0) if stats else 0

        return {
            "mode": bicameral_mind.meta_controller.mode.value,
            "tick_rate": bicameral_mind.meta_controller.get_tick_rate(),
            "hemisphere": bicameral_mind.meta_controller.get_active_hemisphere() or "none",
            "memory": {
                "left": memory_left,
                "right": memory_right,
                "shared": memory_shared
            },
            "model": bicameral_mind.config.get("model", {}).get("name", "unknown"),
            "health": "OK"
        }
    except Exception as e:
        print(f"[ERROR] Status error: {e}")
        return {
            "mode": "error",
            "tick_rate": 0.0,
            "hemisphere": "none",
            "memory": {"left": 0, "right": 0, "shared": 0},
            "model": "unknown",
            "health": "ERROR"
        }


@app.get("/api/memory/stats")
async def get_memory_stats():
    """Return procedural memory statistics."""
    if not procedural_memory or not getattr(procedural_memory, "enabled", False):
        return {"enabled": False, "collections": {}, "status": {}}
    try:
        stats = procedural_memory.get_stats()
        status_keys = ("active", "quarantined", "deprecated", "unknown")
        total_counts = {key: 0 for key in status_keys}
        by_side: dict[str, dict[str, int]] = {}
        for side in ("left", "right", "shared"):
            side_counts = {key: 0 for key in status_keys}
            try:
                bullets = procedural_memory.store.list_bullets(side, limit=10000, include_deprecated=True)
            except Exception:
                bullets = []
            for bullet in bullets:
                status = (bullet.status or "active").lower()
                if status not in side_counts:
                    status = "unknown"
                side_counts[status] += 1
                total_counts[status] += 1
            by_side[side] = side_counts
        stats["status"] = {
            "total": total_counts,
            "by_side": by_side
        }
        return stats
    except Exception as e:
        print(f"[ERROR] Memory stats error: {e}")
        return {"enabled": False, "collections": {}, "status": {}}


@app.get("/api/memory/bullets")
async def get_memory_bullets(hemisphere: str = "shared", limit: int = 25):
    """Return a list of procedural bullets for a hemisphere."""
    if not procedural_memory:
        return {"bullets": []}
    try:
        raw = procedural_memory.store.list_bullets(hemisphere, limit=limit)
        bullets = []
        for item in raw:
            bullet = procedural_memory._convert_bullet(item)
            bullets.append({
                "id": bullet.id,
                "text": bullet.text,
                "side": bullet.side.value,
                "type": bullet.type.value,
                "tags": bullet.tags,
                "status": bullet.status.value,
                "confidence": bullet.confidence,
                "helpful_count": bullet.helpful_count,
                "harmful_count": bullet.harmful_count,
                "score": bullet.score(),
            })
        return {"bullets": bullets}
    except Exception as e:
        print(f"[ERROR] Memory bullet error: {e}")
        return {"bullets": []}


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
        response = await bicameral_mind.process(message.text)

        # Broadcast to WebSocket clients
        await broadcast({
            "type": "chat_response",
            "message": response
        })

        response_payload = response if isinstance(response, dict) else {}
        return {
            "response": response_payload.get("output", response),
            "mode": bicameral_mind.meta_controller.mode.value,
            "tick_rate": bicameral_mind.meta_controller.get_tick_rate(),
            "hemisphere": response_payload.get("hemisphere", bicameral_mind.meta_controller.get_active_hemisphere()),
            "bullets_used": 0
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
        config = load_config(str(config_file)) if load_config else {}

        servers = config.get('mcp', {}).get('servers', [])

        # Format for UI
        result = []
        for server in servers:
            result.append({
                "name": server['name'],
                "status": "connected" if server.get('enabled') else "disabled",
                "enabled": bool(server.get('enabled')),
                "tools": 0,  # TODO: Get actual tool count
                "description": server.get('description', ''),
                "category": server.get('category', 'other')
            })

        return {"servers": result}
    except Exception as e:
        print(f"[ERROR] MCP servers error: {e}")
        return {"servers": []}


@app.get("/api/mcp/servers/{server_name}")
async def get_mcp_server(server_name: str):
    """Return MCP server details."""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        config = load_config(str(config_file)) if load_config else {}
        servers = config.get("mcp", {}).get("servers", [])
        for server in servers:
            if server.get("name") == server_name:
                return {
                    "name": server.get("name"),
                    "type": server.get("type", "stdio"),
                    "command": server.get("command", ""),
                    "args": server.get("args", []),
                    "enabled": bool(server.get("enabled", False)),
                    "description": server.get("description", ""),
                    "category": server.get("category", "other"),
                    "env": server.get("env", {}),
                }
        return {"error": "not_found"}
    except Exception as e:
        print(f"[ERROR] MCP server detail error: {e}")
        return {"error": "failed"}


@app.post("/api/mcp/servers")
async def add_mcp_server(server: MCPServerModel):
    """Add a new MCP server to config."""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        config = load_config(str(config_file)) if load_config else {}
        config.setdefault("mcp", {})
        servers = config["mcp"].setdefault("servers", [])
        if any(s.get("name") == server.name for s in servers):
            return {"status": "exists"}
        servers.append({
            "name": server.name,
            "type": server.type,
            "command": server.command,
            "args": server.args,
            "enabled": server.enabled,
            "description": server.description,
            "category": server.category,
            "env": server.env or {},
        })
        if save_config:
            save_config(config, str(config_file))
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] MCP add server error: {e}")
        return {"status": "error", "message": str(e)}


@app.patch("/api/mcp/servers/{server_name}")
async def update_mcp_server(server_name: str, update: MCPServerUpdate):
    """Update MCP server configuration."""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        config = load_config(str(config_file)) if load_config else {}
        servers = config.get("mcp", {}).get("servers", [])
        updated = False
        for server in servers:
            if server.get("name") != server_name:
                continue
            for key, value in update.model_dump(exclude_unset=True).items():
                if value is None:
                    continue
                server[key] = value
            updated = True
            break
        if updated and save_config:
            save_config(config, str(config_file))
        return {"status": "success" if updated else "not_found"}
    except Exception as e:
        print(f"[ERROR] MCP update server error: {e}")
        return {"status": "error", "message": str(e)}


@app.delete("/api/mcp/servers/{server_name}")
async def delete_mcp_server(server_name: str):
    """Remove an MCP server from config."""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        config = load_config(str(config_file)) if load_config else {}
        servers = config.get("mcp", {}).get("servers", [])
        filtered = [s for s in servers if s.get("name") != server_name]
        if len(filtered) == len(servers):
            return {"status": "not_found"}
        config["mcp"]["servers"] = filtered
        if save_config:
            save_config(config, str(config_file))
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] MCP delete server error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/mcp/config")
async def get_mcp_config():
    """Get current MCP configuration"""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"

    try:
        config = load_config(str(config_file)) if load_config else {}
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
        # Load current config
        config = load_config(str(config_file)) if load_config else {}

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
        if save_config:
            save_config(config, str(config_file))

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
                "mode": bicameral_mind.meta_controller.mode.value,
                "tick_rate": bicameral_mind.meta_controller.get_tick_rate()
            })

        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds

            if bicameral_mind:
                await websocket.send_json({
                    "type": "status_update",
                    "mode": bicameral_mind.meta_controller.mode.value,
                    "tick_rate": bicameral_mind.meta_controller.get_tick_rate()
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
