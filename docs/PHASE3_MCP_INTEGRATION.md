# Phase 3: MCP Integration - Implementation Guide

Last Updated: December 24, 2025

## Overview

**Phase 3** implements Model Context Protocol (MCP) integration to enable automatic learning from external tool usage. This connects the bicameral mind to real-world tools and services, allowing it to learn from actual tool outcomes.

**Key Insight**: Tool executions provide natural, high-quality outcome signals for learning. Every tool call is a learning opportunity.

---

## What is MCP?

**Model Context Protocol (MCP)** is a standard protocol for connecting AI systems to external tools, data sources, and services.

### MCP Enables:
- Tool discovery and registration
- Structured tool execution
- Success/failure outcome signals
- Integration with external systems
- Standardized tool interfaces

### Why MCP for Learning?

1. **Automatic Outcome Signals**: Tool success/failure is objective
2. **Real-World Validation**: Tools interact with actual systems
3. **Rich Context**: Tool parameters and results provide evidence
4. **Natural Learning**: Every tool call is a teaching moment
5. **Scalable**: Works with any MCP-compatible tool

---

## Architecture

```
User Query
    |
    v
Bicameral Mind
    |
    v
Retrieve Bullets (tool usage heuristics)
    |
    v
Execute with MCP Tools
    |
    +---> MCP Integration
    |       |
    |       +---> Tool Discovery
    |       +---> Tool Execution
    |       +---> Result Capture
    |
    v
Generate ExecutionTrace
    |
    v
Calculate Novelty (automatic ticks)
    |
    v
Learn from Trace (LearningPipeline)
    |
    v
Update Bullets (outcome-based)
    |
    v
Promote to Shared (if validated)
```

---

## Components

### 1. MCP Client (`mcp_client.py`)

Core MCP protocol implementation.

**Responsibilities**:
- Connect to MCP servers
- Discover available tools
- Maintain server connections
- Handle connection errors
- Provide tool registry

**Key Classes**:
- `MCPClient`: Main MCP client implementation
- `MCPServer`: Represents a connected server
- `MCPTool`: Tool metadata and schema

### 2. Tool Executor (`tool_executor.py`)

Safe tool execution with comprehensive logging.

**Responsibilities**:
- Execute tools with parameter validation
- Capture execution results
- Measure execution time
- Handle tool errors gracefully
- Generate execution metadata

**Key Features**:
- Parameter validation
- Timeout handling
- Error recovery
- Detailed logging
- Result normalization

### 3. Trace Generator (`mcp_trace_generator.py`)

Converts tool executions into ExecutionTraces.

**Responsibilities**:
- Map tool results to traces
- Extract success/failure signals
- Identify which bullets were used
- Capture error context
- Generate trace metadata

**Trace Components**:
- Task description
- Hemisphere (left/right)
- Execution steps
- Bullets used
- Success/failure
- Error messages
- Tool call details
- Confidence scores

### 4. Learning Integration (`mcp_learning_integration.py`)

Connects tool execution to the learning pipeline.

**Responsibilities**:
- Orchestrate tool execution -> learning flow
- Calculate novelty from tool outcomes
- Trigger reflection when appropriate
- Update bullet scores
- Track learning metrics

**Learning Flow**:
1. Execute tool (with bullets)
2. Generate trace
3. Calculate novelty/ticks
4. Reflect (if novelty high)
5. Extract insights
6. Curate bullets
7. Record outcomes
8. Promote successful bullets

---

## Implementation Details

### Tool Execution with Learning

```python
from integrations.mcp import MCPLearningIntegration
from core.memory import ProceduralMemory
from core.meta_controller import MetaController

# Initialize
mcp_learning = MCPLearningIntegration(
    mcp_client=mcp_client,
    procedural_memory=memory,
    meta_controller=meta_controller,
    learning_pipeline=pipeline
)

# Execute tool with automatic learning
result = await mcp_learning.execute_with_learning(
    tool_name="search_crm",
    parameters={"query": "active leads"},
    hemisphere="left",
    expected_success=True  # For novelty calculation
)

# Result includes:
# - tool_result: Actual tool output
# - trace: ExecutionTrace generated
# - learning_result: LearningResult from pipeline
# - tick_rate: Calculated novelty
# - bullets_updated: Which bullets were scored
```

