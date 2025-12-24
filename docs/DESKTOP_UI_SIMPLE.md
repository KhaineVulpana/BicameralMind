# Desktop UI - Simplified Testing Interface (Windows)

## Overview

Minimal desktop interface for testing the BicameralMind system. Focus on functionality over aesthetics.

## Simplified Technology Stack

### Option 1: Web-Based Local UI (Recommended)
- **FastAPI**: Backend server with REST + WebSocket
- **HTML/CSS/Vanilla JS**: Simple web interface (no build step!)
- **Browser**: Chrome/Edge (modern Windows browser)
- **Auto-launch**: Python opens browser automatically

**Pros**:
- No Electron overhead
- No build process
- Fast iteration
- Easy debugging (browser DevTools)
- Simple deployment (just run Python)

### Option 2: PyQt6 Native (Alternative)
- **PyQt6**: Native Windows widgets
- **FastAPI**: Backend (same as Option 1)
- **Threading**: Run FastAPI in background thread

**Pros**:
- Native Windows feel
- Single executable possible
- No browser required

**Cons**:
- More complex
- Harder to debug
- Requires PyQt6 installation

## Recommended: Web-Based UI

Let's go with a simple web interface that auto-launches in the browser.

### Architecture

```
Python Process
|
+-- FastAPI Server (port 8000)
|   |-- REST API endpoints
|   |-- WebSocket endpoints
|   |-- Static file serving
|   |-- Auto-launch browser
|
+-- Bicameral Mind Integration
    |-- Direct imports from core/
    |-- Real-time event streaming
```

### UI Components (Simplified)

#### 1. Simple Dashboard
```
+--------------------------------------------+
| BicameralMind Testing Interface            |
+--------------------------------------------+
| Status: RUNNING  |  Mode: EXPLORE  | ^0.75 |
+--------------------------------------------+
| Memory: L:243  R:412  S:87                 |
+--------------------------------------------+
```

#### 2. Chat Interface
```
+--------------------------------------------+
| Chat                                       |
+--------------------------------------------+
|                                            |
| You: How do I validate input?              |
|                                            |
| Left Brain: Always validate...             |
| [Bullets: 3 | Tick: 0.45]                  |
|                                            |
| Right Brain: Consider edge cases...        |
| [Bullets: 5 | Tick: 0.72]                  |
|                                            |
+--------------------------------------------+
| > Type message...                  [Send]  |
+--------------------------------------------+
```

#### 3. MCP Tool Monitor
```
+--------------------------------------------+
| MCP Tools                                  |
+--------------------------------------------+
| filesystem: OK (5 tools)                   |
| github: ERROR (reconnect)                  |
+--------------------------------------------+
| Recent:                                    |
| 10:45:23  read_file()  SUCCESS  45ms       |
| 10:44:12  search()     FAILED   -          |
+--------------------------------------------+
```

## Project Structure

```
BicameralMind/
|
+-- api/
|   +-- main.py                  # FastAPI app + auto-launch
|   +-- routers/
|   |   +-- chat.py              # Chat endpoints
|   |   +-- system.py            # System status
|   |   +-- mcp.py               # MCP tools
|   +-- services/
|   |   +-- bicameral_service.py # Bridge to core
|   +-- websockets/
|       +-- events.py            # WebSocket handlers
|
+-- static/                      # Web UI files
|   +-- index.html               # Main UI (single page)
|   +-- style.css                # Minimal styling
|   +-- app.js                   # Vanilla JS (no frameworks)
|
+-- run_ui.py                    # Launch script
```

## Implementation

### 1. FastAPI Backend (api/main.py)

