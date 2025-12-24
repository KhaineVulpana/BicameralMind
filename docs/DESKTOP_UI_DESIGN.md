# Desktop UI Design - BicameralMind

## Overview

Modern desktop application for the BicameralMind agentic AI system with three core components:
1. **Dashboard** - System monitoring and visualization
2. **Conversation Interface** - Natural interaction with the bicameral mind
3. **MCP Tool Integration & Monitoring** - Tool management and execution tracking

## Technology Stack

### Framework: Electron + React
- **Electron**: Cross-platform desktop framework (Windows, macOS, Linux)
- **React**: Modern UI component library
- **TypeScript**: Type-safe frontend development
- **Tailwind CSS**: Utility-first styling
- **Vite**: Fast build tool and dev server

### Backend Integration
- **Python FastAPI**: REST API backend (bridge to bicameral mind)
- **WebSocket**: Real-time updates for consciousness ticks, tool execution
- **Server-Sent Events (SSE)**: Streaming responses from LLM

### State Management
- **Zustand**: Lightweight state management
- **React Query**: Server state management and caching

### Visualization
- **Recharts**: Dashboard charts and graphs
- **React Flow**: Node-based MCP tool visualization
- **Framer Motion**: Smooth animations

## Architecture

```
Desktop UI (Electron + React)
|
+-- Main Process (Node.js)
|   |
|   +-- Window Management
|   +-- IPC Communication
|   +-- System Integration
|
+-- Renderer Process (React)
    |
    +-- Dashboard Component
    |   |-- System Status
    |   |-- Memory Metrics
    |   |-- Hemisphere Activity
    |   |-- Consciousness Ticks
    |
    +-- Conversation Interface
    |   |-- Chat Window
    |   |-- Input Controls
    |   |-- Context Display
    |   |-- Bullet Suggestions
    |
    +-- MCP Tool Monitor
        |-- Tool Registry
        |-- Execution Tracker
        |-- Tool Configuration
        |-- Learning Analytics

Backend API Server (FastAPI)
|
+-- REST Endpoints
|   |-- /api/chat
|   |-- /api/system/status
|   |-- /api/memory/*
|   |-- /api/mcp/*
|
+-- WebSocket Endpoints
|   |-- /ws/consciousness
|   |-- /ws/tools
|   |-- /ws/learning
|
+-- Bicameral Mind Integration
    |-- Left Brain Agent
    |-- Right Brain Agent
    |-- Meta Controller
    |-- Procedural Memory
    |-- MCP Client
```

## Component Specifications

### 1. Dashboard Component

#### Purpose
Real-time monitoring of the bicameral mind system state, memory usage, and learning progress.

#### Features

**System Status Panel**
- Current mode (exploit/explore/integrate)
- Consciousness tick rate
- Active hemisphere indicator
- LLM model and status
- System health indicators

**Memory Metrics**
- Bullet count by hemisphere (left/right/shared)
- Memory usage graphs (active/quarantined/deprecated)
- Recent promotions to shared memory
- Quality score distribution
- Deduplication and pruning statistics

**Hemisphere Activity**
- Left brain activity visualization
- Right brain activity visualization
- Pattern recognition vs mutation ratio
- Recent bullet retrievals
- Learning cycle status

**Consciousness Ticks**
- Real-time tick visualization
- Tick rate history graph
- Novelty signal indicators
- Reflection depth tracking
- Mode transition timeline

**Learning Analytics**
- Learning pipeline statistics
- Insight extraction rate
- Curation success rate
- Reflection depth distribution
- Outcome success/failure ratio

#### UI Layout

