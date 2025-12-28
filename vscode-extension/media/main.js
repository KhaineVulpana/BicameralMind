const vscode = acquireVsCodeApi();

let streamResponses = true;
let activeAssistant = null;

const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const stopBtn = document.getElementById('stop-btn');
const statusEl = document.getElementById('status');
const modelSlow = document.getElementById('model-slow');
const modelFast = document.getElementById('model-fast');
const modeSelect = document.getElementById('mode-select');
const contextIncludeWorkspace = document.getElementById('context-include-workspace');
const contextIncludeOpen = document.getElementById('context-include-open');
const contextAddFile = document.getElementById('context-add-file');
const contextAddFolder = document.getElementById('context-add-folder');
const contextClear = document.getElementById('context-clear');
const contextList = document.getElementById('context-list');

function setStatus(text) {
  if (statusEl) statusEl.textContent = text;
}

function addMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  const label = document.createElement('div');
  label.className = 'label';
  label.textContent = role === 'user' ? 'You' : 'Assistant';
  const body = document.createElement('div');
  body.className = 'body';
  body.textContent = text || '';
  wrapper.appendChild(label);
  wrapper.appendChild(body);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return body;
}

function startAssistantMessage() {
  activeAssistant = addMessage('assistant', '');
}

function appendToken(token) {
  if (!activeAssistant) startAssistantMessage();
  activeAssistant.textContent += token;
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderTrace(details) {
  const leftEl = document.getElementById('trace-left');
  const rightEl = document.getElementById('trace-right');
  const ragEl = document.getElementById('trace-rag');
  const bulletsEl = document.getElementById('trace-bullets');
  const toolsEl = document.getElementById('trace-tools');

  if (leftEl) leftEl.textContent = details?.left || 'No trace yet.';
  if (rightEl) rightEl.textContent = details?.right || 'No trace yet.';

  if (ragEl) {
    const rag = details?.rag_context;
    if (rag) {
      const parts = [];
      if (rag.answer) parts.push(`Answer:\n${rag.answer}`);
      if (Array.isArray(rag.sources) && rag.sources.length) {
        parts.push(`Sources:\n${rag.sources.join('\n')}`);
      }
      if (typeof rag.iterations === 'number') {
        parts.push(`Iterations: ${rag.iterations}`);
      }
      ragEl.textContent = parts.join('\n\n') || 'No trace yet.';
    } else {
      ragEl.textContent = 'No trace yet.';
    }
  }

  if (bulletsEl) {
    const bullets = Array.isArray(details?.retrieved_bullets) ? details.retrieved_bullets : [];
    if (!bullets.length) {
      bulletsEl.textContent = 'No bullets yet.';
    } else {
      bulletsEl.innerHTML = bullets.map((b) => {
        const score = Number.isFinite(Number(b.score)) ? Number(b.score).toFixed(2) : '-';
        return `<div class="bullet"><strong>[${b.id?.slice(0, 10) || ''}]</strong> (${b.side || '-'}) score=${score}<br>${escapeHtml(b.text || '')}</div>`;
      }).join('');
    }
  }

  if (toolsEl) {
    const tools = Array.isArray(details?.tool_trace) ? details.tool_trace : [];
    if (!tools.length) {
      toolsEl.textContent = 'No tool activity.';
    } else {
      toolsEl.innerHTML = tools.map((t) => {
        const ok = t.success ? 'OK' : 'FAIL';
        const name = t.tool || t.tool_call_id || 'tool';
        return `<div class="bullet">${escapeHtml(name)} - ${ok}</div>`;
      }).join('');
    }
  }
}

function renderContext(items) {
  if (!contextList) return;
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    contextList.innerHTML = '<div class="context-empty">No context items yet.</div>';
    return;
  }
  contextList.innerHTML = list.map((item) => {
    const label = escapeHtml(item.label || item.path || '');
    const detail = escapeHtml(item.detail || item.kind || '');
    return `<div class="context-item">
      <div class="meta">
        <div class="label">${label}</div>
        <div class="detail">${detail}</div>
      </div>
      <button class="ghost" data-id="${item.id}">Remove</button>
    </div>`;
  }).join('');
  contextList.querySelectorAll('button[data-id]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      vscode.postMessage({ type: 'contextRemove', id });
    });
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function sendMessage() {
  const text = (inputEl.value || '').trim();
  if (!text) return;

  addMessage('user', text);
  inputEl.value = '';
  startAssistantMessage();
  setStatus('Thinking...');

  vscode.postMessage({ type: 'sendMessage', text, mode: modeSelect?.value || 'auto' });
}