```python
"""FastAPI backend for BicameralMind UI"""
import webbrowser
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Import core system
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.bicameral_mind import BicameralMind
from core.memory import ProceduralMemory
from integrations.mcp.mcp_client import MCPClient

app = FastAPI(title="BicameralMind UI")

# Global state
bicameral_mind = None
active_connections = []

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def startup():
    global bicameral_mind
    # Initialize bicameral mind
    config = load_config()
    bicameral_mind = BicameralMind(config)
    print("BicameralMind initialized")

@app.get("/")
async def root():
    # Serve main UI
    html_file = static_dir / "index.html"
    return HTMLResponse(content=html_file.read_text())

# REST API
@app.get("/api/system/status")
async def get_status():
    return {
        "mode": bicameral_mind.meta_controller.current_mode.value,
        "tick_rate": bicameral_mind.meta_controller.consciousness_tick,
        "hemisphere": "left" if bicameral_mind.meta_controller.active_hemisphere == "left" else "right",
        "memory": {
            "left": bicameral_mind.memory.get_bullet_count("procedural_left"),
            "right": bicameral_mind.memory.get_bullet_count("procedural_right"),
            "shared": bicameral_mind.memory.get_bullet_count("procedural_shared"),
        }
    }

@app.post("/api/chat/message")
async def send_message(message: dict):
    user_input = message["text"]

    # Process through bicameral mind
    response = await bicameral_mind.process_input(user_input)

    return {
        "response": response,
        "mode": bicameral_mind.meta_controller.current_mode.value,
        "tick_rate": bicameral_mind.meta_controller.consciousness_tick,
    }

@app.get("/api/mcp/servers")
async def get_mcp_servers():
    # Return MCP server status
    return {
        "servers": [
            {"name": "filesystem", "status": "connected", "tools": 5},
            {"name": "github", "status": "error", "tools": 0},
        ]
    }

# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(1)
            status = {
                "type": "status_update",
                "mode": bicameral_mind.meta_controller.current_mode.value,
                "tick_rate": bicameral_mind.meta_controller.consciousness_tick,
            }
            await websocket.send_json(status)
    except:
        active_connections.remove(websocket)

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
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    launch_ui()
```

### 2. Simple HTML UI (static/index.html)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BicameralMind - Testing UI</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>BicameralMind Testing Interface</h1>
            <div class="status-bar">
                <span id="status">Status: LOADING...</span>
                <span id="mode">Mode: -</span>
                <span id="tick">Tick: -</span>
            </div>
        </div>

        <!-- Three-column layout -->
        <div class="main-content">
            <!-- Left: Dashboard -->
            <div class="panel dashboard">
                <h2>System</h2>
                <div class="metric">
                    <label>Memory:</label>
                    <div id="memory">L:- R:- S:-</div>
                </div>
                <div class="metric">
                    <label>Mode:</label>
                    <div id="mode-detail">-</div>
                </div>
            </div>

            <!-- Center: Chat -->
            <div class="panel chat-panel">
                <h2>Conversation</h2>
                <div id="chat-messages" class="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" id="message-input" placeholder="Type your message...">
                    <button id="send-btn">Send</button>
                </div>
            </div>

            <!-- Right: MCP Tools -->
            <div class="panel mcp-panel">
                <h2>MCP Tools</h2>
                <div id="mcp-servers"></div>
                <h3>Recent Executions</h3>
                <div id="mcp-log"></div>
            </div>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

### 3. Minimal CSS (static/style.css)

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #1e1e1e;
    color: #d4d4d4;
    height: 100vh;
}

.container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.header {
    background: #2d2d30;
    padding: 10px 20px;
    border-bottom: 1px solid #3e3e42;
}

.header h1 {
    font-size: 18px;
    margin-bottom: 5px;
}

.status-bar {
    display: flex;
    gap: 20px;
    font-size: 12px;
    color: #858585;
}

.main-content {
    display: grid;
    grid-template-columns: 250px 1fr 300px;
    gap: 10px;
    padding: 10px;
    flex: 1;
    overflow: hidden;
}

.panel {
    background: #252526;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 15px;
    overflow-y: auto;
}

.panel h2 {
    font-size: 14px;
    margin-bottom: 15px;
    color: #cccccc;
}

.panel h3 {
    font-size: 12px;
    margin: 15px 0 10px 0;
    color: #858585;
}

/* Dashboard */
.metric {
    margin-bottom: 15px;
}

.metric label {
    display: block;
    font-size: 11px;
    color: #858585;
    margin-bottom: 3px;
}

.metric div {
    font-size: 13px;
    font-family: 'Consolas', monospace;
}

/* Chat */
.chat-panel {
    display: flex;
    flex-direction: column;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 10px;
}

.message {
    margin-bottom: 15px;
    padding: 8px;
    border-radius: 4px;
}

.message.user {
    background: #094771;
}

.message.left {
    background: #1a472a;
}

.message.right {
    background: #5a1e1e;
}

.message .meta {
    font-size: 10px;
    color: #858585;
    margin-top: 5px;
}

.chat-input {
    display: flex;
    gap: 5px;
}

.chat-input input {
    flex: 1;
    padding: 8px;
    background: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    color: #d4d4d4;
    font-size: 13px;
}

.chat-input button {
    padding: 8px 20px;
    background: #0e639c;
    border: none;
    border-radius: 4px;
    color: white;
    cursor: pointer;
    font-size: 13px;
}

.chat-input button:hover {
    background: #1177bb;
}