### Retrieving Tool-Specific Bullets

```python
# Get bullets relevant to a specific tool
bullets, ids = memory.retrieve(
    query=f"Using {tool_name} tool successfully",
    side=Hemisphere.LEFT,
    k=8,
    filter_tags=[tool_name, "tool_usage"]
)

# Use bullets to inform tool parameters
# Execute tool
# Record outcome for those specific bullets
memory.record_outcome(ids, helpful=(tool_result.success))
```

### Automatic Trace Generation

```python
from integrations.mcp import generate_trace_from_tool_result

trace = generate_trace_from_tool_result(
    tool_name="query_database",
    tool_params={"table": "users", "limit": 10},
    tool_result=result,
    bullets_used=bullet_ids,
    hemisphere="left",
    confidence=0.8
)

# Trace includes:
# - Task: "Execute query_database with params {...}"
# - Steps: Individual operations within tool
# - Success: Based on tool result
# - Error: Any error messages
# - Tools called: [tool_name]
# - Confidence: Agent confidence before execution
```

---

## Configuration

### MCP Server Configuration

Add to `config/config.yaml`:

```yaml
mcp:
  enabled: true
  connection_timeout: 30  # seconds
  tool_timeout: 60  # seconds per tool call
  max_retries: 3

  # Tool filtering
  allowed_tools: []  # Empty = allow all
  blocked_tools: []  # Explicit blocklist

  # Learning settings
  auto_learn: true  # Automatically learn from tool usage
  learn_on_success: true
  learn_on_failure: true

  # Servers
  servers:
    # Filesystem tools
    - name: "filesystem"
      type: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
      enabled: true

    # GitHub integration
    - name: "github"
      type: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
      enabled: false  # Requires token

    # Web search
    - name: "brave_search"
      type: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-brave-search"]
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"
      enabled: false  # Requires API key
```

### Procedural Memory Configuration

```yaml
procedural_memory:
  enabled: true

  # Tool-specific bullet tagging
  auto_tag_tools: true  # Automatically tag bullets with tool names

  # Tool-specific collections (optional)
  tool_collections:
    enabled: false  # Start with shared collections
    # When enabled, creates separate collections per tool
    # e.g., procedural_left_filesystem, procedural_left_github
```

---

## Usage Examples

### Basic Tool Execution

```python
from integrations.mcp import MCPClient

# Initialize client
client = MCPClient(config)
await client.connect()

# Discover tools
tools = await client.list_tools()
print(f"Available tools: {[t.name for t in tools]}")

# Execute tool
result = await client.call_tool(
    tool_name="read_file",
    parameters={"path": "./data/example.txt"}
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")
```

### Tool Execution with Learning

```python
from integrations.mcp import MCPLearningIntegration

# Initialize learning integration
mcp_learning = MCPLearningIntegration(
    mcp_client=client,
    procedural_memory=memory,
    meta_controller=meta_controller,
    learning_pipeline=pipeline
)

# Execute with automatic learning
result = await mcp_learning.execute_with_learning(
    tool_name="search_files",
    parameters={"pattern": "*.py", "directory": "./core"},
    hemisphere="left",
    expected_success=True
)

# System automatically:
# 1. Retrieved relevant bullets
# 2. Executed tool
# 3. Generated trace
# 4. Calculated novelty
# 5. Reflected (if needed)
# 6. Updated bullet scores
# 7. Promoted successful patterns

print(f"Tool output: {result.tool_result.output}")
print(f"Tick rate: {result.tick_rate:.2f}")
print(f"Bullets updated: {len(result.bullets_updated)}")
print(f"Insights extracted: {result.learning_result.insights_extracted}")
```

### Agent Integration

