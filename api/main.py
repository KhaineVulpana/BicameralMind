"""FastAPI backend for BicameralMind UI"""
import webbrowser
import asyncio
import json
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
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
    from core.tools import ToolDefinition, ToolExecutionContext, initialize_tools, register_mcp_tools
    from core.memory.bullet import Hemisphere
    from core.memory import ProcedureStore, Procedure, EpisodicStore, Episode
    from config.config_loader import load_config, save_config
    BICAMERAL_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] BicameralMind import failed: {e}")
    print("[INFO] Running in test mode without full system")
    BICAMERAL_AVAILABLE = False
    BicameralMind = None
    load_config = None
    save_config = None
    ToolDefinition = None
    ToolExecutionContext = None
    initialize_tools = None
    register_mcp_tools = None
    ProcedureStore = None
    Procedure = None
    Hemisphere = None

async def _startup():
    """Initialize bicameral mind on startup."""
    global bicameral_mind
    global tool_registry, tool_executor, tool_index, procedure_store, episodic_store

    if not BICAMERAL_AVAILABLE:
        print("[INFO] Running in TEST MODE - UI only, no bicameral mind")
        bicameral_mind = None
        if load_config and initialize_tools:
            config = load_config()
            tool_registry, tool_executor, tool_index = initialize_tools(config)
            if ProcedureStore:
                procedure_store = ProcedureStore(config)
                procedure_store.load()
            if EpisodicStore:
                episodic_store = EpisodicStore(config)
                episodic_store.load()
        return

    try:
        # Load configuration
        config = load_config()

        # Initialize bicameral mind
        bicameral_mind = BicameralMind(config)
        global procedural_memory
        procedural_memory = getattr(bicameral_mind, "memory", None)
        tool_registry = getattr(bicameral_mind, "tool_registry", None)
        tool_executor = getattr(bicameral_mind, "tool_executor", None)
        tool_index = getattr(bicameral_mind, "tool_index", None)
        if ProcedureStore:
            procedure_store = ProcedureStore(config)
            procedure_store.load()
        if EpisodicStore:
            episodic_store = EpisodicStore(config)
            episodic_store.load()

        if getattr(bicameral_mind, "mcp_client", None) and config.get("mcp", {}).get("enabled", False):
            try:
                await bicameral_mind.mcp_client.connect()
                if tool_registry:
                    await register_mcp_tools(tool_registry, tool_index, bicameral_mind.mcp_client)
            except Exception as e:
                print(f"[WARN] MCP connect/register failed: {e}")

        print("[OK] BicameralMind initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize BicameralMind: {e}")
        # Create a minimal mock for testing
        print("[INFO] Running in test mode without full bicameral mind")
        bicameral_mind = None


