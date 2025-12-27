// WebSocket connection
let ws = null;
let isConnected = false;
let toolCache = [];
let chatSuggestions = [];
const chatMetrics = {
    tokens: 0,
    bullets: 0,
    ticks: 0,
    responseTime: 0
};

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

function estimateTokens(text) {
    if (!text) return 0;
    const trimmed = text.trim();
    if (!trimmed) return 0;
    return Math.max(1, Math.ceil(trimmed.length / 4));
}

function updateAnalytics() {
    setText('analytics-tokens', `${chatMetrics.tokens}`);
    setText('analytics-bullets', `${chatMetrics.bullets}`);
    setText('analytics-ticks', `${chatMetrics.ticks}`);
    setText('analytics-response-time', `${chatMetrics.responseTime}ms`);
}

function resetChatMetrics() {
    chatMetrics.tokens = 0;
    chatMetrics.bullets = 0;
    chatMetrics.ticks = 0;
    chatMetrics.responseTime = 0;
    updateAnalytics();
}

function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
        isConnected = true;
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
        isConnected = false;
        updateStatus('DISCONNECTED');
        setTimeout(connectWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'status_update') {
        const mode = data.mode ? data.mode.toUpperCase() : '-';
        const tick = typeof data.tick_rate === 'number' ? data.tick_rate.toFixed(2) : '-';
        document.getElementById('mode').textContent = `Mode: ${mode}`;
        document.getElementById('tick').textContent = `Tick: ${tick}`;
        const tickDetail = document.getElementById('tick-detail');
        if (tickDetail) {
            tickDetail.textContent = tick;
        }
        const tickCurrent = document.getElementById('tick-current');
        if (tickCurrent) {
            tickCurrent.textContent = tick;
        }
        const modeDetail = document.getElementById('mode-detail');
        if (modeDetail) {
            modeDetail.textContent = mode;
        }
    } else if (data.type === 'tool_execution') {
        addToolLog(data);
    }
}

function updateStatus(status) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = `Status: ${status}`;
    statusEl.style.color = status === 'CONNECTED' ? '#3fbac2' : status === 'ERROR' ? '#e06c75' : '#7f8b9b';
}

async function fetchStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        const memory = data.memory || { left: 0, right: 0, shared: 0, staging: 0 };
        const mode = data.mode ? data.mode.toUpperCase() : '-';
        const hemisphere = data.hemisphere ? data.hemisphere.toUpperCase() : '-';
        const tickRate = typeof data.tick_rate === 'number' ? data.tick_rate.toFixed(2) : '-';

        setText('mode', `Mode: ${mode}`);
        setText('tick', `Tick: ${tickRate}`);

        const memoryEl = document.getElementById('memory');
        if (memoryEl) {
            memoryEl.textContent = `L:${memory.left} R:${memory.right} S:${memory.shared}`;
        }
        const memoryLeft = document.getElementById('memory-left');
        const memoryRight = document.getElementById('memory-right');
        const memoryShared = document.getElementById('memory-shared');
        if (memoryLeft) memoryLeft.textContent = memory.left ?? '-';
        if (memoryRight) memoryRight.textContent = memory.right ?? '-';
        if (memoryShared) memoryShared.textContent = memory.shared ?? '-';
        const memoryStaging = document.getElementById('memory-staging');
        if (memoryStaging) memoryStaging.textContent = memory.staging ?? '-';

        const modeDetail = document.getElementById('mode-detail');
        if (modeDetail) modeDetail.textContent = mode;
        const hemisphereEl = document.getElementById('hemisphere');
        if (hemisphereEl) hemisphereEl.textContent = hemisphere;
        const tickDetail = document.getElementById('tick-detail');
        if (tickDetail) tickDetail.textContent = tickRate;
        const tickCurrent = document.getElementById('tick-current');
        if (tickCurrent) tickCurrent.textContent = tickRate;
        const modelName = document.getElementById('model-name');
        if (modelName) modelName.textContent = data.model || '-';
        const systemHealth = document.getElementById('system-health');
        if (systemHealth) systemHealth.textContent = data.health || '-';
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

async function fetchMemoryStats() {
    try {
        const response = await fetch('/api/memory/stats');
        const data = await response.json();
        if (!data || data.enabled === false) {
            setText('memory-active', '-');
            setText('memory-quarantined', '-');
            setText('memory-deprecated', '-');
            return;
        }
        const status = data.status || {};
        const total = status.total || {};
        setText('memory-active', total.active ?? '-');
        setText('memory-quarantined', total.quarantined ?? '-');
        setText('memory-deprecated', total.deprecated ?? '-');
        setText('memory-staged', total.staged ?? '-');
    } catch (error) {
        console.error('Failed to fetch memory stats:', error);
    }
}