```python
class LeftBrain(BaseAgent):
    def __init__(self, config, llm, meta_controller, procedural_memory, mcp_client):
        super().__init__(config, llm, "LeftBrain")
        self.procedural_memory = procedural_memory
        self.meta_controller = meta_controller
        self.mcp_learning = MCPLearningIntegration(
            mcp_client=mcp_client,
            procedural_memory=procedural_memory,
            meta_controller=meta_controller,
            learning_pipeline=LearningPipeline(procedural_memory, llm)
        )

    async def process(self, message: Message) -> Message:
        # Determine if we need to use tools
        if self._should_use_tools(message):
            # Get available tools
            tools = await self.mcp_learning.get_available_tools()

            # Select appropriate tool (LLM-guided)
            tool_name, params = await self._select_tool(message, tools)

            # Execute with learning
            result = await self.mcp_learning.execute_with_learning(
                tool_name=tool_name,
                parameters=params,
                hemisphere="left",
                expected_success=True
            )

            return Message(
                content=result.tool_result.output,
                metadata={"learned": True, "tick_rate": result.tick_rate}
            )

        # Regular processing without tools
        return await self._regular_process(message)
```

---

## Learning from Tools

### What Gets Learned?

**Tool Usage Heuristics**:
- "When searching for X, use parameter Y"
- "Tool Z often fails with input pattern W"
- "Always validate parameter A before calling tool B"
- "Tool C works better than tool D for task E"

**Tool Failure Patterns**:
- "API timeout when query exceeds 100 items"
- "File not found errors occur if path not absolute"
- "Authentication fails if token expired"

**Tool Success Patterns**:
- "Rate limiting avoided by batching requests"
- "Best results from search when query specific"
- "File operations faster with absolute paths"

### Learning Triggers

**High Novelty (Deep Reflection)**:
- Tool fails unexpectedly
- Tool succeeds despite low confidence
- New tool used for first time
- Tool error never seen before

**Medium Novelty (Medium Reflection)**:
- Tool succeeds but with low confidence
- Tool partially succeeds
- Tool warning messages
- Slow execution time

**Low Novelty (Shallow/None)**:
- Tool succeeds as expected
- Routine operation
- High confidence execution
- Fast completion

---

## Error Handling

### Connection Errors

```python
try:
    await client.connect()
except MCPConnectionError as e:
    logger.error(f"Failed to connect to MCP server: {e}")
    # Fallback to non-tool execution
```

### Tool Execution Errors

```python
result = await executor.execute_tool(
    tool_name="api_call",
    parameters=params,
    timeout=30
)

if not result.success:
    # Error is captured in trace
    # Learning pipeline will extract insights
    # Bullets will be updated with harmful signal
    logger.warning(f"Tool failed: {result.error}")
```

### Learning Errors

```python
try:
    learning_result = await mcp_learning.execute_with_learning(...)
except LearningPipelineError as e:
    # Tool still executed, learning failed
    logger.error(f"Learning failed: {e}")
    # Tool result is still available
    return learning_result.tool_result
```

---

## Testing

### Unit Tests

```bash
python -m pytest tests/test_mcp_client.py
python -m pytest tests/test_tool_executor.py
python -m pytest tests/test_mcp_trace_generator.py
```

### Integration Tests

```bash
python tests/test_mcp_integration.py
```

Tests:
- MCP server connection
- Tool discovery
- Tool execution
- Trace generation
- Learning integration
- Error handling
- Timeout handling

### Example MCP Server

```bash
# Run test MCP server
python examples/test_mcp_server.py
```

Provides mock tools for testing:
- `echo`: Simple echo tool
- `fail_always`: Tool that always fails
- `slow_tool`: Tool with configurable delay
- `random_success`: Tool with random outcomes

---

## Performance Considerations

### Connection Pooling

MCP clients maintain persistent connections:
- Reduces connection overhead
- Faster tool execution
- Automatic reconnection on failure

### Caching

Tool schemas are cached:
- Avoid repeated discovery calls
- Faster tool validation
- Reduced network overhead

### Async Execution

All MCP operations are async:
- Non-blocking tool calls
- Parallel tool execution (future)
- Efficient resource usage

### Learning Overhead

Learning adds minimal overhead:
- Trace generation: <10ms
- Novelty calculation: <5ms
- Reflection: Only when novelty high
- Bullet updates: Async, non-blocking

---

## Monitoring & Debugging

### Logging

MCP operations are logged at multiple levels:

```python
# INFO: Connection status, tool calls
logger.info(f"Connected to MCP server: {server_name}")
logger.info(f"Executing tool: {tool_name}")

# WARNING: Failures, retries
logger.warning(f"Tool execution failed: {error}")
logger.warning(f"Retrying connection (attempt {retry}/3)")

# ERROR: Critical failures
logger.error(f"MCP server unreachable: {server_name}")
logger.error(f"Learning pipeline error: {error}")

# DEBUG: Detailed execution
logger.debug(f"Tool parameters: {params}")
logger.debug(f"Tool result: {result}")
logger.debug(f"Trace generated: {trace.trace_id}")
```