```
+----------------------------------------------------------+
| Dashboard                                    [Settings] |
+----------------------------------------------------------+
|                                                          |
|  +-------------------+  +----------------------------+   |
|  | System Status     |  | Memory Metrics            |   |
|  |                   |  |                            |   |
|  | Mode: EXPLORE     |  | Left:  243 bullets        |   |
|  | Tick: 0.75        |  | Right: 412 bullets        |   |
|  | Active: RIGHT     |  | Shared: 87 bullets        |   |
|  | Model: llama3:8b  |  |                            |   |
|  | Health: OK        |  | [Quality Distribution]    |   |
|  +-------------------+  |    Chart showing quality  |   |
|                         +----------------------------+   |
|                                                          |
|  +---------------------------------------------------+   |
|  | Hemisphere Activity                               |   |
|  |                                                   |   |
|  |  LEFT BRAIN              RIGHT BRAIN             |   |
|  |  [Activity Graph]        [Activity Graph]        |   |
|  |  Recent: validation      Recent: mutation        |   |
|  +---------------------------------------------------+   |
|                                                          |
|  +---------------------------------------------------+   |
|  | Consciousness Ticks                               |   |
|  |                                                   |   |
|  |  [Tick Rate Timeline Graph]                      |   |
|  |  Current: 0.75  |  Avg: 0.52  |  Peak: 0.95     |   |
|  +---------------------------------------------------+   |
|                                                          |
|  +---------------------------------------------------+   |
|  | Learning Analytics                                |   |
|  |                                                   |   |
|  |  Total Insights: 142                             |   |
|  |  Curated: 89 (62.7%)                             |   |
|  |  Reflection Depth: [Shallow: 40% | Med: 35% |    |   |
|  |                     Deep: 25%]                   |   |
|  +---------------------------------------------------+   |
+----------------------------------------------------------+
```

### 2. Conversation Interface

#### Purpose
Natural language interaction with the bicameral mind, with visibility into internal processing.

#### Features

**Chat Window**
- Message history with timestamps
- Differentiated messages (user, left brain, right brain, meta)
- Streaming responses with typing indicators
- Code syntax highlighting
- Markdown rendering
- Export conversation history

**Input Controls**
- Multi-line text input with autocomplete
- Attachment support (files, images for future multi-modal)
- Mode selector (let system decide / force left / force right)
- Temperature and token limit controls
- Clear/reset conversation

**Context Display**
- Retrieved bullets shown in sidebar
- Hemisphere source indicators
- Confidence scores
- Relevance highlighting
- Bullet usage tracking

**Bullet Suggestions**
- Real-time bullet creation suggestions
- Inline curation controls (approve/reject/edit)
- Learning feedback (mark helpful/harmful)
- Quick promotion to shared memory

**Conversation Analytics**
- Token usage counter
- Response time tracking
- Bullet retrieval count
- Learning events triggered
- Consciousness tick events

#### UI Layout

```
+----------------------------------------------------------+
| Conversation                    [Mode: Auto] [Settings] |
+----------------------------------------------------------+
|                                                          |
|  +--------------------------------+  +-----------------+ |
|  | Chat History                   |  | Context         | |
|  |                                |  |                 | |
|  | USER (10:23 AM)                |  | Retrieved:      | |
|  | How do I validate user input?  |  |                 | |
|  |                                |  | LEFT (conf 0.8) | |
|  | LEFT BRAIN (10:23 AM)          |  | "Always valid-  | |
|  | Based on my experience, you    |  | ate user input  | |
|  | should always validate input   |  | before proc..." | |
|  | before processing. Here's how: |  |                 | |
|  |                                |  | LEFT (conf 0.7) | |
|  | ```python                      |  | "Use type       | |
|  | def validate_input(data):      |  | hints for..."   | |
|  |   if not data:                 |  |                 | |
|  |     raise ValueError("Empty")  |  | RIGHT (conf 0.5)| |
|  | ```                            |  | "Consider edge  | |
|  |                                |  | cases like..."  | |
|  | [Tick: 0.45 | Novelty: Low]    |  |                 | |
|  |                                |  | SHARED (0.9)    | |
|  | RIGHT BRAIN (10:23 AM)         |  | "Try-except     | |
|  | Consider this edge case:       |  | blocks for..."  | |
|  | What if the input is None but  |  |                 | |
|  | still valid in your context?   |  | [5 bullets]     | |
|  |                                |  |                 | |
|  | [Tick: 0.72 | Novelty: Medium] |  +-----------------+ |
|  |                                |  |                 | |
|  | META CONTROLLER (10:23 AM)     |  | Analytics       | |
|  | High novelty detected.         |  |                 | |
|  | Triggering deep reflection...  |  | Tokens: 342     | |
|  |                                |  | Bullets: 5      | |
|  | [New Insight Suggested]        |  | Ticks: 2        | |
|  | "Validate based on context"    |  | Learning: 1     | |
|  |   [Approve] [Reject] [Edit]    |  |                 | |
|  +--------------------------------+  +-----------------+ |
|                                                          |
|  +---------------------------------------------------+   |
|  | > Type your message...                            |   |
|  |                                            [Send] |   |
|  +---------------------------------------------------+   |
+----------------------------------------------------------+
```