async function fetchProcedures() {
    const list = document.getElementById('procedure-list');
    if (!list) return;

    try {
        const response = await fetch('/api/procedures');
        const data = await response.json();
        const procedures = data.procedures || [];
        if (!procedures.length) {
            list.innerHTML = '<div class="loading">No procedures yet</div>';
            return;
        }
        list.innerHTML = procedures.map((proc) => {
            const tags = (proc.tags || []).slice(0, 3).join(', ');
            return `
                <div class="procedure-card">
                    <div>
                        <h3>${escapeHtml(proc.title || '')}</h3>
                        <p>${escapeHtml(proc.description || '')}</p>
                        <p>${tags ? `Tags: ${escapeHtml(tags)}` : 'No tags'} | Status: ${escapeHtml(proc.status || '')}</p>
                    </div>
                    <span class="pill">${escapeHtml(proc.side || 'shared')}</span>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to fetch procedures:', error);
        list.innerHTML = '<div class="loading">Failed to load procedures</div>';
    }
}

async function fetchTools() {
    const table = document.getElementById('tool-table');
    if (!table) return;
    table.innerHTML = `
        <div class="tool-row header">
            <span>Tool</span>
            <span>Provider</span>
            <span>Status</span>
        </div>
        <div class="tool-row"><span>Loading...</span><span></span><span></span></div>
    `;
    try {
        const response = await fetch('/api/tools');
        const data = await response.json();
        const tools = data.tools || [];
        toolCache = tools.slice();
        populateToolRunner(tools);
        if (!tools.length) {
            table.innerHTML = `
                <div class="tool-row header">
                    <span>Tool</span><span>Provider</span><span>Status</span>
                </div>
                <div class="tool-row"><span>No tools registered</span><span></span><span></span></div>
            `;
            return;
        }
        table.innerHTML = `
            <div class="tool-row header">
                <span>Tool</span><span>Provider</span><span>Status</span>
            </div>
            ${tools.map((tool) => {
                const statusClass = tool.enabled ? 'pill ok' : 'pill warn';
                return `
                    <div class="tool-row">
                        <span>${escapeHtml(tool.name)}</span>
                        <span>${escapeHtml(tool.provider)}</span>
                        <span class="${statusClass}">${tool.enabled ? 'Enabled' : 'Disabled'}</span>
                    </div>
                `;
            }).join('')}
        `;
    } catch (error) {
        console.error('Failed to fetch tools:', error);
        table.innerHTML = '<div class="tool-row"><span>Failed to load tools</span><span></span><span></span></div>';
    }
}

function populateToolRunner(tools) {
    const select = document.getElementById('tool-exec-name');
    if (!select) return;

    const current = select.value;
    const sorted = (tools || []).slice().sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    select.innerHTML = sorted
        .map((tool) => {
            const label = `${tool.name} (${tool.provider})`;
            return `<option value="${escapeHtml(tool.name)}">${escapeHtml(label)}</option>`;
        })
        .join('');

    if (current && (tools || []).some((t) => t.name === current)) {
        select.value = current;
    } else if (!select.value && sorted.length) {
        select.value = sorted[0].name;
    }
}

async function runSelectedTool() {
    const nameEl = document.getElementById('tool-exec-name');
    const paramsEl = document.getElementById('tool-exec-params');
    const hemiEl = document.getElementById('tool-exec-hemisphere');
    const confEl = document.getElementById('tool-exec-confidence');
    const outEl = document.getElementById('tool-exec-output');
    if (!nameEl || !paramsEl || !hemiEl || !confEl || !outEl) return;

    const toolName = nameEl.value;
    let parameters = {};
    try {
        parameters = JSON.parse(paramsEl.value || '{}');
    } catch (err) {
        outEl.value = `Invalid JSON: ${err}`;
        return;
    }

    const confidence = Number(confEl.value);
    const hemisphere = (hemiEl.value || 'left').toLowerCase();

    outEl.value = 'Running...';

    try {
        const resp = await fetch('/api/tools/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tool_name: toolName,
                parameters,
                hemisphere,
                confidence: Number.isFinite(confidence) ? confidence : 0.5
            })
        });
        const data = await resp.json();
        outEl.value = JSON.stringify(data, null, 2);
    } catch (error) {
        outEl.value = `Request failed: ${error}`;
    }
}

async function fetchStaged() {
    const table = document.getElementById('staged-table');
    if (!table) return;
    table.innerHTML = `
        <div class="tool-row header">
            <span>Text</span><span>Confidence</span><span>Source</span><span>Actions</span>
        </div>
        <div class="tool-row"><span>Loading...</span><span></span><span></span><span></span></div>
    `;
    try {
        const response = await fetch('/api/memory/staged');
        const data = await response.json();
        const bullets = data.bullets || [];
        if (!bullets.length) {
            table.innerHTML = `
                <div class="tool-row header">
                    <span>Text</span><span>Confidence</span><span>Source</span><span>Actions</span>
                </div>
                <div class="tool-row"><span>No staged bullets</span><span></span><span></span><span></span></div>
            `;
            return;
        }
        table.innerHTML = `
            <div class="tool-row header">
                <span>Text</span><span>Confidence</span><span>Source</span><span>Actions</span>
            </div>
            ${bullets.map((b) => {
                const conf = (b.confidence ?? 0).toFixed ? b.confidence.toFixed(2) : b.confidence || '-';
                const src = (b.metadata && b.metadata.source_hemisphere) ? b.metadata.source_hemisphere : '-';
                return `
                    <div class="tool-row">
                        <span title="${escapeHtml(b.id)}">${escapeHtml(b.text || '')}</span>
                        <span>${conf}</span>
                        <span>${escapeHtml(src)}</span>
                        <span class="actions">
                            <button class="ghost-btn" data-action="assign-left" data-id="${b.id}">Assign Left</button>
                            <button class="ghost-btn" data-action="assign-right" data-id="${b.id}">Assign Right</button>
                            <button class="ghost-btn warn" data-action="reject" data-id="${b.id}">Reject</button>
                        </span>
                    </div>
                `;
            }).join('')}
        `;
        table.querySelectorAll('button').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                if (!id) return;
                if (btn.dataset.action === 'assign-left') {
                    await assignStaged(id, 'left');
                } else if (btn.dataset.action === 'assign-right') {
                    await assignStaged(id, 'right');
                } else if (btn.dataset.action === 'reject') {
                    await rejectStaged(id);
                }
                fetchStaged();
                fetchMemoryStats();
            });
        });
    } catch (error) {
        console.error('Failed to fetch staged bullets:', error);
        table.innerHTML = '<div class="tool-row"><span>Failed to load staged bullets</span><span></span><span></span><span></span></div>';
    }
}

async function assignStaged(id, target) {
    await fetch(`/api/memory/staged/${encodeURIComponent(id)}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
    });
}

async function rejectStaged(id) {
    await fetch(`/api/memory/staged/${encodeURIComponent(id)}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
}

async function fetchMCPServers() {
    try {
        const response = await fetch('/api/mcp/servers');
        const data = await response.json();
        const serversDiv = document.getElementById('mcp-servers');
        if (!serversDiv) return;

        if (data.servers && data.servers.length > 0) {
            serversDiv.innerHTML = data.servers.map((server) => {
                const statusClass = server.status === 'connected' ? 'pill ok' : server.status === 'disabled' ? 'pill' : 'pill warn';
                const toggleLabel = server.enabled ? 'Disable' : 'Enable';
                return `
                    <div class="server-item" data-name="${escapeHtml(server.name)}">
                        <div class="server-head">
                            <div class="server-name">${escapeHtml(server.name)}</div>
                            <div class="server-actions">
                                <button class="ghost-btn" data-action="toggle">${toggleLabel}</button>
                                <button class="ghost-btn" data-action="remove">Remove</button>
                            </div>
                        </div>
                        <div class="server-meta">
                            <span class="${statusClass}">${escapeHtml(server.status || 'unknown')}</span>
                            <span>Tools: ${server.tools ?? 0}</span>
                            <span>Category: ${escapeHtml(server.category || 'other')}</span>
                        </div>
                        <div class="server-meta">${escapeHtml(server.description || '')}</div>
                    </div>
                `;
            }).join('');

            serversDiv.querySelectorAll('.server-item').forEach((item) => {
                const name = item.dataset.name;
                item.querySelectorAll('button').forEach((btn) => {
                    btn.addEventListener('click', () => handleServerAction(name, btn.dataset.action));
                });
            });
        } else {
            serversDiv.innerHTML = '<div class="loading">No servers configured</div>';
        }
    } catch (error) {
        console.error('Failed to fetch MCP servers:', error);
    }
}

async function handleServerAction(name, action) {
    if (!name) return;
    if (action === 'remove') {
        await deleteMCPServer(name);
    } else if (action === 'toggle') {
        await toggleMCPServer(name);
    }
}

async function toggleMCPServer(name) {
    try {
        const response = await fetch(`/api/mcp/servers/${encodeURIComponent(name)}`);
        const server = await response.json();
        const nextEnabled = !server.enabled;
        await fetch(`/api/mcp/servers/${encodeURIComponent(name)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: nextEnabled })
        });
        fetchMCPServers();
    } catch (error) {
        console.error('Failed to toggle server:', error);
    }
}