sendBtn?.addEventListener('click', sendMessage);
inputEl?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

stopBtn?.addEventListener('click', () => {
  vscode.postMessage({ type: 'cancelStream' });
  setStatus('Stopped.');
});

document.getElementById('refresh-models')?.addEventListener('click', () => {
  vscode.postMessage({ type: 'requestModels' });
});

document.getElementById('reset-session')?.addEventListener('click', () => {
  vscode.postMessage({ type: 'resetSession' });
});

contextAddFile?.addEventListener('click', () => {
  vscode.postMessage({ type: 'contextAddFile' });
});

contextAddFolder?.addEventListener('click', () => {
  vscode.postMessage({ type: 'contextAddFolder' });
});

contextClear?.addEventListener('click', () => {
  vscode.postMessage({ type: 'contextClear' });
});

contextIncludeWorkspace?.addEventListener('change', () => {
  vscode.postMessage({ type: 'contextToggleWorkspace', value: contextIncludeWorkspace.checked });
});

contextIncludeOpen?.addEventListener('change', () => {
  vscode.postMessage({ type: 'contextToggleOpenFiles', value: contextIncludeOpen.checked });
});

modelSlow?.addEventListener('change', () => {
  vscode.postMessage({ type: 'setModels', slow: modelSlow.value, fast: modelFast?.value || '' });
});

modelFast?.addEventListener('change', () => {
  vscode.postMessage({ type: 'setModels', slow: modelSlow?.value || '', fast: modelFast.value });
});

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
    tab.classList.add('active');
    const target = tab.dataset.tab;
    document.querySelectorAll('.panel').forEach((panel) => {
      panel.classList.toggle('active', panel.id === `${target}-panel`);
    });
  });
});

window.addEventListener('message', (event) => {
  const msg = event.data;
  if (!msg || !msg.type) return;

  if (msg.type === 'config') {
    streamResponses = Boolean(msg.streamResponses);
  }
  if (msg.type === 'models') {
    const models = Array.isArray(msg.models) ? msg.models : [];
    const active = msg.active || {};
    modelSlow.innerHTML = models.map((m) => `<option value="${m.name}">${m.name}</option>`).join('');
    modelFast.innerHTML = `<option value="">(same as slow)</option>` + models.map((m) => `<option value="${m.name}">${m.name}</option>`).join('');
    if (active.slow) modelSlow.value = active.slow;
    if (active.fast) modelFast.value = active.fast;
  }
  if (msg.type === 'context') {
    if (contextIncludeWorkspace) {
      contextIncludeWorkspace.checked = Boolean(msg.includeWorkspace);
    }
    if (contextIncludeOpen) {
      contextIncludeOpen.checked = Boolean(msg.includeOpenFiles);
    }
    renderContext(msg.items || []);
  }
  if (msg.type === 'stream-start') {
    setStatus('Streaming...');
  }
  if (msg.type === 'token') {
    appendToken(msg.value || '');
  }
  if (msg.type === 'final') {
    if (!activeAssistant) startAssistantMessage();
    activeAssistant.textContent = msg.value || '';
    activeAssistant = null;
    setStatus('Idle');
  }
  if (msg.type === 'details') {
    renderTrace(msg.value || {});
  }
  if (msg.type === 'error') {
    addMessage('assistant', `Error: ${msg.message || 'Unknown error'}`);
    activeAssistant = null;
    setStatus('Error');
  }
  if (msg.type === 'status') {
    setStatus(msg.message || 'Idle');
  }
  if (msg.type === 'session-reset') {
    messagesEl.innerHTML = '';
    renderTrace({});
  }
});

vscode.postMessage({ type: 'requestModels' });
vscode.postMessage({ type: 'requestContext' });