### 3. MCP Tool Integration & Monitoring

#### Purpose
Manage MCP servers, monitor tool execution, and track learning from tool usage.

#### Features

**Tool Registry**
- Connected MCP servers list
- Available tools by server
- Tool descriptions and schemas
- Connection status indicators
- Add/remove/configure servers

**Execution Tracker**
- Real-time tool execution log
- Execution parameters and results
- Success/failure indicators
- Execution time tracking
- Error messages and stack traces
- Retry controls

**Tool Configuration**
- Server connection settings
- Tool allowlist/blocklist management
- Timeout and retry configuration
- Learning settings per tool
- API key management (secure)

**Learning Analytics**
- Tool usage statistics
- Success rate by tool
- Bullets learned from tool usage
- Tool outcome correlation
- Novelty signals from tools
- Most valuable tools ranking

**Visual Tool Flow**
- Node-based tool execution visualization
- Tool dependencies and chains
- Data flow between tools
- Parallel execution tracking
- Tool composition builder

#### UI Layout

```
+----------------------------------------------------------+
| MCP Tools                              [Add Server] [?] |
+----------------------------------------------------------+
|                                                          |
|  +-------------------+  +----------------------------+   |
|  | Connected Servers |  | Tool Execution Log        |   |
|  |                   |  |                            |   |
|  | filesystem        |  | 10:45:23  read_file()     |   |
|  |   Status: OK      |  |   File: config.yaml       |   |
|  |   Tools: 5        |  |   Result: SUCCESS (45ms)  |   |
|  |   [Configure]     |  |   Learning: +1 bullet     |   |
|  |                   |  |                            |   |
|  | github            |  | 10:44:12  search_repos()  |   |
|  |   Status: ERROR   |  |   Query: "bicameral"      |   |
|  |   Tools: 0        |  |   Result: FAILED          |   |
|  |   [Reconnect]     |  |   Error: API limit        |   |
|  |                   |  |   Learning: +1 bullet     |   |
|  | brave_search      |  |                            |   |
|  |   Status: DISABLED|  | 10:43:01  write_file()    |   |
|  |   [Enable]        |  |   File: output.txt        |   |
|  +-------------------+  |   Result: SUCCESS (23ms)  |   |
|                         +----------------------------+   |
|                                                          |
|  +---------------------------------------------------+   |
|  | Available Tools                                   |   |
|  |                                                   |   |
|  |  filesystem.read_file       [Allowed] [Config]   |   |
|  |  filesystem.write_file      [Allowed] [Config]   |   |
|  |  filesystem.list_directory  [Allowed] [Config]   |   |
|  |  github.search_repos        [Blocked] [Config]   |   |
|  |  github.create_issue        [Blocked] [Config]   |   |
|  +---------------------------------------------------+   |
|                                                          |
|  +---------------------------------------------------+   |
|  | Tool Analytics                                    |   |
|  |                                                   |   |
|  |  Most Used:        read_file (47 calls)          |   |
|  |  Highest Success:  write_file (98.2%)            |   |
|  |  Most Learning:    search_repos (12 bullets)     |   |
|  |                                                   |   |
|  |  [Success Rate Chart]                            |   |
|  |  [Usage Timeline]                                |   |
|  +---------------------------------------------------+   |
+----------------------------------------------------------+
```

