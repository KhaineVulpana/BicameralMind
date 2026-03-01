import * as vscode from 'vscode';
import * as crypto from 'crypto';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

type DetailsPayload = {
    left?: string;
    right?: string;
    rag_context?: {
        answer?: string;
        sources?: string[];
        iterations?: number;
    };
    retrieved_bullets?: Array<{
        id: string;
        text: string;
        side: string;
        score?: number;
        tags?: string[];
    }>;
    tool_trace?: Array<{
        tool_call_id?: string;
        tool?: string;
        success?: boolean;
        duration_ms?: number;
        error?: string | null;
    }>;
};

type ContextItem = {
    id: string;
    kind: 'file' | 'folder';
    path: string;
};

type ContextState = {
    items: ContextItem[];
    includeWorkspace: boolean;
    includeOpenFiles: boolean;
};

class BicameralMindViewProvider implements vscode.WebviewViewProvider {
    private view?: vscode.WebviewView;
    private activeStreamAbort?: AbortController;
    private output = vscode.window.createOutputChannel('BicameralMind');
    private currentSessionId?: string;
    private contextItems: ContextItem[] = [];
    private includeWorkspace = true;
    private includeOpenFiles = true;
    private contextLoaded = false;

    constructor(private readonly context: vscode.ExtensionContext) {}

