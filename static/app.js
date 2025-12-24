// WebSocket connection
let ws = null;
let isConnected = false;

// Connect to WebSocket
function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
        console.log('WebSocket connected');
        isConnected = true;
        updateStatus('CONNECTED');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('ERROR');
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        isConnected = false;
        updateStatus('DISCONNECTED');
        setTimeout(connectWebSocket, 3000); // Reconnect after 3s
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'status_update') {
        // Update status bar
        document.getElementById('mode').textContent = `Mode: ${data.mode.toUpperCase()}`;
        document.getElementById('tick').textContent = `Tick: ${data.tick_rate.toFixed(2)}`;
    } else if (data.type === 'tool_execution') {
        // Add tool execution to log
        addToolLog(data);
    }
}

// Update status indicator
function updateStatus(status) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = `Status: ${status}`;

    // Color coding
    statusEl.style.color = status === 'CONNECTED' ? '#4ec9b0' :
                          status === 'ERROR' ? '#f48771' :
                          '#858585';
}

// Fetch system status
async function fetchStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        // Update memory display
        document.getElementById('memory').textContent =
            `L:${data.memory.left} R:${data.memory.right} S:${data.memory.shared}`;

        // Update mode and hemisphere
        document.getElementById('mode-detail').textContent = data.mode.toUpperCase();
        document.getElementById('hemisphere').textContent = data.hemisphere.toUpperCase();

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
        if (data.servers && data.servers.length > 0) {
            serversDiv.innerHTML = data.servers.map(server => `
                <div class="server ${server.status}">
                    <div class="server-name">${server.name}</div>
                    <div class="server-status">${server.status.toUpperCase()} | ${server.tools} tools</div>
                </div>
            `).join('');
        } else {
            serversDiv.innerHTML = '<div class="loading">No servers configured</div>';
        }
    } catch (error) {
        console.error('Failed to fetch MCP servers:', error);
        document.getElementById('mcp-servers').innerHTML =
            '<div class="loading">Failed to load servers</div>';
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

    // Disable input while processing
    input.disabled = true;
    document.getElementById('send-btn').disabled = true;

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
            tick: data.tick_rate,
            hemisphere: data.hemisphere,
            bullets: data.bullets_used
        });

        // Refresh status after response
        fetchStatus();

    } catch (error) {
        console.error('Failed to send message:', error);
        addMessage('system', `Error: ${error.message}`);
    } finally {
        // Re-enable input
        input.disabled = false;
        document.getElementById('send-btn').disabled = false;
        input.focus();
    }
}

function addMessage(type, text, meta = null) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    let metaHtml = '';
    if (meta) {
        metaHtml = `<div class="meta">
            Mode: ${meta.mode.toUpperCase()} |
            Tick: ${meta.tick.toFixed(2)} |
            Hemisphere: ${meta.hemisphere.toUpperCase()} |
            Bullets: ${meta.bullets || 0}
        </div>`;
    }

    messageDiv.innerHTML = `
        <div class="text">${escapeHtml(text)}</div>
        ${metaHtml}
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addToolLog(data) {
    const logDiv = document.getElementById('mcp-log');

    // Remove "No executions" message if present
    if (logDiv.querySelector('.log-entry')?.textContent === 'No executions yet') {
        logDiv.innerHTML = '';
    }

    const entry = document.createElement('div');
    entry.className = `log-entry ${data.success ? 'success' : 'error'}`;

    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `${timestamp}  ${data.tool}()  ${data.success ? 'SUCCESS' : 'FAILED'}  ${data.duration_ms}ms`;

    logDiv.insertBefore(entry, logDiv.firstChild);

    // Keep only last 10 entries
    while (logDiv.children.length > 10) {
        logDiv.removeChild(logDiv.lastChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Connect WebSocket
    connectWebSocket();

    // Fetch initial data
    fetchStatus();
    fetchMCPServers();

    // Refresh data periodically
    setInterval(fetchStatus, 5000); // Every 5 seconds
    setInterval(fetchMCPServers, 10000); // Every 10 seconds

    // Send message on button click
    document.getElementById('send-btn').addEventListener('click', sendMessage);

    // Send message on Enter key
    document.getElementById('message-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    console.log('BicameralMind UI initialized');
});