## Backend API Design

### REST API Endpoints

```python
# System Status
GET  /api/system/status
GET  /api/system/health
GET  /api/system/metrics

# Conversation
POST /api/chat/message
GET  /api/chat/history
DELETE /api/chat/clear

# Memory
GET  /api/memory/bullets?hemisphere={left|right|shared}
GET  /api/memory/stats
POST /api/memory/feedback  # Mark bullet helpful/harmful
GET  /api/memory/search?query={text}

# MCP Tools
GET  /api/mcp/servers
POST /api/mcp/servers/connect
DELETE /api/mcp/servers/{server_id}
GET  /api/mcp/tools
POST /api/mcp/tools/execute
GET  /api/mcp/executions
GET  /api/mcp/analytics

# Learning
GET  /api/learning/insights
GET  /api/learning/stats
POST /api/learning/curate  # Approve/reject insight
```

### WebSocket Events

```python
# Consciousness updates
ws://localhost:8000/ws/consciousness
Events:
  - tick: { rate: 0.75, mode: "explore", hemisphere: "right" }
  - mode_change: { from: "exploit", to: "explore" }
  - reflection: { depth: "deep", insights: 3 }

# Tool execution updates
ws://localhost:8000/ws/tools
Events:
  - tool_start: { tool: "read_file", params: {...} }
  - tool_progress: { tool: "read_file", progress: 0.5 }
  - tool_complete: { tool: "read_file", result: {...}, duration_ms: 45 }
  - tool_error: { tool: "read_file", error: "..." }

# Learning updates
ws://localhost:8000/ws/learning
Events:
  - insight_extracted: { insight: {...}, confidence: 0.8 }
  - bullet_created: { bullet: {...}, hemisphere: "left" }
  - bullet_promoted: { bullet_id: "...", to: "shared" }
  - curation_needed: { insight: {...} }
```

## Implementation Phases

### Phase A: Foundation (Week 1)
1. Set up Electron + React + TypeScript project
2. Create basic window and navigation
3. Implement FastAPI backend skeleton
4. Set up WebSocket communication
5. Create basic layout structure

### Phase B: Dashboard (Week 2)
1. Implement system status panel
2. Create memory metrics visualizations
3. Add hemisphere activity graphs
4. Implement consciousness tick tracking
5. Add learning analytics

### Phase C: Conversation Interface (Week 3)
1. Implement chat window and message display
2. Add input controls and mode selector
3. Create context sidebar with bullet display
4. Implement streaming responses
5. Add bullet suggestion and curation UI

### Phase D: MCP Tool Monitor (Week 4)
1. Implement server registry and management
2. Create tool execution log
3. Add tool configuration UI
4. Implement learning analytics
5. Add visual tool flow (optional)

### Phase E: Polish & Integration (Week 5)
1. Add animations and transitions
2. Implement error handling and retries
3. Add settings and preferences
4. Create user documentation
5. Performance optimization

## Project Structure