async function deleteMCPServer(name) {
    try {
        await fetch(`/api/mcp/servers/${encodeURIComponent(name)}`, { method: 'DELETE' });
        fetchMCPServers();
    } catch (error) {
        console.error('Failed to delete server:', error);
    }
}

async function addMCPServer(event) {
    event.preventDefault();
    const payload = {
        name: document.getElementById('mcp-name').value.trim(),
        type: document.getElementById('mcp-type').value,
        command: document.getElementById('mcp-command').value.trim(),
        args: document.getElementById('mcp-args').value.split(',').map((s) => s.trim()).filter(Boolean),
        description: document.getElementById('mcp-description').value.trim(),
        category: document.getElementById('mcp-category').value.trim(),
        enabled: document.getElementById('mcp-enabled').checked
    };

    try {
        await fetch('/api/mcp/servers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        event.target.reset();
        fetchMCPServers();
    } catch (error) {
        console.error('Failed to add server:', error);
    }
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage('user', text);
    input.value = '';

    input.disabled = true;
    document.getElementById('send-btn').disabled = true;
    const startTime = performance.now();

    try {
        const modeSelect = document.getElementById('chat-mode');
        const tempInput = document.getElementById('chat-temp');
        const tokenInput = document.getElementById('chat-tokens');
        const payload = {
            text,
            mode: modeSelect ? modeSelect.value : 'auto'
        };
        const tempValue = tempInput ? parseFloat(tempInput.value) : NaN;
        const tokenValue = tokenInput ? parseInt(tokenInput.value, 10) : NaN;
        if (Number.isFinite(tempValue)) {
            payload.temperature = tempValue;
        }
        if (Number.isFinite(tokenValue)) {
            payload.max_tokens = tokenValue;
        }

        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        const responseText = data.response || data.output || '';
        addMessage('assistant', responseText, {
            mode: data.mode,
            tick: data.tick_rate,
            hemisphere: data.hemisphere,
            bullets: data.bullets_used
        });
        renderChatTrace(data.details);
        pushSuggestionsFromDetails(data.details);

        chatMetrics.tokens += estimateTokens(text) + estimateTokens(responseText);
        if (Number.isFinite(data.bullets_used)) {
            chatMetrics.bullets += data.bullets_used;
        }
        chatMetrics.ticks += 1;
        chatMetrics.responseTime = Math.round(performance.now() - startTime);
        updateAnalytics();

        fetchStatus();
    } catch (error) {
        console.error('Failed to send message:', error);
        addMessage('system', `Error: ${error.message}`);
    } finally {
        input.disabled = false;
        document.getElementById('send-btn').disabled = false;
        input.focus();
    }
}

function addMessage(type, text, meta = null) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const normalized = (type || '').toLowerCase();
    const roleMap = {
        user: 'user',
        left: 'left',
        right: 'right',
        both: 'integrated',
        integrated: 'integrated',
        assistant: 'integrated',
        meta: 'integrated',
        system: 'system'
    };
    const labelMap = {
        user: 'User',
        left: 'Left Brain',
        right: 'Right Brain',
        both: 'Integrated',
        integrated: 'Integrated',
        assistant: 'Assistant',
        meta: 'Meta Controller',
        system: 'System'
    };
    const role = roleMap[normalized] || 'system';
    const label = labelMap[normalized] || 'System';
    messageDiv.className = `message ${role}`;

    let metaHtml = '';
    if (meta) {
        const mode = meta.mode ? meta.mode.toUpperCase() : '-';
        const tick = typeof meta.tick === 'number' ? meta.tick.toFixed(2) : '-';
        const hemisphere = meta.hemisphere ? meta.hemisphere.toUpperCase() : '-';
        metaHtml = `<div class="meta">Mode: ${mode} | Tick: ${tick} | Hemisphere: ${hemisphere} | Bullets: ${meta.bullets || 0}</div>`;
    }

    messageDiv.innerHTML = `
        <div class="message-meta">${label}</div>
        <div class="text">${escapeHtml(text)}</div>
        ${metaHtml}
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function clearChat() {
    const messagesDiv = document.getElementById('chat-messages');
    if (!messagesDiv) return;
    messagesDiv.innerHTML = `
        <div class="message system">
            <div class="message-meta">System</div>
            <div class="text">BicameralMind ready. Ask a question to begin.</div>
        </div>
    `;
    const traceDiv = document.getElementById('chat-trace');
    if (traceDiv) {
        traceDiv.innerHTML = '<div class="context-item">No trace yet.</div>';
    }
    chatSuggestions = [];
    renderSuggestions();
    resetChatMetrics();
}

function renderChatTrace(details) {
    const traceDiv = document.getElementById('chat-trace');
    if (!traceDiv) return;

    if (!details || typeof details !== 'object') {
        traceDiv.innerHTML = '<div class="context-item">No trace available.</div>';
        return;
    }

    const left = details.left ? String(details.left) : '';
    const right = details.right ? String(details.right) : '';
    const rag = details.rag_context && typeof details.rag_context === 'object' ? details.rag_context : null;

    const blocks = [];

    if (rag) {
        const sources = Array.isArray(rag.sources) ? rag.sources.slice(0, 3).join('\n') : '';
        const ragText = [
            rag.answer ? `Answer:\n${rag.answer}` : '',
            sources ? `Sources:\n${sources}` : '',
            typeof rag.iterations === 'number' ? `Iterations: ${rag.iterations}` : ''
        ].filter(Boolean).join('\n\n');
        blocks.push(
            `<details class="trace-block" open><summary>RAG Context</summary><pre>${escapeHtml(ragText || '—')}</pre></details>`
        );
    }

    if (left) {
        blocks.push(
            `<details class="trace-block"><summary>Left Brain</summary><pre>${escapeHtml(left)}</pre></details>`
        );
    }

    if (right) {
        blocks.push(
            `<details class="trace-block"><summary>Right Brain</summary><pre>${escapeHtml(right)}</pre></details>`
        );
    }

    traceDiv.innerHTML = blocks.length ? blocks.join('') : '<div class="context-item">No trace yet.</div>';
}

function extractCandidateBullets(text) {
    if (!text) return [];
    const lines = String(text).split('\n').map((l) => l.trim()).filter(Boolean);
    const candidates = [];

    for (const line of lines) {
        if (candidates.length >= 6) break;
        const looksLikeBullet = /^([-*]\\s+|\\d+\\.\\s+|\\d+\\)\\s+)/.test(line);
        if (!looksLikeBullet) continue;
        const cleaned = line.replace(/^([-*]\\s+|\\d+\\.\\s+|\\d+\\)\\s+)/, '').trim();
        if (cleaned.length >= 12 && cleaned.length <= 220) {
            candidates.push(cleaned);
        }
    }

    if (candidates.length) return candidates;

    const raw = String(text).replace(/\\s+/g, ' ').trim();
    if (!raw) return [];
    const parts = raw.split(/(?<=[.!?])\\s+/).slice(0, 2);
    const fallback = parts.join(' ').trim();
    if (fallback.length >= 12) return [fallback.slice(0, 220)];
    return [];
}

function pushSuggestionsFromDetails(details) {
    if (!details || typeof details !== 'object') return;
    const left = details.left ? String(details.left) : '';
    const right = details.right ? String(details.right) : '';

    const newItems = [];
    for (const candidate of [...extractCandidateBullets(left), ...extractCandidateBullets(right)]) {
        if (!candidate) continue;
        newItems.push({
            id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
            text: candidate,
            confidence: 0.5,
            tags: []
        });
    }

    const seen = new Set(chatSuggestions.map((s) => s.text.toLowerCase().trim()));
    for (const item of newItems) {
        const key = item.text.toLowerCase().trim();
        if (seen.has(key)) continue;
        seen.add(key);
        chatSuggestions.unshift(item);
    }

    chatSuggestions = chatSuggestions.slice(0, 6);
    renderSuggestions();
}

function renderSuggestions() {
    const root = document.getElementById('chat-suggestions');
    if (!root) return;

    if (!chatSuggestions.length) {
        root.innerHTML = '<div class="context-item">No suggestions yet.</div>';
        return;
    }

    root.innerHTML = chatSuggestions.map((s) => {
        return `
            <div class="context-item" data-suggestion-id="${escapeHtml(s.id)}">
                <strong>${escapeHtml(s.text)}</strong>
                <div class="context-actions">
                    <button class="ghost-btn" data-action="approve">Send to Staging</button>
                    <button class="ghost-btn" data-action="edit">Edit</button>
                    <button class="ghost-btn" data-action="reject">Dismiss</button>
                </div>
            </div>
        `;
    }).join('');

    root.querySelectorAll('button').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const container = btn.closest('[data-suggestion-id]');
            const id = container ? container.dataset.suggestionId : null;
            if (!id) return;
            const idx = chatSuggestions.findIndex((s) => s.id === id);
            if (idx < 0) return;
            const item = chatSuggestions[idx];

            if (btn.dataset.action === 'reject') {
                chatSuggestions.splice(idx, 1);
                renderSuggestions();
                return;
            }

            if (btn.dataset.action === 'edit') {
                const updated = prompt('Edit bullet text', item.text);
                if (updated && updated.trim()) {
                    item.text = updated.trim();
                    renderSuggestions();
                }
                return;
            }

            if (btn.dataset.action === 'approve') {
                btn.disabled = true;
                try {
                    const resp = await fetch('/api/memory/staged', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: item.text, confidence: item.confidence, tags: item.tags })
                    });
                    const data = await resp.json();
                    if (!resp.ok || data.error) {
                        alert(`Failed to stage bullet: ${data.error || resp.status}`);
                        btn.disabled = false;
                        return;
                    }
                    chatSuggestions.splice(idx, 1);
                    renderSuggestions();
                    fetchStaged();
                } catch (error) {
                    alert(`Failed to stage bullet: ${error}`);
                    btn.disabled = false;
                }
            }
        });
    });
}

function addToolLog(data) {
    const logDiv = document.getElementById('mcp-log');
    if (!logDiv) return;

    if (logDiv.querySelector('.log-entry')?.textContent === 'No executions yet') {
        logDiv.innerHTML = '';
    }

    const entry = document.createElement('div');
    entry.className = `log-entry ${data.success ? 'success' : 'error'}`;
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `${timestamp}  ${data.tool}()  ${data.success ? 'SUCCESS' : 'FAILED'}  ${data.duration_ms}ms`;
    logDiv.insertBefore(entry, logDiv.firstChild);

    while (logDiv.children.length > 12) {
        logDiv.removeChild(logDiv.lastChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initTabs() {
    document.querySelectorAll('.tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            document.querySelectorAll('.tab-panel').forEach((panel) => {
                panel.classList.toggle('active', panel.id === `tab-${target}`);
            });
        });
    });
}

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    initTabs();
    connectWebSocket();
    fetchStatus();
    fetchMemoryStats();
    fetchMCPServers();
    fetchProcedures();
    fetchTools();
    fetchStaged();
    updateAnalytics();

    setInterval(fetchStatus, 5000);
    setInterval(fetchMemoryStats, 10000);
    setInterval(fetchMCPServers, 10000);

    const refreshBtn = document.getElementById('refresh-procedures');
    if (refreshBtn) refreshBtn.addEventListener('click', fetchProcedures);
    const refreshToolsBtn = document.getElementById('refresh-tools');
    if (refreshToolsBtn) refreshToolsBtn.addEventListener('click', fetchTools);
    const refreshStagedBtn = document.getElementById('refresh-staged');
    if (refreshStagedBtn) refreshStagedBtn.addEventListener('click', fetchStaged);

    const searchInput = document.getElementById('procedure-search');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase().trim();
            document.querySelectorAll('.procedure-card').forEach((card) => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }

    const addForm = document.getElementById('mcp-add-form');
    if (addForm) addForm.addEventListener('submit', addMCPServer);

    document.getElementById('send-btn').addEventListener('click', sendMessage);
    const clearBtn = document.getElementById('chat-clear');
    if (clearBtn) clearBtn.addEventListener('click', clearChat);

    const toolRunBtn = document.getElementById('tool-exec-run');
    if (toolRunBtn) toolRunBtn.addEventListener('click', runSelectedTool);

    const input = document.getElementById('message-input');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