async def _shutdown():
    """Cleanup bicameral mind on shutdown."""
    global bicameral_mind
    if bicameral_mind:
        try:
            bicameral_mind.stop()
        except Exception as e:
            print(f"[WARN] Failed to stop BicameralMind: {e}")
        if getattr(bicameral_mind, "mcp_client", None):
            try:
                await bicameral_mind.mcp_client.disconnect()
            except Exception as e:
                print(f"[WARN] MCP disconnect failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup()
    try:
        yield
    finally:
        await _shutdown()


app = FastAPI(title="BicameralMind UI", lifespan=lifespan)

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
tool_registry = None
tool_executor = None
tool_index = None
procedure_store = None
episodic_store = None
active_connections: list[WebSocket] = []

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _tool_to_dict(tool):
    return {
        "name": tool.name,
        "description": tool.description,
        "provider": tool.provider.value if hasattr(tool.provider, "value") else str(tool.provider),
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
        "tags": tool.tags,
        "version": tool.version,
        "enabled": tool.enabled,
        "risk": tool.risk,
        "timeout": tool.timeout,
        "config": tool.config,
        "metadata": tool.metadata,
    }


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


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict = {}
    hemisphere: str = "left"
    confidence: float = 0.5
    metadata: Optional[dict] = None


class ToolRegisterRequest(BaseModel):
    definition: dict


class StagedAssignRequest(BaseModel):
    target: str
    reviewer: Optional[str] = None
    reason: Optional[str] = None


class StagedBulletCreateRequest(BaseModel):
    text: str
    confidence: Optional[float] = None
    tags: Optional[list[str]] = None
    source_hemisphere: Optional[str] = None
    metadata: Optional[dict] = None
    auto_assign: Optional[bool] = None


class ProcedureRequest(BaseModel):
    data: dict


class EpisodeRequest(BaseModel):
    data: dict


def _list_ollama_models() -> list[dict]:
    """Return models available in the local Ollama instance."""
    try:
        proc = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return [{"name": "", "error": str(exc)}]

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return [{"name": "", "error": err or f"ollama list failed (code={proc.returncode})"}]

    lines = [ln.rstrip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if len(lines) <= 1:
        return []

    out: list[dict] = []
    for ln in lines[1:]:
        parts = ln.split()
        if not parts:
            continue
        name = parts[0]
        model_id = parts[1] if len(parts) >= 2 else ""
        size = ""
        modified = ""
        if len(parts) >= 4:
            size = f"{parts[2]} {parts[3]}"
            modified = " ".join(parts[4:]) if len(parts) > 4 else ""
        elif len(parts) >= 3:
            size = parts[2]
        out.append({"name": name, "id": model_id, "size": size, "modified": modified})

    return out


def _try_parse_chat_tool_command(text: str) -> Optional[dict]:
    """Parse simple slash commands for tool usage.

    Supported:
    - /help
    - /tool <tool_name> <json_params?>
    - /open <path>
    """
    if not text:
        return None
    raw = text.strip()
    if not raw.startswith("/"):
        return None

    if raw == "/help":
        return {"type": "help"}

    if raw.startswith("/open "):
        path = raw[len("/open ") :].strip().strip('"')
        if not path:
            return {"type": "error", "message": "Usage: /open <path>"}
        return {"type": "tool", "tool_name": "local.open_path", "parameters": {"path": path}}

    if raw.startswith("/tool "):
        parts = raw.split(None, 2)
        if len(parts) < 2:
            return {"type": "error", "message": "Usage: /tool <tool_name> <json_params?>"}
        tool_name = parts[1].strip()
        params_text = parts[2].strip() if len(parts) >= 3 else "{}"
        if not params_text:
            params_text = "{}"
        try:
            params = json.loads(params_text)
        except Exception as exc:
            return {"type": "error", "message": f"Invalid JSON params: {exc}"}
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return {"type": "error", "message": "Tool params must be a JSON object"}
        return {"type": "tool", "tool_name": tool_name, "parameters": params}

    return {"type": "error", "message": "Unknown command. Try /help"}


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
            "memory": {"left": 0, "right": 0, "shared": 0, "staging": 0},
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
        memory_staging = stats.get("staging", {}).get("count", 0) if stats else 0

        return {
            "mode": bicameral_mind.meta_controller.mode.value,
            "tick_rate": bicameral_mind.meta_controller.get_tick_rate(),
            "hemisphere": bicameral_mind.meta_controller.get_active_hemisphere() or "none",
            "memory": {
                "left": memory_left,
                "right": memory_right,
                "shared": memory_shared,
                "staging": memory_staging
            },
            "model": ((bicameral_mind.config.get("model", {}) or {}).get("slow") or (bicameral_mind.config.get("model", {}) or {})).get("name", "unknown"),
            "health": "OK"
        }
    except Exception as e:
        print(f"[ERROR] Status error: {e}")
        return {
            "mode": "error",
            "tick_rate": 0.0,
            "hemisphere": "none",
            "memory": {"left": 0, "right": 0, "shared": 0, "staging": 0},
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
        status_keys = ("active", "quarantined", "deprecated", "staged", "unknown")
        total_counts = {key: 0 for key in status_keys}
        by_side: dict[str, dict[str, int]] = {}
        for side in ("left", "right", "shared", "staging"):
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


@app.get("/api/memory/staged")
async def list_staged_bullets(limit: int = 50):
    """List staged bullets awaiting assignment."""
    if not procedural_memory:
        return {"bullets": []}
    try:
        bullets = procedural_memory.list_staged(limit=limit)
        return {
            "bullets": [
                {
                    "id": b.id,
                    "text": b.text,
                    "status": b.status.value,
                    "confidence": b.confidence,
                    "tags": b.tags,
                    "metadata": b.metadata,
                }
                for b in bullets
            ]
        }
    except Exception as e:
        print(f"[ERROR] Memory staged error: {e}")
        return {"bullets": []}


@app.post("/api/memory/staged")
async def create_staged_bullet(request: StagedBulletCreateRequest):
    """Create a staged bullet (manual suggestion)."""
    if not procedural_memory:
        return {"error": "memory_unavailable"}

    text = (request.text or "").strip()
    if not text:
        return {"error": "text_required"}

    src = (request.source_hemisphere or "left").lower().strip()
    if src not in ("left", "right", "shared", "staging"):
        src = "left"

    confidence = request.confidence
    try:
        confidence = float(confidence) if confidence is not None else 0.5
    except Exception:
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    meta = dict(request.metadata or {})
    meta.setdefault("source", "ui_suggestion")
    meta.setdefault("source_hemisphere", src)

    bullet = procedural_memory.stage_bullet(
        text=text,
        source_hemisphere=Hemisphere(src) if src in ("left", "right", "staging") else Hemisphere.LEFT,
        tags=request.tags or [],
        confidence=confidence,
        metadata=meta,
        auto_assign=request.auto_assign,
    )

    return {
        "status": "success",
        "bullet": {
            "id": bullet.id,
            "text": bullet.text,
            "status": bullet.status.value,
            "confidence": bullet.confidence,
            "tags": bullet.tags,
            "metadata": bullet.metadata,
        },
    }


@app.post("/api/memory/staged/{bullet_id}/assign")
async def assign_staged_bullet(bullet_id: str, request: StagedAssignRequest):
    """Assign a staged bullet to a hemisphere."""
    if not procedural_memory:
        return {"error": "memory_unavailable"}
    target = request.target.lower().strip()
    if target not in ("left", "right"):
        return {"error": "invalid_target"}
    assigned = procedural_memory.assign_staged_bullet(
        bullet_id,
        Hemisphere(target),
        reviewer=request.reviewer or "manual",
    )
    if not assigned:
        return {"error": "not_found"}
    return {"status": "success", "bullet_id": assigned.id, "side": assigned.side.value}


@app.post("/api/memory/staged/{bullet_id}/reject")
async def reject_staged_bullet(bullet_id: str, request: StagedAssignRequest):
    """Reject a staged bullet."""
    if not procedural_memory:
        return {"error": "memory_unavailable"}
    success = procedural_memory.reject_staged_bullet(
        bullet_id,
        reason=request.reason or "",
        reviewer=request.reviewer or "manual",
    )
    return {"status": "success" if success else "not_found"}


@app.get("/api/procedures")
async def list_procedures(side: Optional[str] = None, status: Optional[str] = None, tag: Optional[str] = None, limit: int = 50):
    """List procedures (playbooks)."""
    if not procedure_store:
        return {"procedures": []}
    tags = [tag] if tag else None
    procedures = procedure_store.list(side=side, status=status, tags=tags, limit=limit)
    return {"procedures": [proc.to_dict() for proc in procedures]}


@app.get("/api/procedures/search")
async def search_procedures(q: str, limit: int = 20):
    """Search procedures by title/description/tags."""
    if not procedure_store:
        return {"procedures": []}
    procedures = procedure_store.search(q, limit=limit)
    return {"procedures": [proc.to_dict() for proc in procedures]}


@app.get("/api/procedures/{proc_id}")
async def get_procedure(proc_id: str):
    """Get a procedure by id."""
    if not procedure_store:
        return {"error": "store_unavailable"}
    proc = procedure_store.get(proc_id)
    if not proc:
        return {"error": "not_found"}
    return {"procedure": proc.to_dict()}


@app.post("/api/procedures")
async def create_procedure(request: ProcedureRequest):
    """Create a new procedure."""
    if not procedure_store:
        return {"error": "store_unavailable"}
    proc = Procedure.from_dict(request.data)
    created = procedure_store.create(proc)
    return {"status": "success", "procedure": created.to_dict()}


@app.patch("/api/procedures/{proc_id}")
async def update_procedure(proc_id: str, request: ProcedureRequest):
    """Update an existing procedure."""
    if not procedure_store:
        return {"error": "store_unavailable"}
    updated = procedure_store.update(proc_id, request.data)
    if not updated:
        return {"error": "not_found"}
    return {"status": "success", "procedure": updated.to_dict()}


@app.delete("/api/procedures/{proc_id}")
async def delete_procedure(proc_id: str):
    """Delete a procedure."""
    if not procedure_store:
        return {"error": "store_unavailable"}
    removed = procedure_store.delete(proc_id)
    return {"status": "success" if removed else "not_found"}


# Episodic memory
@app.get("/api/episodes")
async def list_episodes(side: Optional[str] = None, limit: int = 50):
    """List episodic memories."""
    if not episodic_store:
        return {"episodes": []}
    episodes = episodic_store.list(limit=limit, side=side)
    return {"episodes": [ep.to_dict() for ep in episodes]}


@app.get("/api/episodes/search")
async def search_episodes(q: str, k: int = 5, side: Optional[str] = None):
    """Search episodic memories."""
    if not episodic_store:
        return {"episodes": []}
    episodes, ids = episodic_store.search(q, k=k, side=side)
    return {"episodes": [ep.to_dict() for ep in episodes], "ids": ids}


@app.post("/api/episodes")
async def create_episode(request: EpisodeRequest):
    """Create an episode."""
    if not episodic_store:
        return {"error": "store_unavailable"}
    data = request.data or {}
    if not data.get("id"):
        return {"error": "id_required"}
    ep = episodic_store.add(
        episode_id=data["id"],
        title=data.get("title", ""),
        summary=data.get("summary", ""),
        content=data.get("content", ""),
        side=data.get("side", "shared"),
        tags=data.get("tags") or [],
        outcome=data.get("outcome", "unknown"),
        trace_ids=data.get("trace_ids") or [],
        metadata=data.get("metadata") or {},
    )
    return {"status": "success", "episode": ep.to_dict()}


@app.delete("/api/episodes/{episode_id}")
async def delete_episode(episode_id: str):
    """Delete an episode."""
    if not episodic_store:
        return {"error": "store_unavailable"}
    removed = episodic_store.delete(episode_id)
    return {"status": "success" if removed else "not_found"}


@app.post("/api/chat/message")
async def send_message(message: ChatMessage):
    """Process chat message through bicameral mind"""
    cmd = _try_parse_chat_tool_command(message.text)
    if cmd:
        if cmd["type"] == "help":
            return {
                "response": (
                    "Commands:\n"
                    "- /help\n"
                    "- /open <path>\n"
                    "- /tool <tool_name> <json_params?>\n\n"
                    "Examples:\n"
                    "- /open data\n"
                    "- /tool cli.git {\"args\":[\"status\"]}\n"
                    "- /tool cli.rg {\"args\":[\"-n\",\"AgenticRAG\",\"integrations/rag/agentic_rag.py\"]}"
                ),
                "mode": "tool",
                "hemisphere": "system",
                "tick_rate": 0.0,
                "bullets_used": 0,
            }

        if cmd["type"] == "error":
            return {
                "response": cmd.get("message", "Invalid command"),
                "mode": "tool",
                "hemisphere": "system",
                "tick_rate": 0.0,
                "bullets_used": 0,
            }

        if cmd["type"] == "tool":
            if not tool_executor or ToolExecutionContext is None or not tool_registry:
                return {
                    "response": "Tool system not available",
                    "mode": "tool",
                    "hemisphere": "system",
                    "tick_rate": 0.0,
                    "bullets_used": 0,
                }

            tool_def = tool_registry.get_tool(cmd["tool_name"], allow_disabled=True)
            if not tool_def:
                return {
                    "response": f"Tool not found: {cmd['tool_name']}",
                    "mode": "tool",
                    "hemisphere": "system",
                    "tick_rate": 0.0,
                    "bullets_used": 0,
                }

            tools_cfg = (getattr(bicameral_mind, "config", None) or {}).get("tools", {}) if bicameral_mind else {}
            allow_high_risk = bool(tools_cfg.get("allow_high_risk_chat", False))
            if str(getattr(tool_def, "risk", "low")).lower() == "high" and not allow_high_risk:
                return {
                    "response": (
                        f"Refusing to run high-risk tool via chat: {tool_def.name}\n"
                        "Set `tools.allow_high_risk_chat: true` in config to override."
                    ),
                    "mode": "tool",
                    "hemisphere": "system",
                    "tick_rate": 0.0,
                    "bullets_used": 0,
                }

            context = ToolExecutionContext(
                tool_name=cmd["tool_name"],
                parameters=cmd.get("parameters") or {},
                hemisphere="left",
                confidence=0.5,
                metadata={"source": "chat_command"},
            )
            record = await tool_executor.execute(context)
            try:
                await broadcast(
                    {
                        "type": "tool_execution",
                        "tool": record.context.tool_name,
                        "success": bool(record.result.success),
                        "duration_ms": int((record.result.execution_time or 0.0) * 1000),
                    }
                )
            except Exception:
                pass

            output_text = record.result.output
            if isinstance(output_text, (dict, list)):
                output_text = json.dumps(output_text, indent=2)
            elif output_text is None:
                output_text = ""
            else:
                output_text = str(output_text)

            if record.result.success:
                response_text = f"[OK] {record.context.tool_name}\n{output_text}".strip()
            else:
                err = record.result.error or "Tool failed"
                response_text = f"[FAIL] {record.context.tool_name}: {err}\n{output_text}".strip()

            return {
                "response": response_text,
                "mode": "tool",
                "hemisphere": "system",
                "tick_rate": 0.0,
                "bullets_used": 0,
            }

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
        details = {}
        if response_payload:
            for key in ("mode", "hemisphere", "left", "right", "rag_context", "retrieved_bullets"):
                if key in response_payload:
                    details[key] = response_payload.get(key)

        bullets_used = 0
        retrieved = details.get("retrieved_bullets")
        if isinstance(retrieved, list):
            bullets_used = len(retrieved)
        elif isinstance(response_payload, dict):
            if isinstance(response_payload.get("bullets_count"), int):
                bullets_used = int(response_payload.get("bullets_count") or 0)
            elif isinstance(response_payload.get("bullets_used"), list):
                bullets_used = len(response_payload.get("bullets_used") or [])
        return {
            "response": response_payload.get("output", response),
            "mode": bicameral_mind.meta_controller.mode.value,
            "tick_rate": bicameral_mind.meta_controller.get_tick_rate(),
            "hemisphere": response_payload.get("hemisphere", bicameral_mind.meta_controller.get_active_hemisphere()),
            "bullets_used": bullets_used,
            "details": details,
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


@app.get("/api/tools")
async def list_tools(enabled_only: bool = True, provider: Optional[str] = None):
    """List tools from the registry."""
    if not tool_registry:
        return {"tools": []}
    tools = tool_registry.list_tools(enabled_only=enabled_only)
    if provider:
        tools = [t for t in tools if str(getattr(t.provider, "value", t.provider)) == provider]
    return {"tools": [_tool_to_dict(tool) for tool in tools]}


@app.get("/api/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get a single tool definition."""
    if not tool_registry:
        return {"error": "registry_unavailable"}
    tool = tool_registry.get_tool(tool_name, allow_disabled=True)
    if not tool:
        return {"error": "not_found"}
    return {"tool": _tool_to_dict(tool)}


@app.get("/api/tools/search")
async def search_tools(q: str, k: int = 5, provider: Optional[str] = None):
    """Search tools by semantic similarity."""
    if not tool_index:
        return {"results": []}
    providers = [provider] if provider else None
    results = tool_index.search(q, k=k, providers=providers)
    return {
        "results": [
            {
                "name": r.name,
                "score": r.score,
                "provider": r.provider,
                "description": r.description,
                "tags": r.tags,
            }
            for r in results
        ]
    }


@app.get("/api/tools/stats")
async def get_tool_stats(window_minutes: int = 60, buckets: int = 12, recent: int = 20):
    """Return tool usage analytics based on ToolExecutor execution history."""
    if not tool_executor:
        return {
            "stats": {"total_executions": 0, "success_rate": 0.0},
            "per_tool": [],
            "timeline": [],
            "recent": [],
        }

    history = list(getattr(tool_executor, "execution_history", []) or [])
    base_stats = tool_executor.get_stats() if hasattr(tool_executor, "get_stats") else {"total_executions": len(history)}

    # Per-tool rollups
    per_tool: dict[str, dict] = {}
    for record in history:
        tool_name = getattr(getattr(record, "context", None), "tool_name", "") or ""
        if not tool_name:
            continue
        tool_stats = per_tool.setdefault(
            tool_name,
            {
                "name": tool_name,
                "total": 0,
                "success": 0,
                "failed": 0,
                "total_ms": 0.0,
                "last_used": None,
            },
        )
        tool_stats["total"] += 1
        ok = bool(getattr(getattr(record, "result", None), "success", False))
        if ok:
            tool_stats["success"] += 1
        else:
            tool_stats["failed"] += 1

        exec_time = float(getattr(getattr(record, "result", None), "execution_time", 0.0) or 0.0)
        tool_stats["total_ms"] += exec_time * 1000.0
        ts = getattr(record, "timestamp", None)
        if ts and (tool_stats["last_used"] is None or ts > tool_stats["last_used"]):
            tool_stats["last_used"] = ts

    per_tool_list = []
    for tool_name, row in per_tool.items():
        total = int(row.get("total") or 0)
        success = int(row.get("success") or 0)
        failed = int(row.get("failed") or 0)
        avg_ms = (float(row.get("total_ms") or 0.0) / total) if total else 0.0
        last_used = row.get("last_used")
        per_tool_list.append(
            {
                "name": tool_name,
                "total": total,
                "success": success,
                "failed": failed,
                "success_rate": (success / total) if total else 0.0,
                "avg_duration_ms": avg_ms,
                "last_used": last_used.isoformat() if isinstance(last_used, datetime) else None,
            }
        )

    per_tool_list.sort(key=lambda r: r.get("total", 0), reverse=True)

    # Recent executions
    recent_records = sorted(history, key=lambda r: getattr(r, "timestamp", datetime.min), reverse=True)[: max(0, int(recent))]
    recent_payload = []
    for record in recent_records:
        result = getattr(record, "result", None)
        context = getattr(record, "context", None)
        ts = getattr(record, "timestamp", None)
        recent_payload.append(
            {
                "tool": getattr(context, "tool_name", ""),
                "hemisphere": getattr(context, "hemisphere", ""),
                "success": bool(getattr(result, "success", False)),
                "duration_ms": int(float(getattr(result, "execution_time", 0.0) or 0.0) * 1000),
                "error": getattr(result, "error", None),
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else None,
            }
        )

    # Timeline buckets within a window
    timeline = []
    try:
        window_minutes = max(1, int(window_minutes))
        buckets = max(1, int(buckets))
    except Exception:
        window_minutes = 60
        buckets = 12

    now = datetime.utcnow()
    start = now - timedelta(minutes=window_minutes)
    bucket_seconds = (window_minutes * 60.0) / float(buckets)
    counts = [{"total": 0, "success": 0} for _ in range(buckets)]
    for record in history:
        ts = getattr(record, "timestamp", None)
        if not isinstance(ts, datetime):
            continue
        if ts < start or ts > now:
            continue
        delta = (ts - start).total_seconds()
        idx = int(delta // bucket_seconds) if bucket_seconds > 0 else 0
        idx = min(max(idx, 0), buckets - 1)
        counts[idx]["total"] += 1
        if bool(getattr(getattr(record, "result", None), "success", False)):
            counts[idx]["success"] += 1

    for i in range(buckets):
        bucket_start = start + timedelta(seconds=bucket_seconds * i)
        total = counts[i]["total"]
        success = counts[i]["success"]
        timeline.append(
            {
                "start": bucket_start.isoformat(),
                "total": total,
                "success": success,
                "success_rate": (success / total) if total else 0.0,
            }
        )

    return {
        "stats": base_stats,
        "per_tool": per_tool_list,
        "timeline": timeline,
        "recent": recent_payload,
    }


@app.post("/api/tools/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool via the registry."""
    if not tool_executor or ToolExecutionContext is None:
        return {"error": "executor_unavailable"}
    context = ToolExecutionContext(
        tool_name=request.tool_name,
        parameters=request.parameters or {},
        hemisphere=request.hemisphere,
        confidence=request.confidence,
        metadata=request.metadata or {},
    )
    record = await tool_executor.execute(context)

    try:
        await broadcast(
            {
                "type": "tool_execution",
                "tool": record.context.tool_name,
                "success": bool(record.result.success),
                "duration_ms": int((record.result.execution_time or 0.0) * 1000),
            }
        )
    except Exception:
        pass

    return {
        "tool_name": record.context.tool_name,
        "success": record.result.success,
        "output": record.result.output,
        "error": record.result.error,
        "execution_time": record.result.execution_time,
        "steps": record.execution_steps,
    }


@app.post("/api/tools/register")
async def register_tool(request: ToolRegisterRequest):
    """Register a tool definition."""
    if not tool_registry or ToolDefinition is None:
        return {"error": "registry_unavailable"}
    tool = ToolDefinition.from_dict(request.definition)
    tool_registry.register(tool, save=True)
    if tool_index:
        tool_index.index_tools([tool])
    return {"status": "success", "tool": _tool_to_dict(tool)}


@app.patch("/api/tools/{tool_name}")
async def update_tool(tool_name: str, update: dict):
    """Update tool definition fields."""
    if not tool_registry:
        return {"error": "registry_unavailable"}
    tool = tool_registry.get_tool(tool_name, allow_disabled=True)
    if not tool:
        return {"error": "not_found"}
    for key, value in update.items():
        if hasattr(tool, key):
            setattr(tool, key, value)
    tool_registry.register(tool, save=True)
    if tool_index:
        tool_index.index_tools([tool])
    return {"status": "success", "tool": _tool_to_dict(tool)}


@app.delete("/api/tools/{tool_name}")
async def delete_tool(tool_name: str):
    """Delete a tool definition."""
    if not tool_registry:
        return {"error": "registry_unavailable"}
    removed = tool_registry.remove(tool_name, save=True)
    if removed and tool_index:
        tool_index.remove(tool_name)
    return {"status": "success" if removed else "not_found"}


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

        # Count MCP tools per server (if tool registry loaded)
        tool_counts: dict[str, int] = {}
        if tool_registry:
            try:
                tools_all = tool_registry.list_tools(enabled_only=False)
                for tool in tools_all:
                    provider = getattr(getattr(tool, "provider", None), "value", getattr(tool, "provider", ""))
                    if str(provider) != "mcp":
                        continue
                    if not bool(getattr(tool, "enabled", True)):
                        continue
                    cfg = getattr(tool, "config", None) or {}
                    server_name = cfg.get("server") if isinstance(cfg, dict) else ""
                    if server_name:
                        tool_counts[server_name] = tool_counts.get(server_name, 0) + 1
            except Exception:
                tool_counts = {}

        # Format for UI
        result = []
        for server in servers:
            result.append({
                "name": server['name'],
                "status": "connected" if server.get('enabled') else "disabled",
                "enabled": bool(server.get('enabled')),
                "tools": tool_counts.get(server.get("name", ""), 0),
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


@app.get("/api/models/ollama")
async def list_ollama_models():
    """List locally available Ollama models."""
    return {"models": _list_ollama_models()}


@app.get("/api/models/active")
async def get_active_models():
    """Return currently active model configuration."""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    config = load_config(str(config_file)) if load_config else {}
    model_cfg = (config.get("model", {}) or {})

    slow_cfg = model_cfg.get("slow") or model_cfg
    fast_cfg = model_cfg.get("fast") or {}
    return {
        "slow": (slow_cfg or {}).get("name", ""),
        "fast": (fast_cfg or {}).get("name", ""),
    }


class ActiveModelUpdate(BaseModel):
    slow: str
    fast: Optional[str] = None


@app.post("/api/models/active")
async def set_active_models(update: ActiveModelUpdate):
    """Set active model(s), persist config, and update runtime if possible."""
    slow = (update.slow or "").strip()
    fast = (update.fast or "").strip() if update.fast is not None else ""

    if not slow:
        return {"error": "slow_required"}

    available = {m.get("name") for m in _list_ollama_models() if m.get("name")}
    if available and slow not in available:
        return {"error": "slow_not_available", "available": sorted(available)}
    if fast and available and fast not in available:
        return {"error": "fast_not_available", "available": sorted(available)}

    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    config = load_config(str(config_file)) if load_config else {}
    config.setdefault("model", {})

    # Promote legacy model config to model.slow for consistency.
    if isinstance(config["model"], dict) and "slow" not in config["model"] and "name" in config["model"]:
        config["model"] = {"slow": dict(config["model"])}

    model_cfg = config.get("model", {}) or {}
    slow_cfg = model_cfg.get("slow") or {}
    slow_cfg["name"] = slow
    model_cfg["slow"] = slow_cfg

    if fast:
        fast_cfg = model_cfg.get("fast") or {}
        fast_cfg["name"] = fast
        model_cfg["fast"] = fast_cfg
    else:
        model_cfg.pop("fast", None)

    config["model"] = model_cfg
    if save_config:
        save_config(config, str(config_file))

    if bicameral_mind and hasattr(bicameral_mind, "set_models"):
        try:
            bicameral_mind.set_models(slow, fast_name=fast or None)
        except Exception as exc:
            return {"error": "runtime_update_failed", "message": str(exc)}

    return {"status": "success", "slow": slow, "fast": fast}


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