```
BicameralMind/
|
+-- desktop/                    # Desktop UI
|   |
|   +-- electron/               # Electron main process
|   |   +-- main.ts             # Entry point
|   |   +-- preload.ts          # IPC bridge
|   |   +-- window.ts           # Window management
|   |
|   +-- src/                    # React app
|   |   +-- components/
|   |   |   +-- Dashboard/
|   |   |   |   +-- SystemStatus.tsx
|   |   |   |   +-- MemoryMetrics.tsx
|   |   |   |   +-- HemisphereActivity.tsx
|   |   |   |   +-- ConsciousnessTicks.tsx
|   |   |   |   +-- LearningAnalytics.tsx
|   |   |   |
|   |   |   +-- Conversation/
|   |   |   |   +-- ChatWindow.tsx
|   |   |   |   +-- MessageList.tsx
|   |   |   |   +-- InputControls.tsx
|   |   |   |   +-- ContextSidebar.tsx
|   |   |   |   +-- BulletSuggestion.tsx
|   |   |   |
|   |   |   +-- MCPTools/
|   |   |       +-- ServerRegistry.tsx
|   |   |       +-- ExecutionLog.tsx
|   |   |       +-- ToolConfiguration.tsx
|   |   |       +-- AnalyticsDashboard.tsx
|   |   |       +-- ToolFlow.tsx
|   |   |
|   |   +-- hooks/
|   |   |   +-- useWebSocket.ts
|   |   |   +-- useChat.ts
|   |   |   +-- useMemory.ts
|   |   |   +-- useMCPTools.ts
|   |   |
|   |   +-- store/
|   |   |   +-- systemStore.ts
|   |   |   +-- chatStore.ts
|   |   |   +-- mcpStore.ts
|   |   |
|   |   +-- services/
|   |   |   +-- api.ts           # REST API client
|   |   |   +-- websocket.ts     # WebSocket client
|   |   |
|   |   +-- types/
|   |   |   +-- system.ts
|   |   |   +-- chat.ts
|   |   |   +-- mcp.ts
|   |   |
|   |   +-- App.tsx
|   |   +-- main.tsx
|   |
|   +-- package.json
|   +-- vite.config.ts
|   +-- tsconfig.json
|
+-- api/                        # FastAPI backend
|   +-- main.py                 # FastAPI app
|   +-- routers/
|   |   +-- chat.py
|   |   +-- memory.py
|   |   +-- mcp.py
|   |   +-- system.py
|   |
|   +-- websockets/
|   |   +-- consciousness.py
|   |   +-- tools.py
|   |   +-- learning.py
|   |
|   +-- services/
|   |   +-- bicameral_service.py  # Bridge to core system
|   |   +-- mcp_service.py
|   |
|   +-- models/
|       +-- requests.py
|       +-- responses.py
```

## Key Design Principles

1. **Real-time Updates**: Use WebSocket for live system state
2. **Transparency**: Show internal processing (bullets, ticks, reflection)
3. **Control**: Let user influence mode, parameters, and learning
4. **Feedback Loop**: Easy way to mark bullets helpful/harmful
5. **Non-blocking**: Don't freeze UI during LLM operations
6. **Offline-capable**: Works without internet (local LLM)
7. **Cross-platform**: Windows, macOS, Linux support
8. **Accessible**: Keyboard shortcuts, screen reader support

## Security Considerations

1. **API Keys**: Secure storage in system keychain
2. **Local-first**: All data stored locally
3. **No telemetry**: Complete privacy
4. **Sandboxing**: Electron security best practices
5. **Input validation**: Sanitize all user inputs
6. **File system access**: Limited to configured directories

## Performance Targets

- **Initial load**: < 2 seconds
- **Chat response**: < 100ms latency to start streaming
- **Dashboard refresh**: 60 FPS animations
- **Memory usage**: < 500MB RAM
- **Bullet search**: < 50ms for 1000+ bullets
- **WebSocket latency**: < 10ms

## Accessibility

- **Keyboard navigation**: Full keyboard support
- **Screen readers**: ARIA labels on all components
- **High contrast**: Support high contrast mode
- **Text scaling**: Respect system font size
- **Focus indicators**: Clear focus states

## Future Enhancements

1. **Multi-modal**: Image and audio support
2. **Plugins**: Extension system for custom components
3. **Themes**: Dark/light/custom themes
4. **Export**: Save conversations as markdown/PDF
5. **Collaboration**: Share bullets between instances
6. **Mobile companion**: Mobile app for monitoring
7. **Voice input**: Speech-to-text support
8. **Visualizations**: 3D memory space visualization

## Next Steps

1. Review and approve design
2. Set up development environment
3. Create project scaffolding
4. Implement Phase A (Foundation)
5. Begin Phase B (Dashboard)
