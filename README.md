# Bicameral Mind

A local AI system implementing an A2A "bicameral brain" architecture with consciousness ticks, agentic RAG, and multi-modal capabilities.

## Architecture

```
┌─────────────────────────────────────┐
│      Meta-Controller (Ticker)       │
│   Consciousness / Mode Switching    │
└────────┬────────────────────┬───────┘
         │                    │
    ┌────▼─────┐         ┌───▼──────┐
    │   LEFT   │◄───────►│  RIGHT   │
    │  BRAIN   │         │  BRAIN   │
    └────┬─────┘         └────┬─────┘
         │                    │
         │   Pattern Match    │  Pattern Break
         │   Recognition      │  Mutation
         │   Replication      │  Exploration
         │                    │
         └────────┬───────────┘
                  │
           ┌──────▼───────┐
           │ Agentic RAG  │
           │   +  MCP     │
           └──────────────┘
```

### Components

- **Left Brain**: Pattern recognition & replication (exploit mode)
- **Right Brain**: Pattern breaking & mutation (explore mode)
- **Meta-Controller**: Consciousness tick system, mode switching
 - **Agentic RAG**: Iterative retrieval with self‑checking
 - **MCP Integration (Model Context Protocol)**: Enables the
   bicameral system to call external tools and services (e.g. CRM
   connectors like HubSpot) via the Model Context Protocol.  MCP
   servers are configured in ``config/config.yaml`` under the
   ``mcp`` section.  When ``enabled`` is true the system will attempt
   to connect to these servers.  The meta‑cognitive planner is a
   separate internal mechanism (not related to MCP) that coordinates
   complex tasks; it remains available for future extensions.

### Running on consumer hardware

The default configuration included in this repository targets large
models (e.g. Qwen 2.5 14B) and multi‑GPU systems.  To run the
framework on a single desktop PC with an RTX 4080 (16 GB VRAM) and
32 GB of system RAM, adjust the configuration as follows:

* **Choose a smaller model:** Edit ``config/config.yaml`` and set
  ``model.name`` to a 7–10 billion parameter model such as
  ``llama3:8b`` (recommended), ``qwen2.5:7b`` or another model that
  supports 4‑bit quantisation.  These fit within 16 GB VRAM when
  quantised via **Ollama** or **LocalAI**.
* **Reduce token limits:** Lower ``max_tokens`` to 2048 or less.
  Large token windows increase memory usage; smaller values improve
  stability on consumer GPUs.
* **Keep retrieval lightweight:** The default RAG configuration
  (``rag.top_k=5`` and ``rag.max_iterations=5``) works on desktop
  hardware.  If you encounter memory pressure, you can lower these
  values.
* **Use quantisation:** Ensure your model runner is configured to
  use 4‑bit (int4) weights.  This dramatically reduces VRAM usage
  with minimal impact on quality.

After making these changes, the Bicameral Mind system should run
comfortably on a single 16 GB GPU without requiring multiple cards.

## Installation

### Prerequisites

1. **Python 3.10+**
2. **Ollama** ([install here](https://ollama.ai))

### Setup

```bash
# 1. Clone repository
git clone <your-repo-url> Bicameral_Mind
cd Bicameral_Mind

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull recommended model
ollama pull qwen2.5:14b
# Or: ollama pull llama3.1:8b

# 4. Configure (optional - edit config/config.yaml)

# 5. Run
python main.py
```

## Quick Start

### Interactive Mode

```bash
python main.py
```

Commands:
- Type queries normally
- `/status` - View consciousness state
- `/history` - View conversation history
- `/quit` - Exit

### Programmatic Usage

```python
from core.bicameral_mind import BicameralMind
import asyncio

async def main():
    mind = BicameralMind("config/config.yaml")
    await mind.start()
    
    result = await mind.process("Explain quantum computing")
    print(result["output"])
    
    # Add knowledge
    mind.add_knowledge(["Document content here..."])
    
    # Get consciousness metrics
    state = mind.get_consciousness_state()
    print(f"Mode: {state['mode']}, Tick Rate: {state['tick_rate']}")
    
    mind.stop()

asyncio.run(main())
```

## Configuration

Edit `config/config.yaml`:

```yaml
model:
  name: "qwen2.5:14b"  # Your Ollama model
  temperature: 0.7

bicameral:
  tick_interval: 0.5  # Consciousness tick frequency
  tick_threshold:
    entropy: 0.6      # Uncertainty threshold
    conflict: 0.5     # Brain conflict threshold
    novelty: 0.7      # Pattern novelty threshold

rag:
  enabled: true
  retrieval_mode: "agentic"  # or "single"
  max_iterations: 5
```

## How It Works

### Bicameral Processing

1. **Meta-Controller ticks** periodically (default: 0.5s)
2. Evaluates **entropy, conflict, novelty**
3. Switches mode:
   - **EXPLOIT** → Left brain (pattern matching)
   - **EXPLORE** → Right brain (exploration)
   - **INTEGRATE** → Both brains (synthesis)

### Consciousness Metrics

- **Tick Rate**: Frequency of reevaluation (consciousness frequency)
- **Mode**: Current cognitive mode
- **Active Hemisphere**: Which brain is dominant

### Agentic RAG

Unlike single-pass RAG:
1. Retrieves documents
2. Assesses coverage
3. Refines query if gaps exist
4. Retrieves again (up to max iterations)
5. Synthesizes final answer

## Roadmap

- [x] Core bicameral architecture
- [x] Consciousness tick system
- [x] Agentic RAG
- [ ] MCP integration (active)
- [ ] Multi-modal (vision, audio)
- [ ] GAN-based generative learning
- [ ] Long-term memory consolidation

## Project Structure

```
Bicameral_Mind/
├── core/
│   ├── bicameral_mind.py      # Main orchestrator
│   ├── base_agent.py           # Agent base class
│   ├── left_brain/
│   │   └── agent.py            # Pattern recognition
│   ├── right_brain/
│   │   └── agent.py            # Pattern mutation
│   └── meta_controller/
│       └── controller.py       # Consciousness ticks
├── integrations/
│   ├── rag/
│   │   └── agentic_rag.py     # RAG system
│   ├── mcp/
│   │   └── mcp_integration.py # MCP template
│   └── tools/
├── config/
│   └── config.yaml             # Configuration
├── data/
│   ├── knowledge_base/
│   ├── vector_store/
│   └── memory/
├── main.py                     # Entry point
└── requirements.txt
```

## License

MIT

## Contributing

This is a research/experimental project. PRs welcome.

## Notes

The "bicameral mind" architecture and consciousness tick system are proprietary implementations. Standard integrations (RAG, MCP, LLM clients) use existing open-source tools.