    resolveWebviewView(webviewView: vscode.WebviewView): void {
        this.view = webviewView;
        const webview = webviewView.webview;
        webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.joinPath(this.context.extensionUri, 'media'),
            ],
        };
        webview.html = this.getWebviewHtml(webview);

        webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'sendMessage':
                    await this.handleSendMessage(message.text, message.mode);
                    break;
                case 'requestContext':
                    this.postContextState();
                    break;
                case 'contextAddFile':
                    await this.handleContextAdd('file');
                    break;
                case 'contextAddFolder':
                    await this.handleContextAdd('folder');
                    break;
                case 'contextRemove':
                    this.removeContextItem(String(message.id || ''));
                    break;
                case 'contextClear':
                    this.clearContextItems();
                    break;
                case 'contextToggleWorkspace':
                    this.setIncludeWorkspace(Boolean(message.value));
                    break;
                case 'contextToggleOpenFiles':
                    this.setIncludeOpenFiles(Boolean(message.value));
                    break;
                case 'requestModels':
                    await this.handleRequestModels();
                    break;
                case 'setModels':
                    await this.handleSetModels(message.slow, message.fast);
                    break;
                case 'cancelStream':
                    this.activeStreamAbort?.abort();
                    this.activeStreamAbort = undefined;
                    if (this.currentSessionId) {
                        this.sendCancel(this.currentSessionId).catch(() => undefined);
                    }
                    break;
                case 'resetSession':
                    await this.resetSession();
                    break;
                default:
                    break;
            }
        });

        this.ensureContextState();
        this.postConfig();
        this.postContextState();
        this.handleRequestModels().catch(() => undefined);
    }

    private postConfig(): void {
        const config = vscode.workspace.getConfiguration('bicameralmind');
        this.postMessage({
            type: 'config',
            streamResponses: config.get<boolean>('streamResponses', true),
        });
    }

    private ensureContextState(): void {
        if (this.contextLoaded) {
            return;
        }
        const projectId = this.getProjectId();
        const key = this.getContextStateKey(projectId);
        const stored = this.context.workspaceState.get<ContextState>(key);
        const config = vscode.workspace.getConfiguration('bicameralmind');
        this.contextItems = stored?.items || [];
        this.includeWorkspace = stored?.includeWorkspace ?? config.get<boolean>('contextIncludeWorkspace', true);
        this.includeOpenFiles = stored?.includeOpenFiles ?? config.get<boolean>('contextIncludeOpenFiles', true);
        this.contextLoaded = true;
    }

    private getContextStateKey(projectId: string): string {
        return `context:${projectId}`;
    }

    private persistContextState(): void {
        const projectId = this.getProjectId();
        const state: ContextState = {
            items: this.contextItems,
            includeWorkspace: this.includeWorkspace,
            includeOpenFiles: this.includeOpenFiles,
        };
        void this.context.workspaceState.update(this.getContextStateKey(projectId), state);
    }

    private postContextState(): void {
        this.ensureContextState();
        const root = this.getWorkspaceRoot();
        const items = this.contextItems.map((item) => ({
            id: item.id,
            kind: item.kind,
            label: this.toDisplayPath(item.path, root),
            detail: item.kind === 'folder' ? 'Folder' : 'File',
        }));
        this.postMessage({
            type: 'context',
            items,
            includeWorkspace: this.includeWorkspace,
            includeOpenFiles: this.includeOpenFiles,
            workspaceRoot: root || '',
        });
    }

    private setIncludeWorkspace(value: boolean): void {
        this.ensureContextState();
        this.includeWorkspace = value;
        this.persistContextState();
        this.postContextState();
    }

    private setIncludeOpenFiles(value: boolean): void {
        this.ensureContextState();
        this.includeOpenFiles = value;
        this.persistContextState();
        this.postContextState();
    }

    private async handleContextAdd(kind: 'file' | 'folder'): Promise<void> {
        this.ensureContextState();
        const uris = await vscode.window.showOpenDialog({
            canSelectFiles: kind === 'file',
            canSelectFolders: kind === 'folder',
            canSelectMany: true,
            openLabel: kind === 'file' ? 'Add file' : 'Add folder',
        });
        if (!uris || !uris.length) {
            return;
        }
        let changed = false;
        for (const uri of uris) {
            const fsPath = uri.fsPath;
            if (!fsPath) {
                continue;
            }
            const id = this.hashContextItem(kind, fsPath);
            if (this.contextItems.some((item) => item.id === id)) {
                continue;
            }
            this.contextItems.push({ id, kind, path: fsPath });
            changed = true;
        }
        if (changed) {
            this.contextItems.sort((a, b) => a.path.localeCompare(b.path));
            this.persistContextState();
            this.postContextState();
        }
    }

    private removeContextItem(id: string): void {
        if (!id) {
            return;
        }
        const next = this.contextItems.filter((item) => item.id !== id);
        if (next.length === this.contextItems.length) {
            return;
        }
        this.contextItems = next;
        this.persistContextState();
        this.postContextState();
    }

    private clearContextItems(): void {
        if (!this.contextItems.length) {
            return;
        }
        this.contextItems = [];
        this.persistContextState();
        this.postContextState();
    }

    private hashContextItem(kind: string, fsPath: string): string {
        return crypto.createHash('sha1').update(`${kind}:${fsPath}`).digest('hex').slice(0, 12);
    }

    private toDisplayPath(fsPath: string, root: string): string {
        if (root) {
            const rel = path.relative(root, fsPath);
            if (rel && !rel.startsWith('..') && !path.isAbsolute(rel)) {
                return rel;
            }
        }
        return fsPath;
    }

    private async handleSendMessage(text: string, mode?: string): Promise<void> {
        const trimmed = (text || '').trim();
        if (!trimmed) {
            return;
        }
        const config = vscode.workspace.getConfiguration('bicameralmind');
        const stream = config.get<boolean>('streamResponses', true);
        const sessionId = await this.ensureSession();
        if (!sessionId) {
            this.postMessage({ type: 'error', message: 'No session available.' });
            return;
        }
        this.currentSessionId = sessionId;

        this.postMessage({ type: 'stream-start' });

        let contextPayload: Record<string, any> | null = null;
        let contextUpdated = false;
        try {
            contextPayload = await this.buildClientContext();
            const contextToSend = contextPayload || {};
            await this.sendContextUpdate(sessionId, contextToSend);
            contextUpdated = true;
        } catch (error: any) {
            this.output.appendLine(`[context] failed: ${String(error)}`);
        }

        if (stream) {
            await this.streamMessage(sessionId, trimmed);
            return;
        }

        try {
            const payload = {
                project_id: this.getProjectId(),
                text: trimmed,
                mode: mode || undefined,
                client_context: contextUpdated ? undefined : contextPayload || undefined,
            };
            const response = await this.backendRequest(
                `/v1/sessions/${sessionId}/messages`,
                {
                    method: 'POST',
                    body: JSON.stringify(payload),
                }
            );
            const data = await response.json();
            this.postMessage({ type: 'final', value: data.final || '' });
            this.postMessage({ type: 'details', value: data.details || {} });
        } catch (error: any) {
            this.postMessage({ type: 'error', message: String(error) });
        }
    }

    private getContextConfig(): {
        maxFiles: number;
        maxOpenFiles: number;
        maxFileBytes: number;
        maxTotalBytes: number;
        excludeGlob?: string;
    } {
        const config = vscode.workspace.getConfiguration('bicameralmind');
        const maxFiles = Math.max(1, Number(config.get<number>('contextMaxFiles', 200)) || 200);
        const maxOpenFiles = Math.max(0, Number(config.get<number>('contextMaxOpenFiles', 4)) || 0);
        const maxFileBytes = Math.max(256, Number(config.get<number>('contextMaxFileBytes', 12000)) || 12000);
        const maxTotalBytes = Math.max(maxFileBytes, Number(config.get<number>('contextMaxTotalBytes', 60000)) || 60000);
        const excludeGlobRaw = String(
            config.get<string>(
                'contextExcludeGlob',
                '**/{node_modules,.git,dist,build,out,venv,.venv,__pycache__}/**'
            ) || ''
        ).trim();
        return {
            maxFiles,
            maxOpenFiles,
            maxFileBytes,
            maxTotalBytes,
            excludeGlob: excludeGlobRaw || undefined,
        };
    }

    private async buildClientContext(): Promise<Record<string, any> | null> {
        this.ensureContextState();
        const root = this.getWorkspaceRoot();
        const cfg = this.getContextConfig();
        const context: Record<string, any> = {};
        let remaining = cfg.maxTotalBytes;

        if (root) {
            context.workspace_root = root;
        }

        if (this.includeWorkspace && root) {
            const files = await vscode.workspace.findFiles('**/*', cfg.excludeGlob, cfg.maxFiles);
            context.workspace_files = files.map((uri) => this.toDisplayPath(uri.fsPath, root));
            if (files.length >= cfg.maxFiles) {
                context.workspace_files_truncated = true;
            }
        }

        if (this.includeOpenFiles && cfg.maxOpenFiles > 0 && remaining > 0) {
            const openDocs = this.collectOpenDocuments(cfg.maxOpenFiles);
            for (const doc of openDocs) {
                const payload = this.consumeText(doc.getText(), cfg.maxFileBytes, remaining);
                if (!payload) {
                    continue;
                }
                remaining -= payload.used;
                if (!context.open_files) {
                    context.open_files = [];
                }
                context.open_files.push({
                    path: this.toDisplayPath(doc.uri.fsPath, root),
                    language: doc.languageId,
                    content: payload.text,
                    truncated: payload.truncated,
                });
                if (remaining <= 0) {
                    break;
                }
            }
        }

        if (this.contextItems.length) {
            const selected: any[] = [];
            for (const item of this.contextItems) {
                if (item.kind === 'file' && remaining > 0) {
                    const payload = await this.readFileForContext(item.path, cfg.maxFileBytes, remaining);
                    if (!payload) {
                        continue;
                    }
                    remaining -= payload.used;
                    selected.push({
                        kind: 'file',
                        path: this.toDisplayPath(item.path, root),
                        content: payload.text,
                        truncated: payload.truncated,
                    });
                    if (remaining <= 0) {
                        break;
                    }
                } else if (item.kind === 'folder') {
                    const listing = await this.listFilesForContext(item.path, cfg.maxFiles, cfg.excludeGlob);
                    selected.push({
                        kind: 'folder',
                        path: this.toDisplayPath(item.path, root),
                        files: listing.files,
                        truncated: listing.truncated,
                    });
                }
            }
            if (selected.length) {
                context.selected = selected;
            }
        }

        const hasData = Boolean(
            context.workspace_files ||
                (Array.isArray(context.open_files) && context.open_files.length) ||
                (Array.isArray(context.selected) && context.selected.length)
        );
        if (!hasData) {
            return null;
        }
        context.meta = {
            max_files: cfg.maxFiles,
            max_file_bytes: cfg.maxFileBytes,
            max_total_bytes: cfg.maxTotalBytes,
            include_workspace: this.includeWorkspace,
            include_open_files: this.includeOpenFiles,
        };
        return context;
    }

    private async sendContextUpdate(sessionId: string, contextPayload: Record<string, any>): Promise<void> {
        await this.backendRequest(`/v1/sessions/${sessionId}/context`, {
            method: 'POST',
            body: JSON.stringify({
                project_id: this.getProjectId(),
                context: contextPayload,
            }),
        });
    }

    private collectOpenDocuments(limit: number): vscode.TextDocument[] {
        if (limit <= 0) {
            return [];
        }
        const docs: vscode.TextDocument[] = [];
        const seen = new Set<string>();
        const active = vscode.window.activeTextEditor;
        const editors = vscode.window.visibleTextEditors;
        const ordered = active ? [active, ...editors.filter((e) => e !== active)] : editors;

        for (const editor of ordered) {
            const doc = editor.document;
            if (doc.uri.scheme !== 'file') {
                continue;
            }
            const fsPath = doc.uri.fsPath;
            if (seen.has(fsPath)) {
                continue;
            }
            seen.add(fsPath);
            docs.push(doc);
            if (docs.length >= limit) {
                break;
            }
        }
        return docs;
    }

    private consumeText(
        content: string,
        maxBytes: number,
        remaining: number
    ): { text: string; truncated: boolean; used: number } | null {
        if (!content || remaining <= 0 || maxBytes <= 0) {
            return null;
        }
        const allowed = Math.min(maxBytes, remaining);
        const text = content.slice(0, allowed);
        if (!text || text.includes('\u0000')) {
            return null;
        }
        return {
            text,
            truncated: content.length > text.length,
            used: text.length,
        };
    }

    private async readFileForContext(
        fsPath: string,
        maxBytes: number,
        remaining: number
    ): Promise<{ text: string; truncated: boolean; used: number } | null> {
        if (remaining <= 0 || maxBytes <= 0) {
            return null;
        }
        try {
            const uri = vscode.Uri.file(fsPath);
            const data = await vscode.workspace.fs.readFile(uri);
            const allowed = Math.min(maxBytes, remaining);
            const slice = data.slice(0, allowed);
            const text = Buffer.from(slice).toString('utf8');
            if (!text || text.includes('\u0000')) {
                return null;
            }
            return {
                text,
                truncated: data.length > allowed,
                used: slice.length,
            };
        } catch (error: any) {
            this.output.appendLine(`[context] failed to read ${fsPath}: ${String(error)}`);
            return null;
        }
    }

    private async listFilesForContext(
        folderPath: string,
        maxFiles: number,
        excludeGlob?: string
    ): Promise<{ files: string[]; truncated: boolean }> {
        try {
            const pattern = new vscode.RelativePattern(folderPath, '**/*');
            const files = await vscode.workspace.findFiles(pattern, excludeGlob, maxFiles);
            const root = this.getWorkspaceRoot();
            return {
                files: files.map((uri) => this.toDisplayPath(uri.fsPath, root)),
                truncated: files.length >= maxFiles,
            };
        } catch (error: any) {
            this.output.appendLine(`[context] failed to list ${folderPath}: ${String(error)}`);
            return { files: [], truncated: false };
        }
    }

    private async streamMessage(sessionId: string, text: string): Promise<void> {
        const projectId = this.getProjectId();
        const url = this.makeBackendUrl(
            `/v1/sessions/${sessionId}/events?project_id=${encodeURIComponent(projectId)}&text=${encodeURIComponent(text)}`
        );
        const headers = this.buildAuthHeaders();

        for (let attempt = 0; attempt < 3; attempt++) {
            const controller = new AbortController();
            this.activeStreamAbort = controller;

            try {
                const response = await fetch(url, {
                    headers,
                    signal: controller.signal,
                });
                if (!response.ok || !response.body) {
                    throw new Error(`Stream failed: ${response.status}`);
                }

                await this.consumeSse(response.body, (event, data) => {
                    if (event === 'token') {
                        this.postMessage({ type: 'token', value: String(data) });
                    } else if (event === 'tool_call') {
                        this.handleToolCall(sessionId, data).catch((error) => {
                            this.postMessage({ type: 'error', message: String(error) });
                        });
                    } else if (event === 'final') {
                        this.postMessage({ type: 'final', value: String(data || '') });
                    } else if (event === 'details') {
                        this.postMessage({ type: 'details', value: data || {} });
                    } else if (event === 'error') {
                        const message = typeof data === 'string' ? data : (data?.error || 'Unknown error');
                        this.postMessage({ type: 'error', message });
                    }
                });
                return;
            } catch (error: any) {
                if (error?.name === 'AbortError') {
                    return;
                }
                if (attempt >= 2) {
                    this.postMessage({ type: 'error', message: String(error) });
                    return;
                }
                await this.delay(300 * Math.pow(2, attempt));
            } finally {
                this.activeStreamAbort = undefined;
            }
        }
    }

    private async consumeSse(
        stream: ReadableStream<Uint8Array>,
        onEvent: (event: string, data: any) => void
    ): Promise<void> {
        const reader = stream.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            let idx = buffer.indexOf('\n\n');
            while (idx >= 0) {
                const raw = buffer.slice(0, idx);
                buffer = buffer.slice(idx + 2);
                const { event, data } = this.parseSseChunk(raw);
                if (event && data !== undefined) {
                    onEvent(event, data);
                }
                idx = buffer.indexOf('\n\n');
            }
        }
    }

    private parseSseChunk(chunk: string): { event: string; data: any } {
        const lines = chunk.split(/\r?\n/);
        let event = 'message';
        const dataLines: string[] = [];

        for (const line of lines) {
            if (line.startsWith('event:')) {
                event = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
                dataLines.push(line.slice(5).trim());
            }
        }

        const dataStr = dataLines.join('\n');
        if (!dataStr) {
            return { event, data: '' };
        }
        try {
            return { event, data: JSON.parse(dataStr) };
        } catch {
            return { event, data: dataStr };
        }
    }

    private async delay(ms: number): Promise<void> {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    private async handleRequestModels(): Promise<void> {
        try {
            const [modelsResp, activeResp] = await Promise.all([
                this.backendRequest('/v1/models/ollama'),
                this.backendRequest(`/v1/models/active?project_id=${encodeURIComponent(this.getProjectId())}`),
            ]);
            const models = await modelsResp.json();
            const active = await activeResp.json();
            this.postMessage({
                type: 'models',
                models: models.models || [],
                active,
            });
        } catch (error: any) {
            this.postMessage({ type: 'error', message: String(error) });
        }
    }

    private async handleToolCall(sessionId: string, toolCall: any): Promise<void> {
        const name = String(toolCall?.name || '');
        const toolCallId = String(toolCall?.tool_call_id || '');
        const args = (toolCall?.args && typeof toolCall.args === 'object') ? toolCall.args : {};
        const risk = String(toolCall?.risk || 'low').toLowerCase();

        this.output.appendLine(`[tool_call] ${name} (${toolCallId}) risk=${risk}`);

        const config = vscode.workspace.getConfiguration('bicameralmind');
        const allowHighRisk = config.get<boolean>('allowHighRiskTools', false);
        if (risk === 'high' && !allowHighRisk) {
            await this.postToolResult(sessionId, toolCallId, false, 'High-risk tool blocked by settings');
            return;
        }

        const confirmed = await this.confirmToolRun(name, args, risk === 'high');
        if (!confirmed) {
            await this.postToolResult(sessionId, toolCallId, false, 'User rejected tool execution');
            return;
        }

        const result = await this.executeTool(name, args);
        await this.postToolResult(sessionId, toolCallId, result.success, result.output, result.artifacts);
    }

    private async confirmToolRun(name: string, args: any, highRisk: boolean): Promise<boolean> {
        const message = `Allow tool "${name}" to run?`;
        const detail = highRisk ? 'High-risk action.' : 'Low-risk action.';
        const choice = await vscode.window.showWarningMessage(message, { detail, modal: highRisk }, 'Allow', 'Cancel');
        return choice === 'Allow';
    }

    private async postToolResult(
        sessionId: string,
        toolCallId: string,
        success: boolean,
        output: any,
        artifacts?: any
    ): Promise<void> {
        try {
            const payload = {
                session_id: sessionId,
                tool_call_id: toolCallId,
                success,
                output,
                artifacts: artifacts || {},
            };
            await this.backendRequest('/v1/tool_results', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            this.output.appendLine(`[tool_result] ${toolCallId} success=${success}`);
        } catch (error: any) {
            this.output.appendLine(`[tool_result] failed: ${String(error)}`);
        }
    }

    private async executeTool(name: string, args: any): Promise<{ success: boolean; output: any; artifacts?: any }> {
        try {
            if (name === 'workspace.readFile' || name === 'read_file') {
                const uri = this.resolvePath(args.path);
                const data = await vscode.workspace.fs.readFile(uri);
                return { success: true, output: data.toString() };
            }
            if (name === 'workspace.listFiles') {
                const pattern = String(args.pattern || '**/*');
                const limit = Number(args.limit || 50);
                const files = await vscode.workspace.findFiles(pattern, args.exclude || undefined, limit);
                return { success: true, output: files.map((f) => f.fsPath) };
            }
            if (name === 'workspace.search') {
                const query = String(args.query || '');
                const limit = Number(args.limit || 20);
                const results: any[] = [];
                const finder = (vscode.workspace as any).findTextInFiles;
                if (!finder) {
                    return { success: false, output: 'findTextInFiles not available in this VS Code version' };
                }
                await finder.call(
                    vscode.workspace,
                    { pattern: query },
                    { include: args.include || undefined, exclude: args.exclude || undefined, maxResults: limit },
                    (result: any) => {
                        if (results.length >= limit) return;
                        results.push({
                            path: result.uri.fsPath,
                            preview: result.preview?.text || '',
                        });
                    }
                );
                return { success: true, output: results };
            }
            if (name === 'git.status') {
                const cwd = this.getWorkspaceRoot();
                const { stdout } = await execAsync('git status --porcelain', { cwd });
                return { success: true, output: stdout.trim() };
            }
            if (name === 'git.diff') {
                const cwd = this.getWorkspaceRoot();
                const { stdout } = await execAsync('git diff', { cwd, maxBuffer: 5_000_000 });
                return { success: true, output: stdout };
            }
            if (name === 'workspace.applyEdits') {
                return await this.previewAndApplyEdit(args);
            }
            if (name === 'terminal.run') {
                const command = String(args.command || '');
                if (!command) {
                    return { success: false, output: 'Missing command' };
                }
                const cwd = this.getWorkspaceRoot();
                const { stdout, stderr } = await execAsync(command, { cwd, maxBuffer: 5_000_000 });
                return { success: true, output: stdout || stderr };
            }
            if (name === 'local.open_path') {
                const uri = this.resolvePath(args.path);
                const stat = await vscode.workspace.fs.stat(uri);
                if (stat.type & vscode.FileType.Directory) {
                    await vscode.commands.executeCommand('vscode.openFolder', uri, true);
                } else {
                    await vscode.window.showTextDocument(uri);
                }
                return { success: true, output: `Opened ${uri.fsPath}` };
            }
            return { success: false, output: `Unsupported tool: ${name}` };
        } catch (error: any) {
            return { success: false, output: String(error) };
        }
    }

    private async previewAndApplyEdit(args: any): Promise<{ success: boolean; output: any; artifacts?: any }> {
        const relPath = String(args.path || '');
        const content = String(args.content || '');
        if (!relPath) {
            return { success: false, output: 'Missing path for applyEdits' };
        }
        const uri = this.resolvePath(relPath);
        const doc = await vscode.workspace.openTextDocument(uri);
        const newDoc = await vscode.workspace.openTextDocument({ content, language: doc.languageId });
        await vscode.commands.executeCommand('vscode.diff', uri, newDoc.uri, `Proposed edit: ${path.basename(relPath)}`);

        const choice = await vscode.window.showWarningMessage(
            `Apply edits to ${relPath}?`,
            { modal: true },
            'Apply',
            'Cancel'
        );
        if (choice !== 'Apply') {
            return { success: false, output: 'User cancelled edit' };
        }

        const edit = new vscode.WorkspaceEdit();
        const lastLine = doc.lineAt(doc.lineCount - 1);
        const range = new vscode.Range(0, 0, doc.lineCount - 1, lastLine.text.length);
        edit.replace(uri, range, content);
        await vscode.workspace.applyEdit(edit);
        return { success: true, output: `Applied edit to ${relPath}`, artifacts: { path: relPath } };
    }

    private async handleSetModels(slow: string, fast: string): Promise<void> {
        try {
            const payload = {
                project_id: this.getProjectId(),
                slow,
                fast: fast || undefined,
            };
            const resp = await this.backendRequest('/v1/models/active', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok || data.error) {
                throw new Error(data.error || `HTTP ${resp.status}`);
            }
        } catch (error: any) {
            this.postMessage({ type: 'error', message: String(error) });
        }
    }

    private async ensureSession(): Promise<string | null> {
        const projectId = this.getProjectId();
        const key = `session:${projectId}`;
        const existing = this.context.workspaceState.get<string>(key);
        if (existing) {
            return existing;
        }
        try {
            const resp = await this.backendRequest('/v1/sessions', {
                method: 'POST',
                body: JSON.stringify({ project_id: projectId }),
            });
            const data = await resp.json();
            if (!resp.ok || !data.session_id) {
                throw new Error(data.error || `HTTP ${resp.status}`);
            }
            await this.context.workspaceState.update(key, data.session_id);
            return data.session_id;
        } catch (error) {
            this.postMessage({ type: 'error', message: String(error) });
            return null;
        }
    }

    async resetSession(): Promise<void> {
        const projectId = this.getProjectId();
        const key = `session:${projectId}`;
        await this.context.workspaceState.update(key, undefined);
        this.postMessage({ type: 'session-reset' });
    }

    async reconnect(): Promise<void> {
        this.postConfig();
        this.postContextState();
        await this.handleRequestModels();
        this.postMessage({ type: 'status', message: 'Reconnected.' });
    }

    private async sendCancel(sessionId: string): Promise<void> {
        try {
            await this.backendRequest(`/v1/sessions/${sessionId}/cancel`, {
                method: 'POST',
            });
        } catch (error: any) {
            this.output.appendLine(`[cancel] failed: ${String(error)}`);
        }
    }

    private getProjectId(): string {
        const workspace = vscode.workspace.workspaceFolders?.[0];
        if (!workspace) {
            return 'default';
        }
        const key = `projectId:${workspace.uri.toString()}`;
        let projectId = this.context.workspaceState.get<string>(key);
        if (!projectId) {
            const hash = crypto.createHash('sha1').update(workspace.uri.fsPath).digest('hex');
            projectId = hash.slice(0, 12);
            this.context.workspaceState.update(key, projectId);
        }
        return projectId;
    }

    private getWorkspaceRoot(): string {
        const workspace = vscode.workspace.workspaceFolders?.[0];
        return workspace ? workspace.uri.fsPath : process.cwd();
    }

    private resolvePath(inputPath: string): vscode.Uri {
        if (!inputPath) {
            throw new Error('Missing path');
        }
        if (path.isAbsolute(inputPath)) {
            return vscode.Uri.file(inputPath);
        }
        const root = this.getWorkspaceRoot();
        return vscode.Uri.file(path.join(root, inputPath));
    }

    private getBackendUrl(): string {
        const config = vscode.workspace.getConfiguration('bicameralmind');
        const url = config.get<string>('backendUrl', 'http://localhost:8000');
        return url.replace(/\/+$/, '');
    }

    private buildAuthHeaders(): Record<string, string> {
        const config = vscode.workspace.getConfiguration('bicameralmind');
        const token = String(config.get<string>('authToken', '') || '').trim();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        return headers;
    }

    private makeBackendUrl(pathname: string): string {
        const base = this.getBackendUrl();
        return `${base}${pathname}`;
    }

    private async backendRequest(
        pathname: string,
        init: RequestInit = {}
    ): Promise<Response> {
        const url = this.makeBackendUrl(pathname);
        const headers = this.buildAuthHeaders();
        const response = await fetch(url, {
            ...init,
            headers: {
                ...headers,
                ...(init.headers || {}),
            },
        });
        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Backend error ${response.status}: ${text}`);
        }
        return response;
    }

    private postMessage(payload: any): void {
        this.view?.webview.postMessage(payload);
    }

    private getWebviewHtml(webview: vscode.Webview): string {
        const mediaUri = vscode.Uri.joinPath(this.context.extensionUri, 'media');
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaUri, 'main.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaUri, 'styles.css'));
        const nonce = crypto.randomBytes(16).toString('hex');

        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
  <link rel="stylesheet" href="${styleUri}">
  <title>BicameralMind</title>
</head>
<body>
  <div class="app">
    <header>
      <h1>BicameralMind</h1>
      <div class="controls">
        <label>Mode
          <select id="mode-select">
            <option value="auto">Auto</option>
            <option value="left">Left</option>
            <option value="right">Right</option>
          </select>
        </label>
        <label>Slow Model <select id="model-slow"></select></label>
        <label>Fast Model <select id="model-fast"></select></label>
        <button id="refresh-models" class="ghost">Refresh</button>
        <button id="reset-session" class="ghost">Reset Session</button>
      </div>
    </header>
    <nav class="tabs">
      <button class="tab active" data-tab="chat">Chat</button>
      <button class="tab" data-tab="trace">Trace</button>
      <button class="tab" data-tab="context">Context</button>
    </nav>
    <main>
      <section id="chat-panel" class="panel active">
        <div id="messages" class="messages"></div>
        <div class="composer">
          <textarea id="message-input" rows="3" placeholder="Message BicameralMind..."></textarea>
          <div class="composer-actions">
            <button id="send-btn" class="primary">Send</button>
            <button id="stop-btn" class="ghost">Stop</button>
          </div>
        </div>
      </section>
      <section id="trace-panel" class="panel">
        <div class="trace-block">
          <h2>RAG</h2>
          <pre id="trace-rag">No trace yet.</pre>
        </div>
        <div class="trace-grid">
          <div class="trace-block">
            <h2>Left Hemisphere</h2>
            <pre id="trace-left">No trace yet.</pre>
          </div>
          <div class="trace-block">
            <h2>Right Hemisphere</h2>
            <pre id="trace-right">No trace yet.</pre>
          </div>
        </div>
        <div class="trace-block">
          <h2>Retrieved Bullets</h2>
          <div id="trace-bullets">No bullets yet.</div>
        </div>
        <div class="trace-block">
          <h2>Tool Trace</h2>
          <div id="trace-tools">No tool activity.</div>
        </div>
      </section>
      <section id="context-panel" class="panel">
        <div class="context-controls">
          <label><input type="checkbox" id="context-include-workspace"> Include workspace overview</label>
          <label><input type="checkbox" id="context-include-open"> Include open files</label>
        </div>
        <div class="context-actions">
          <button id="context-add-file" class="ghost">Add file</button>
          <button id="context-add-folder" class="ghost">Add folder</button>
          <button id="context-clear" class="ghost">Clear</button>
        </div>
        <div id="context-list" class="context-list">No context items yet.</div>
        <div class="context-hint">Context is sent with each message.</div>
      </section>
    </main>
    <footer id="status">Idle</footer>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}

export function activate(context: vscode.ExtensionContext) {
    const provider = new BicameralMindViewProvider(context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('bicameralmind.chatView', provider)
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bicameralmind.openChat', () => {
            vscode.commands.executeCommand('workbench.view.extension.bicameralmind');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bicameralmind.resetSession', async () => {
            await provider.resetSession();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bicameralmind.reconnect', async () => {
            await provider.reconnect();
        })
    );
}

export function deactivate() {}