### Metrics

Track MCP usage:

```python
stats = mcp_learning.get_stats()
print(f"Total tool calls: {stats['total_calls']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average execution time: {stats['avg_execution_time']:.2f}s")
print(f"Bullets learned: {stats['bullets_created']}")
print(f"Bullets promoted: {stats['bullets_promoted']}")
```

---

## Security Considerations

### Tool Allowlisting

Restrict which tools can be used:

```yaml
mcp:
  allowed_tools: ["read_file", "search_files", "query_db"]
  blocked_tools: ["delete_file", "modify_system"]
```

### Parameter Validation

All tool parameters are validated:
- Type checking
- Range validation
- Pattern matching
- Schema compliance

### Sandboxing

Tools should run in sandboxed environments:
- Filesystem restrictions
- Network restrictions
- Resource limits
- Timeout enforcement

### Credential Management

Never hardcode credentials:

```yaml
# BAD
env:
  API_KEY: "sk_1234567890"

# GOOD
env:
  API_KEY: "${API_KEY}"  # From environment variable
```

---

## Troubleshooting

### MCP Server Won't Connect

1. Check server is running
2. Verify connection parameters
3. Check network/firewall
4. Review server logs
5. Test with simple client

### Tool Execution Fails

1. Validate parameters match schema
2. Check tool is available
3. Verify credentials/permissions
4. Review timeout settings
5. Check server logs

### Learning Not Working

1. Verify `auto_learn: true`
2. Check procedural memory enabled
3. Review learning pipeline config
4. Check novelty detection
5. Review reflection settings

### Performance Issues

1. Check connection pooling enabled
2. Review timeout settings
3. Monitor server response times
4. Check learning overhead
5. Profile execution

---

## Next Steps (Future Enhancements)

### Phase 3.1: Advanced Tool Management
- Tool composition (chaining)
- Parallel tool execution
- Tool result caching
- Smart tool selection

### Phase 3.2: Tool-Specific Optimization
- Per-tool bullet collections
- Tool-specific reflection
- Tool effectiveness metrics
- Tool recommendation system

### Phase 3.3: Multi-Agent Tool Coordination
- Tool allocation between hemispheres
- Collaborative tool usage
- Tool conflict resolution
- Shared tool learning

---

## Files Created/Modified

**Created**:
- `integrations/mcp/mcp_client.py` - MCP protocol client
- `integrations/mcp/tool_executor.py` - Safe tool execution
- `integrations/mcp/mcp_trace_generator.py` - Trace generation
- `integrations/mcp/mcp_learning_integration.py` - Learning integration
- `integrations/mcp/exceptions.py` - MCP-specific exceptions
- `tests/test_mcp_client.py` - MCP client tests
- `tests/test_mcp_integration.py` - Integration tests
- `examples/mcp_usage_example.py` - Usage examples
- `examples/test_mcp_server.py` - Test server

**Modified**:
- `integrations/mcp/__init__.py` - Exports
- `config/config.yaml` - MCP configuration
- `core/left_brain/agent.py` - MCP integration
- `core/right_brain/agent.py` - MCP integration

**Documentation**:
- `docs/PHASE3_MCP_INTEGRATION.md` - This document

---

## Critical Design Principles

### Tool Execution
- ALWAYS validate parameters before execution
- ALWAYS capture success/failure signals
- ALWAYS generate traces from tool calls
- NEVER skip error handling
- NEVER execute without timeout

### Learning Integration
- Tool outcomes MUST update bullet scores
- High novelty MUST trigger reflection
- Successful patterns MUST be promoted
- Failed patterns MUST be learned from
- Learning MUST NOT block tool execution

### Safety
- ALWAYS use allowlists for sensitive operations
- ALWAYS validate credentials
- ALWAYS enforce timeouts
- NEVER trust tool input
- NEVER expose credentials in logs

---

**Status**: Phase 3 Implementation Guide Complete

**Next**: Implement MCP client and tool executor