/* MCP Tools */
.server {
    margin-bottom: 10px;
    padding: 8px;
    background: #2d2d30;
    border-radius: 4px;
    font-size: 12px;
}

.server.ok { border-left: 3px solid #4ec9b0; }
.server.error { border-left: 3px solid #f48771; }

.log-entry {
    font-size: 11px;
    font-family: 'Consolas', monospace;
    padding: 5px;
    margin-bottom: 5px;
    background: #1e1e1e;
    border-radius: 3px;
}

.log-entry.success { color: #4ec9b0; }
.log-entry.error { color: #f48771; }
```

### 4. Vanilla JavaScript (static/app.js)

```javascript
// WebSocket connection
let ws = null;

// Connect to WebSocket
function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateStatus('CONNECTED');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onerror = () => {
        updateStatus('ERROR');
    };

    ws.onclose = () => {
        updateStatus('DISCONNECTED');
        setTimeout(connectWebSocket, 3000); // Reconnect after 3s
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'status_update') {
        document.getElementById('mode').textContent = `Mode: ${data.mode}`;
        document.getElementById('tick').textContent = `Tick: ${data.tick_rate.toFixed(2)}`;
    }
}

// Update status indicator
function updateStatus(status) {
    document.getElementById('status').textContent = `Status: ${status}`;
}

// Fetch system status
async function fetchStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        document.getElementById('memory').textContent =
            `L:${data.memory.left} R:${data.memory.right} S:${data.memory.shared}`;
        document.getElementById('mode-detail').textContent = data.mode;
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

// Fetch MCP servers
async function fetchMCPServers() {
    try {
        const response = await fetch('/api/mcp/servers');
        const data = await response.json();

        const serversDiv = document.getElementById('mcp-servers');
        serversDiv.innerHTML = data.servers.map(server => `
            <div class="server ${server.status === 'connected' ? 'ok' : 'error'}">
                ${server.name}: ${server.status.toUpperCase()} (${server.tools} tools)
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to fetch MCP servers:', error);
    }
}

// Send chat message
async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();

    if (!text) return;

    // Add user message to chat
    addMessage('user', text);
    input.value = '';

    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        // Add response to chat
        addMessage('left', data.response, {
            mode: data.mode,
            tick: data.tick_rate
        });
    } catch (error) {
        console.error('Failed to send message:', error);
        addMessage('error', 'Failed to send message');
    }
}

function addMessage(type, text, meta = null) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    messageDiv.innerHTML = `
        <div class="text">${text}</div>
        ${meta ? `<div class="meta">Mode: ${meta.mode} | Tick: ${meta.tick.toFixed(2)}</div>` : ''}
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Connect WebSocket
    connectWebSocket();

    // Fetch initial data
    fetchStatus();
    fetchMCPServers();

    // Refresh data periodically
    setInterval(fetchStatus, 5000);
    setInterval(fetchMCPServers, 10000);

    // Send message on button click
    document.getElementById('send-btn').addEventListener('click', sendMessage);

    // Send message on Enter key
    document.getElementById('message-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});
```

### 5. Launch Script (run_ui.py)

```python
"""Launch BicameralMind UI"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and launch
from api.main import launch_ui

if __name__ == "__main__":
    print("=" * 60)
    print(" BicameralMind Testing UI")
    print("=" * 60)
    print()
    print("Starting server on http://localhost:8000")
    print("Browser will open automatically...")
    print()
    print("Press Ctrl+C to stop")
    print()

    launch_ui()
```

## Usage

```bash
# Install dependencies (if needed)
pip install fastapi uvicorn websockets

# Launch UI
python run_ui.py
```

Browser opens automatically at http://localhost:8000

## Next Steps for Implementation

1. Create directory structure:
   - api/
   - static/
   - Create files above

2. Implement basic endpoints:
   - System status
   - Chat (simple echo first)
   - MCP server list

3. Test in browser

4. Add WebSocket updates

5. Connect to actual BicameralMind

## Benefits of This Approach

1. **No build step**: Just HTML/CSS/JS files
2. **Fast iteration**: Edit and refresh browser
3. **Easy debugging**: Browser DevTools
4. **Minimal dependencies**: Just FastAPI + uvicorn
5. **Simple deployment**: One Python command
6. **Windows-optimized**: Uses system browser

## File Checklist

- [ ] api/main.py (FastAPI backend)
- [ ] api/routers/chat.py
- [ ] api/routers/system.py
- [ ] api/routers/mcp.py
- [ ] api/services/bicameral_service.py
- [ ] api/websockets/events.py
- [ ] static/index.html
- [ ] static/style.css
- [ ] static/app.js
- [ ] run_ui.py
