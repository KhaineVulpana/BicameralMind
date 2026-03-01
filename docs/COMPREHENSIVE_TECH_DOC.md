# Bicameral Mind: A Dual-Hemisphere Cognitive Architecture for AI

## Table of Contents
1. [Overview](#overview)
2. [What Makes This Different](#what-makes-this-different)
3. [Core Concepts](#core-concepts)
4. [Technical Architecture](#technical-architecture)
5. [How It Works](#how-it-works)
6. [Implementation Details](#implementation-details)
7. [Getting Started](#getting-started)
8. [Phase Completion Status](#phase-completion-status)
9. [Configuration](#configuration)
10. [Development Roadmap](#development-roadmap)

---

## Overview

**Bicameral Mind** is a local, offline-capable AI system that implements a dual-hemisphere cognitive architecture inspired by human brain lateralization. Unlike traditional AI systems that rely on single-agent reasoning or weight-based training, this system uses **two specialized agents** with complementary cognitive styles that learn from experience through **Agentic Context Engineering (ACE)** rather than gradient descent.

### What This System Is

- **A cognitive architecture** with two specialized reasoning agents (left/right hemispheres)
- **A learning system** that improves through experience without model fine-tuning
- **An agentic platform** that integrates external tools via Model Context Protocol (MCP)
- **A local-first solution** designed to run entirely on consumer hardware

### What This System Is NOT

-  A standard chatbot or conversational AI
-  A simple RAG (Retrieval-Augmented Generation) system
-  A reinforcement learning or fine-tuning framework
-  Cloud-dependent or requiring API calls

---

## What Makes This Different

### 1. **Bicameral Cognition**

The system implements **two distinct cognitive agents** that both recognize AND generate patterns, but focus on different aspects of pattern information:

| Hemisphere | Pattern Recognition | Pattern Generation | Core Question |
|------------|-------------------|-------------------|---------------|
| **Left Brain** | Detects when expected structure IS present<br>Confirms regularity and repetition<br>"This matches model X" | Replicates known patterns<br>Applies established rules<br>Extends patterns conservatively | "What IS a pattern?"<br>"What has reliably worked?" |
| **Right Brain** | Detects when expected structure FAILS<br>Notices anomalies, gaps, contradictions<br>"Something broke / doesn't fit" | Mutates existing patterns<br>Creates novel recombinations<br>Introduces intentional variation | "What is NOT a pattern?"<br>"What if the pattern is wrong?" |

**Critical Design Principle:**

Both hemispheres ask questions AND provide answers. The difference is:
- **Left** asks binary, decidable questions ("Is this true or false?", "Does this meet constraint X?")
- **Right** asks open-ended, exploratory questions ("What else could this be?", "What assumptions are we making?")

**Cognitive Operating Modes:**

**Left Hemisphere - Pattern Continuity (Exploit)**
- **Recognition:** Confirms that known patterns are present
- **Generation:** Replicates proven strategies
- **Stopping Rule:** Stops when a decision boundary is crossed (binary choice made)
- **Output Style:** Deterministic, precise, convergent
- **Typical Behaviors:**
  - Formal reasoning and constraint satisfaction
  - Edge-case elimination and validation
  - Falsification attempts ("prove this wrong")
  - Optimization within known solution space

**Right Hemisphere - Pattern Violation (Explore)**
- **Recognition:** Flags when expected patterns break or fail
- **Generation:** Creates mutations and variations
- **Stopping Rule:** Stops when idea space is "rich enough" (sufficient diversity)
- **Output Style:** Divergent, possibility-oriented, expansive
- **Typical Behaviors:**
  - Divergent thinking and reframing
  - Hypothesis generation from anomalies
  - Analogical reasoning across domains
  - Exploration of unknown solution space

**Why This Separation Matters:**

This is NOT "logic vs creativity" (too vague). This is:
- **Prediction confirmation vs prediction error** as dual cognitive engines
- **Compression (left) vs Expansion (right)** of solution space
- **Exploitation (left) vs Exploration (right)** of strategies

These agents:
- Operate on the same base LLM but with different prompts, retrieval strategies, and memory stores
- Cannot directly overwrite each other's knowledge (preserving cognitive diversity)
- Learn independently while sharing high-confidence consensus knowledge
- **Both handle both recognition and generation** - they differ in WHAT they recognize and HOW they generate

### 2. **Agentic Context Engineering (ACE)**

Instead of updating model weights, the system **evolves context** through a bullet-based procedural memory:

- **NOT summaries**: Knowledge is stored as discrete, atomic bullets
- **NOT rewriting**: Memory grows incrementally; bullets are added, scored, and pruned
- **NOT hidden**: All procedural knowledge is inspectable, editable, and auditable

### 3. **Consciousness Ticks**

A novel **meta-cognitive control mechanism** inspired by discrete moments of conscious awareness in human cognition.

**What Ticks Are:**

Ticks represent discrete reevaluation moments - the system's equivalent of "wait... hold on" realizations. Think of them as:
- **A cognitive clock** that triggers periodic self-evaluation
- **An attention allocator** that decides what deserves focus
- **A mode switcher** that determines whether to keep exploiting or start exploring
- **A learning gate** that controls when and how deeply to reflect

**What Ticks Are NOT:**

-  **NOT emotions or feelings** - No anthropomorphization, no simulated consciousness
-  **NOT direct learning signals** - They don't score bullets as helpful/harmful
-  **NOT rewards** - This is not reinforcement learning
-  **NOT always active** - Low tick rates mean the system is in "flow state"

**The Consciousness Rate Concept:**

Tick frequency can be measured and interpreted as a "rate of consciousness" - how often the system needs to pause and reconsider:

| Tick Rate | Cognitive State | What's Happening | Hemisphere Behavior |
|-----------|----------------|------------------|---------------------|
| **Low (0.0-0.3)** | Flow / Autopilot | Background processing<br>Habitual reasoning<br>Known patterns | Stable, using proven bullets<br>Minimal reflection needed |
| **Medium (0.3-0.5)** | Normal Alertness | Standard task switching<br>Routine decision-making | Periodic check-ins<br>Shallow reflection |
| **High (0.5-0.8)** | Active Problem-Solving | Uncertainty present<br>Tool failures occurring<br>Hemispheres disagreeing | Deep reflection triggered<br>Learning likely |
| **Sustained High (0.8-1.0)** | Crisis / Breakthrough | Model breakdown<br>Paradigm shift needed<br>Current knowledge insufficient | Maximum learning pressure<br>New bullets generated |

**Tick Behavior Patterns:**

The system can exhibit different cognitive states based on tick frequency AND which hemisphere is repeatedly selected:

**High ticks + Left hemisphere loop:**
- **Meaning:** System detects something is wrong but keeps trying to solve it with existing logic
- **Analog:** Rumination, over-analysis, "stuck in a rut"
- **What's happening:** High uncertainty but low novelty tolerance
- **Action needed:** Force exploration (switch to Right)

**High ticks + Right hemisphere loop:**
- **Meaning:** System believes existing patterns are insufficient
- **Analog:** Brainstorming spirals, manic creativity
- **What's happening:** High novelty signal, unbounded search
- **Action needed:** Anchor with constraints (bring in Left)

**High ticks + oscillation (Left <-> Right):**
- **Meaning:** Active learning in progress
- **Analog:** Insight formation, hypothesis testing
- **What's happening:** Exploration <-> validation cycle
- **Expected outcome:** New bullet creation, then convergence

**The Critical Rule - Ticks Are Gates, Not Scores:**

```
WRONG: Every tick = +1 helpful or harmful
       
     This would make "time spent thinking" = "truth"
     Loops would self-reinforce
     The system could "learn" just by ticking

CORRECT: Ticks decide IF/HOW DEEPLY to reflect
         Outcomes decide WHAT to learn
         
       Ticks are necessary but NOT sufficient for learning
```

**What Ticks Actually Control:**

1. **Whether reflection occurs at all** (tick above threshold)
2. **Depth of reflection** (shallow/medium/deep based on tick rate)
3. **Whether new bullets are written** (high ticks + repeated failures)
4. **Whether to force hemisphere switching** (stuck in loops)
5. **Whether to promote/demote bullets** (sustained patterns)

**Tick as Attention:**

The tick is functionally equivalent to attention and arousal in biological systems:
- **Low ticks** = System is confident, proceeding automatically
- **High ticks** = System is uncertain, needs conscious deliberation
- **Tick spike** = Something unexpected happened, demands focus

This creates a **rate of consciousness** that's measurable and interpretable without claiming the system "feels" anything.

### 4. **Outcome-Based Learning**

Learning happens through **execution feedback**, not time spent:

**Helpful Signals:**
- Tool calls succeed as expected
- Validators/tests pass
- User confirms correctness
- Retrieved evidence supports claims

**Harmful Signals:**
- Tool/schema failures
- Output contradicts evidence
- User corrections
- Tests fail

---

---

## Core Concepts

### The Interaction Loop: How Hemispheres Work Together

The two hemispheres don't just alternate - they engage in a **continuous explore-prune cycle**:

```
Right Hemisphere (Pattern Violation):
  Generates 5-10 possibilities
  Asks open questions
  Proposes alternative framings
        
Left Hemisphere (Pattern Continuity):
  Tests each for feasibility
  Checks against constraints
  Validates logic and schemas
  Eliminates invalid options
        
Meta-Controller (Consciousness Tick):
  Evaluates cognitive state:
    - Are we stuck? (sustained high ticks on one side)
    - Are we learning? (oscillating with decreasing ticks)
    - Are we done? (ticks dropping, decision made)
  Decides:
    - Continue current hemisphere?
    - Switch to other hemisphere?
    - Increase/decrease reflection depth?
        
Repeat until convergence
```

**Example Interaction - "Should we implement feature X?"**

**Right Hemisphere (Explore):**
- "Here are 6 interpretations of feature X"
- "Here are 4 ways it could work"
- "Here are risks we might not be considering"
- Output: Multiple hypotheses, open questions

**Left Hemisphere (Prune):**
- "Interpretations 1, 3, 5 violate constraints"
- "Only option 2 is feasible in current timeline"
- "Risk A is a blocker; B is acceptable"
- Output: Binary decisions, constraint violations flagged

**Right Hemisphere (Refine):**
- "Given option 2, here are 3 variants"
- "Here's a reframing that removes Risk A"
- Output: Refined possibilities

**Left Hemisphere (Commit):**
- "Variant 2 passes all checks"
- "Decision: Implement variant 2"
- Output: Final decision

**Meta-Controller Throughout:**
- Ticks start high (uncertainty about feature)
- Drop during pruning (options narrowing)
- Spike if conflict detected (hemispheres disagree)
- Drop to low (decision made, high confidence)

### Why Both Sides Need Both Recognition AND Generation

**The Trap of Oversimplification:**

If you assigned:
- Recognition ONLY to Left
- Creation ONLY to Right

You'd get:
- Brittle pattern lock-in (no detection of when patterns fail)
- Chaotic novelty (no validation of generated ideas)

**The Correct Model:**

Both sides recognize, both sides generate - but they recognize and generate **different aspects**:

**Left Hemisphere:**
- **Recognizes:** "This IS a pattern I know" (confirmation)
- **Generates:** "Apply this known pattern" (replication)
- **Example Bullet:** "When MCP tool fails with schema error, request schema and retry"

**Right Hemisphere:**
- **Recognizes:** "This is NOT a pattern I know" (violation detection)
- **Generates:** "Try this mutation of the pattern" (creative variation)
- **Example Bullet:** "When stuck, try analogies from unrelated domains"

This creates **complementary learning**:
- Left learns better rules for known situations
- Right learns better strategies for unknown situations
- Shared memory contains what both agree works universally

### Procedural Memory vs Knowledge RAG

The system maintains **two separate memory systems** that must never be confused:

| Memory Type | Purpose | Storage | Retrieval |
|-------------|---------|---------|-----------|
| **Knowledge RAG** | Facts, documents, papers, code | Standard vector store (docs/chunks) | Semantic similarity |
| **Procedural Memory** | "What works", strategies, heuristics | Bullet-based playbooks (atomic items) | Hemisphere-specific + metadata filtering |

**Critical Distinction:** Procedural memory bullets are NOT facts. They are behavioral knowledge:
- "When MCP tool returns schema error, request schema and retry with strict typing"
- "If retrieval confidence < 0.3, ask clarifying question"
- "Prefer exact matching over semantic inference for IDs"

### The Three Playbooks

Procedural memory is partitioned into three vector collections:

1. **`procedural_left`**: Left hemisphere's logic-oriented rules, checklists, validation steps
2. **`procedural_right`**: Right hemisphere's exploration heuristics, hypothesis templates
3. **`procedural_shared`**: High-confidence, cross-validated consensus knowledge

Each hemisphere:
- Queries only its own collection + shared
- Learns primarily in its own memory space
- Promotes proven bullets to shared memory after repeated success

### Bullet Lifecycle

Every procedural memory bullet follows a strict lifecycle:

```
NEW -> QUARANTINED -> ACTIVE -> SHARED (promotion)
                           -> DEPRECATED (if harmful)
```

**Quarantine Rules:**
- All new bullets start quarantined
- Must be marked helpful N times (default: 3) before becoming active
- Must have zero (or very low) harmful marks
- Prevents single-event noise from polluting memory

**Promotion to Shared:**
- `helpful_count >= 3` (configurable)
- `harmful_count == 0` (strict by default)
- Used successfully in multiple distinct episodes
- Ideally cross-validated by both hemispheres

---

## Technical Architecture

### System Layers

```

                        User Interface                        
                   (Desktop UI / CLI / API)                   

                              

                     Meta-Controller                          
  - Consciousness tick generator                             
  - Hemisphere selection (left/right/both)                   
  - Exploration policy (exploit/explore/integrate)           
  - Novelty detection & conflict resolution                  

                              
                
                                           
   
     Left Hemisphere              Right Hemisphere       
  (Pattern Continuity)          (Pattern Violation)      
                                                         
  - Logic & validation          - Creativity & novelty   
  - Tool correctness            - Hypothesis generation  
  - Checklists & schemas        - Reframing & questions  
  - Risk aversion               - Exploration            
   
                                        
         
                     

                  Learning Pipeline                           
  1. Execute -> 2. Trace -> 3. Reflect -> 4. Curate -> 5. Learn  
                                                               
  - Reflector (tick-gated depth: shallow/medium/deep)        
  - Curator (insight extraction, quality control)            
  - Deduplicator (semantic similarity, quality merging)      
  - Pruner (policy-based: aggressive/balanced/conservative)  

                     

                  Procedural Memory                           
                                                               
                     
   procedural_left     procedural_right                  
                                                         
   k=8, conf=0.6      k=16, conf=0.4                   
   precision-first     diversity-first                   
                     
                                                               
                  
          procedural_shared                                 
    (Consensus knowledge, helpful_count3)                  
                  
                                                               
  Technology: ChromaDB + Sentence Transformers               
  Embeddings: all-MiniLM-L6-v2 (CPU-friendly)               

                     

                External Integrations                         
                                                               
  - Model Context Protocol (MCP) - Tool execution            
  - Knowledge RAG - Factual retrieval (separate from memory) 
  - Local LLM - Inference via Ollama                         

```

### Data Flow: Single Task Execution

```
User Query
    
Meta-Controller Tick
     Calculate novelty from context
     Decide hemisphere lead (left/right/both)
     Set reflection depth threshold
    
Hemisphere Agent (e.g., Left)
     Retrieve procedural bullets (from procedural_left + shared)
     Retrieve knowledge facts (from RAG, if needed)
     Assemble prompt with:
       - System role ("You are Left Brain...")
       - Facts from RAG
       - Procedural strategies from bullets
       - Common failure modes
     Execute plan (potentially calling MCP tools)
     Log which bullet IDs were used
    
Tool Execution (if applicable)
     Validate parameters using bullet rules
     Call MCP tool
     Capture success/failure + trace
     Generate ExecutionTrace object
    
Novelty Calculation
     Compare expected vs actual outcomes
     Measure: entropy, conflict, surprise, tool failures
     Emit tick_rate (0.0 = routine, 1.0 = high novelty)
    
Learning Pipeline (if tick_rate > threshold)
    
1. Reflector (tick-gated depth)
     Shallow (tick < 0.5): "Did this work?"
     Medium (0.5  tick < 0.8): "What helped/harmed?"
     Deep (tick  0.8): "Why? What's missing?"
    
2. Extract Insights
     Parse reflection output
     Tag with evidence and confidence
     Produce candidate bullets
    
3. Curator
     Quality control (min_confidence filter)
     Duplicate detection (semantic similarity)
     Decide: add new bullet or update existing
     All new bullets start QUARANTINED
    
4. Outcome Scoring
     If success: helpful_count += 1 for top relevant bullets
     If failure: harmful_count += 1 for implicated bullets
     Promotion check: helpful3, harmful=0 -> ACTIVE
    
5. Shared Promotion (if eligible)
     Check cross-validation criteria
     Optionally translate for other hemisphere
     Copy to procedural_shared
    
Final Answer to User
```

---

## How It Works

### 1. Consciousness Ticks Drive Reflection

The meta-controller continuously evaluates execution novelty to generate ticks:

**Novelty Signals:**
- Tool call outcomes (success/failure)
- Schema mismatches
- Contradiction between hemispheres
- User corrections
- Low retrieval confidence

**Tick Calculation:**
```python
novelty_score = weighted_average(
    entropy_delta,           # Expected vs actual outcome difference
    conflict_signal,         # Hemispheres disagree on approach
    tool_failure_rate,       # How many tools are failing
    retrieval_uncertainty,   # RAG confidence is low
    user_correction_flag     # User said "that's wrong"
)

tick_rate = smooth(novelty_score)  # Moving average to prevent oscillation
```

**Tick-Gated Reflection Depth:**

The tick rate determines NOT whether learning happens, but HOW DEEPLY the system reflects:

```

 Tick Rate: 0.0 - 0.5 (Low to Medium)                        
 Reflection: SHALLOW or NONE                                  
                                                               
 Questions Asked:                                              
   - "Did this work?" (yes/no)                                
   - "Was the outcome expected?" (yes/no)                     
                                                               
 Action:                                                       
   - Simple outcome recording (helpful/harmful)               
   - No new bullets created                                   
   - Existing bullets scored only                             



 Tick Rate: 0.5 - 0.8 (Medium to High)                       
 Reflection: MEDIUM                                           
                                                               
 Questions Asked:                                              
   - "What specifically helped or harmed?"                    
   - "Which bullets were most relevant?"                      
   - "Was there a pattern to the failure/success?"           
                                                               
 Action:                                                       
   - Detailed trace analysis                                  
   - Bullet causality assessment                              
   - Potential bullet updates                                 
   - May quarantine new bullet if gap detected                



 Tick Rate: 0.8 - 1.0 (High to Extreme)                      
 Reflection: DEEP (involves LLM reasoning)                    
                                                               
 Questions Asked:                                              
   - "WHY did this fail/succeed?"                             
   - "What's the underlying pattern we're missing?"           
   - "What assumptions were wrong?"                           
   - "What tool/strategy should we try instead?"              
                                                               
 Action:                                                       
   - Full LLM-powered reflection                              
   - Causal analysis across multiple traces                   
   - New bullet creation (quarantined)                        
   - May force hemisphere switch                              
   - May promote/deprecate existing bullets                   

```

**The Critical Insight:**

Ticks measure **cognitive pressure**, not truth:
- High ticks = "I need to think harder about this"
- Low ticks = "I'm confident in this pattern"
- Oscillating ticks = "I'm actively learning"
- Sustained high ticks = "My current knowledge is insufficient"

**What This Prevents:**
-  Time spent thinking = correctness
-  Loops can't self-reinforce just by running
-  Noise doesn't accumulate from routine operations

### 2. Hemispheres Have Different Retrieval Strategies

**Left Hemisphere (Precision-First):**
```python
retrieval_config = {
    "k": 8,                    # Lower K (fewer bullets)
    "min_confidence": 0.6,     # Higher confidence threshold
    "diversity_penalty": 0.8,  # Penalize novelty
    "tag_filter": strict,      # Hard tool/domain filters
    "re_rank_by": "helpful_count",
    "exclude_statuses": ["quarantined"]
}
```

**Right Hemisphere (Diversity-First):**
```python
retrieval_config = {
    "k": 16,                   # Higher K (more options)
    "min_confidence": 0.4,     # Lower confidence threshold
    "diversity_penalty": 0.2,  # Encourage variety
    "tag_filter": loose,       # Looser matching
    "re_rank_by": "novelty + diversity",
    "allow_statuses": ["quarantined"]  # Include wild ideas
}
```

### 3. Learning Pipeline Prevents Memory Collapse

**Problem ACE Solves:** Traditional LLM memory systems suffer from:
- **Brevity bias**: Summaries get shorter over time
- **Context collapse**: Rewriting destroys detail
- **Hallucinated learning**: Single events create false patterns

**ACE Solution (Implemented Here):**
1. **Never rewrite** - Only add/update discrete bullets
2. **Start quarantined** - All new knowledge must prove itself
3. **Outcome-based scoring** - Ticks gate reflection, outcomes update scores
4. **Periodic dedupe/prune** - Remove redundancy without losing quality
5. **Explicit lifecycle** - Quarantined -> Active -> Shared -> Deprecated

### 4. Cross-Hemisphere Learning (Conservative Mode)

**Default: `shared_only` Mode**
- Each hemisphere learns in its own memory space
- No direct cross-writing
- Shared memory acts as the **only bridge**
- Bullets must earn promotion through repeated success

**Promotion Flow:**
```
Left Bullet (helpful_count=3, harmful=0)
    
Eligible for Shared
    
Cross-Validation Check (optional):
    "Has Right hemisphere used this successfully?"
    
Translation (if needed):
    Convert "strict rule" -> "creative constraint"
    
Copy to procedural_shared
    
Now available to both hemispheres
```

**Why This Matters:**
- Prevents one hemisphere from overwriting the other
- Preserves cognitive diversity
- Shared memory represents **consensus**, not compromise

---

## Implementation Details

### Bullet Schema

Every procedural memory bullet is stored with comprehensive metadata:

```python
@dataclass
class Bullet:
    id: str                    # Stable unique ID (e.g., "pb_left_0421")
    side: Literal["left", "right", "shared"]
    bullet_type: BulletType    # tool_rule | heuristic | checklist | pitfall | template | example
    text: str                  # The actual content (embedded)
    tags: List[str]            # ["mcp", "hubspot", "schema"]
    confidence: float          # 0.0 - 1.0
    helpful_count: int         # Incremented on successful outcomes
    harmful_count: int         # Incremented on failures
    status: BulletStatus       # active | quarantined | deprecated
    created_at: datetime
    last_used_at: datetime
    source_trace_id: Optional[str]  # Link to episodic trace
    metadata: Dict[str, Any]   # Extensible for future features
```

### Vector Store Technology Stack

**Primary Storage: ChromaDB**
- Persistent local vector database
- Separate collections per hemisphere + shared
- Fast approximate nearest neighbor search
- Built-in metadata filtering

**Embeddings: Sentence Transformers**
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- CPU-friendly (384-dimensional embeddings)
- Balanced speed/quality for procedural text

**Why Not FAISS?**
- Chroma provides simpler collection management
- Metadata filtering is more straightforward
- Persistence is handled automatically
- Minimal configuration overhead

### MCP (Model Context Protocol) Integration

**What MCP Provides:**
- Standardized interface for tool execution
- Structured tool discovery and registration
- Success/failure signals for learning
- Safe parameter validation

**How It's Used:**
1. **Tool Discovery**: MCP servers advertise available tools
2. **Parameter Validation**: Bullet rules check schemas before execution
3. **Execution**: Tools are called with validated parameters
4. **Trace Generation**: Every tool call produces an ExecutionTrace
5. **Learning**: Tool outcomes update bullet scores

**Example Flow:**
```python
# Retrieve relevant tool-usage bullets
bullets = memory.retrieve(
    query="hubspot contact creation",
    tags=["mcp", "hubspot"],
    side="left"
)

# Execute tool with bullet-guided validation
result = mcp_client.execute_tool(
    tool_name="hubspot.create_contact",
    params=validate_with_bullets(params, bullets),
    timeout=30
)

# Generate trace
trace = ExecutionTrace(
    tool_name="hubspot.create_contact",
    outcome="success" if result.ok else "failure",
    bullets_used=[b.id for b in bullets],
    evidence=result.data
)

# Learn from outcome
if result.ok:
    memory.record_helpful(bullets[0].id)
else:
    memory.record_harmful(bullets[0].id)
    learning_pipeline.reflect_and_curate(trace, tick_rate=0.9)
```

### Maintenance & Memory Hygiene

**Deduplication (Daily):**
```python
deduplicator.run(
    threshold=0.90,           # Cosine similarity threshold
    merge_strategy="quality", # Keep highest quality bullet
    max_per_run=100          # Safety limit
)
```

**Pruning (Weekly):**
```python
pruner.run(
    policy="balanced",        # aggressive | balanced | conservative
    criteria={
        "min_helpful": 1,
        "max_harmful": 3,
        "min_age_days": 30,
        "unused_threshold_days": 90
    },
    backup=True               # Automatic backup before pruning
)
```

**Quality Analysis:**
```python
quality_scores = {
    "high": confidence > 0.7 and helpful > harmful * 3,
    "medium": confidence > 0.5 and helpful >= harmful,
    "low": confidence < 0.5 or harmful > helpful
}
```

---

## Getting Started

### Hardware Requirements

**Minimum:**
- GPU: 16GB VRAM (RTX 4080 or equivalent)
- RAM: 32GB
- CPU: Modern multi-core (i5-13600K or better)
- Storage: 50GB free (for models + vector DB)

**Recommended Models:**
- **Llama 3.1 8B** (quantized to 4-bit: ~6GB VRAM)
- **Qwen 3:14B** (quantized to 4-bit: ~9GB VRAM)
- **Gemma 3 12B int4** (~7GB VRAM)

### Installation

1. **Clone repository:**
```bash
git clone https://github.com/yourusername/Bicameral_Mind.git
cd Bicameral_Mind
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `langchain-core >= 0.1.0`
- `langchain-community >= 0.0.38`
- `chromadb >= 0.4.22`
- `sentence-transformers >= 2.3.1`
- `ollama >= 0.13.5`
- `pydantic >= 2.0.0`

3. **Setup local LLM (via Ollama):**
```bash
# Install Ollama (if not already)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3:8b
```

4. **Configure the system:**
Edit `config/config.yaml`:
```yaml
model:
  name: "llama3:8b"
  base_url: "http://localhost:11434"
  max_tokens: 2048

procedural_memory:
  persist_directory: "./data/memory/procedural"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  promote_threshold: 3
  quarantine_threshold: 2
```

5. **Run tests:**
```bash
# Phase 1: Procedural memory
python tests/test_procedural_memory.py

# Phase 2: Learning pipeline
python tests/test_learning_simple.py

# Phase 3: MCP integration
python tests/test_mcp_integration.py
```

6. **Try examples:**
```bash
# Basic usage
python examples/usage.py

# Learning pipeline
python examples/learning_pipeline_example.py

# MCP tools
python examples/mcp_usage_example.py
```

### Quick Start Example

```python
from core.bicameral_mind import BicameralMind
from core.memory.learning_pipeline import LearningPipeline
from core.meta_controller import MetaController

# Initialize system
mind = BicameralMind(config_path="config/config.yaml")
controller = MetaController()
pipeline = LearningPipeline(memory=mind.memory)

# Example 1: Routine query (Left hemisphere favored)
query = "What's the correct schema for HubSpot contact creation?"

tick_rate = controller.calculate_novelty(query)  # Low novelty -> 0.2
hemisphere = controller.select_hemisphere(tick_rate)  # "left"

response = mind.process(
    query=query,
    hemisphere=hemisphere,
    enable_learning=True
)

print(f"Answer: {response.text}")
print(f"Tick Rate: {tick_rate:.2f} (Low - routine pattern)")
print(f"Hemisphere: {hemisphere} (Pattern confirmation)")
print(f"Bullets Used: {len(response.bullets_used)}")
# Expected: Left returns precise schema from its checklist bullets

# Example 2: Novel problem (Right hemisphere favored)
query = "The HubSpot API is rejecting all our calls with a mysterious error. What creative approaches could we try?"

tick_rate = controller.calculate_novelty(query)  # High novelty -> 0.8
hemisphere = controller.select_hemisphere(tick_rate)  # "right"

response = mind.process(
    query=query,
    hemisphere=hemisphere,
    enable_learning=True
)

print(f"\nAnswer: {response.text}")
print(f"Tick Rate: {tick_rate:.2f} (High - pattern violation)")
print(f"Hemisphere: {hemisphere} (Creative exploration)")
print(f"Bullets Used: {len(response.bullets_used)}")
# Expected: Right generates multiple hypotheses and alternative approaches

# Example 3: Learning from failure
query = "Create a contact in HubSpot with email 'test@example.com'"

# First attempt - tool call fails due to missing required field
tick_rate_initial = 0.3  # Starts low (seems routine)

response = mind.process(query, "left", enable_learning=True)
# Tool fails: "Missing required field: firstname"

# Tick rate spikes after failure
tick_rate_after_failure = controller.calculate_novelty_from_trace(
    response.execution_trace
)  # -> 0.9 (high - unexpected failure)

# Deep reflection triggered
if tick_rate_after_failure > 0.8:
    insights = pipeline.reflect_and_curate(
        trace=response.execution_trace,
        tick_rate=tick_rate_after_failure,
        depth="deep"
    )
    # New bullet created (quarantined):
    # "HubSpot contact creation requires 'firstname' field even though API docs mark it optional"
    
print(f"\nLearning occurred:")
print(f"Initial tick: {tick_rate_initial:.2f}")
print(f"Post-failure tick: {tick_rate_after_failure:.2f}")
print(f"New bullets quarantined: {len(insights)}")
print(f"Bullets will become active after 3 successful uses")
```

### Understanding the Examples

**Example 1 - Left Hemisphere (Pattern Confirmation):**
- Query asks for established knowledge (schema)
- Low novelty (we've done this before)
- Left hemisphere retrieves precise rules
- No learning needed (pattern already known)

**Example 2 - Right Hemisphere (Pattern Violation):**
- Query indicates existing approaches aren't working
- High novelty (unexpected behavior)
- Right hemisphere generates alternative hypotheses
- May create new exploration strategies

**Example 3 - Learning Loop:**
- Starts as routine (low ticks)
- Failure causes tick spike (high novelty)
- Deep reflection extracts lesson
- New bullet quarantined
- Future similar tasks will use this bullet
- After 3 successes, bullet becomes active

---

## Phase Completion Status

###  Phase 1: Procedural Memory Foundation
**Status**: Complete

**Implemented:**
- Bullet-based storage (NOT summaries)
- Three separate collections (left/right/shared)
- Outcome-based learning (NOT tick-based)
- Automatic promotion to shared memory
- Quarantine -> Active lifecycle
- No cross-hemisphere contamination

###  Phase 2: Learning Pipeline
**Status**: Complete

**Implemented:**
- Tick-gated reflection (shallow/medium/deep)
- Execution trace analysis
- Insight extraction with evidence
- Quality-controlled curation
- Duplicate detection
- Complete learning cycle

**Critical Principles:**
-  Ticks gate reflection DEPTH, NOT scoring
-  Outcomes update SCORES, NOT ticks
-  Reflector proposes, Curator decides
-  Add incrementally, never rewrite
-  Start QUARANTINED, promote with validation

###  Phase 2.5: Automatic Tick Generation
**Status**: Complete

**Implemented:**
- Novelty detector for consciousness ticks
- Automatic tick calculation from execution novelty
- Moving average to prevent oscillation
- Evidence-based novelty measurements
- Five novelty signal types

###  Phase 3: MCP Integration
**Status**: Complete

**Implemented:**
- MCP server connection management
- Tool discovery and registration
- Safe tool execution with error handling
- Tool result to ExecutionTrace conversion
- Automatic outcome signal extraction
- Integration with learning pipeline
- Real-time learning from tool usage

###  Phase 4: Deduplication & Pruning
**Status**: Complete

**Implemented:**
- Semantic deduplication (cosine similarity)
- Quality-based bullet merging
- Quality analyzer (aggressive/balanced/conservative policies)
- Safe pruning with automatic backup
- Scheduled maintenance (daily dedupe, weekly prune)
- Comprehensive audit trail

###  Phase 6: Cross-Hemisphere Learning
**Status**: Core implementation complete

**Implemented:**
- Suggestion lifecycle + delivery gating
- Teaching API for explicit transfer
- Conflict detection with quarantine metadata
- Shared promotion gates
- Diversity metrics and convergence throttling
- Forced exploration policy

###  Phase 5: Desktop UI
**Status**: In Progress

**Planned:**
- Real-time dashboard
- Bullet curation interface
- Tool monitoring and configuration
- Conversation history with hemisphere visualization

---

## Configuration

### Complete Configuration Reference

```yaml
# config/config.yaml

# LLM Configuration
model:
  name: "llama3:8b"
  base_url: "http://localhost:11434"
  temperature: 0.7
  max_tokens: 2048
  context_window: 8192

# Procedural Memory
procedural_memory:
  enabled: true
  persist_directory: "./data/memory/procedural"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  
  # Phase 1: Basic Settings
  promote_threshold: 3        # helpful_count needed for Active -> Shared
  quarantine_threshold: 2     # helpful_count needed for Quarantined -> Active
  
  # Phase 2: Learning Pipeline
  learning:
    reflection_enabled: true
    auto_curate: true
    min_insight_confidence: 0.5
    deep_reflection_llm: true
  
  # Phase 4: Maintenance
  maintenance:
    enabled: true
    deduplicate_enabled: true
    dedup_threshold: 0.90     # Cosine similarity threshold
    dedup_schedule: "daily"
    prune_enabled: true
    prune_policy: "balanced"  # aggressive | balanced | conservative
    prune_schedule: "weekly"
    backup_before_prune: true
    max_prune_per_run: 100
  
  # Phase 6: Cross-Hemisphere Learning
  cross_hemisphere:
    mode: "shared_only"       # shared_only | suggestions
    enabled: true
    suggestions:
      enabled: false          # Enable for aggressive cross-teaching
    shared:
      promote_threshold: 3
      harmful_tolerance: 0
    conflicts:
      enabled: true
    diversity:
      enabled: true
    exploration:
      enabled: true

# Meta-Controller
meta_controller:
  tick:
    base_rate: 0.5
    novelty_weight: 0.7
    conflict_weight: 0.8
    entropy_weight: 0.5
  
  reflection_thresholds:
    shallow: 0.0
    medium: 0.5
    deep: 0.8

# Knowledge RAG (separate from procedural memory)
knowledge_rag:
  enabled: true
  persist_directory: "./data/memory/rag"
  chunk_size: 512
  chunk_overlap: 50

# MCP Integration
mcp:
  enabled: true
  servers:
    - name: "hubspot"
      url: "http://localhost:3000/mcp"
      timeout: 30
    # Add more MCP servers as needed

# Logging
logging:
  level: "INFO"
  file: "./logs/bicameral_mind.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## Development Roadmap

### Immediate Next Steps

**Phase 5: Desktop UI Completion**
- [ ] Streaming response visualization
- [ ] Real-time bullet curation interface
- [ ] Hemisphere activity monitoring
- [ ] Tool execution dashboard

**Phase 6: Cross-Hemisphere Learning Refinement**
- [ ] Suggestion learning metrics
- [ ] Teaching effectiveness tracking
- [ ] Cognitive diversity monitoring
- [ ] Hemisphere specialization analysis

### Medium-Term Goals

**Phase 7: Episodic Memory Integration**
- [ ] Link bullets to execution traces
- [ ] Trace replay for learning validation
- [ ] Pattern recognition across episodes
- [ ] Causal chain analysis

**Phase 8: Multi-Modal Learning**
- [ ] Visual trace analysis
- [ ] Audio/speech learning integration
- [ ] Image-based insights
- [ ] Multi-modal bullet creation

### Long-Term Vision

**Generative Self-Play (GAN-Based Learning)**
- [ ] Left/Right hemispheres as GANs
- [ ] Adversarial training data generation
- [ ] Pattern-antipattern synthesis
- [ ] Self-improving exploration strategies

**Multi-Agent Scaling**
- [ ] Support for >2 specialized agents
- [ ] Domain-specific expert agents
- [ ] Hierarchical meta-controllers
- [ ] Distributed execution (multi-machine)

---

## Key Design Principles

### 1. **No Hidden Dependencies**
All knowledge is local, inspectable, and user-controlled. No cloud APIs required.

### 2. **Outcome-Based, Not Time-Based**
Ticks measure cognitive pressure and gate reflection depth. Only execution outcomes update bullet scores.

### 3. **Incremental Growth, Never Rewrite**
Memory expands through atomic bullets. Deduplication and pruning are explicit, auditable operations.

### 4. **Preserve Cognitive Diversity**
Hemispheres maintain distinct reasoning styles. Shared memory represents consensus, not compromise.

### 5. **Inspectability First**
Every bullet, trace, and decision is logged and queryable. The system explains itself.

### 6. **Local-First, Cloud-Optional**
Designed for consumer hardware. Cloud integrations (if added) are opt-in, not required.

---

## Testing & Validation

### Test Coverage

**Unit Tests:**
-  Procedural memory CRUD operations
-  Bullet lifecycle (quarantine -> active -> shared)
-  Hemisphere separation (no cross-contamination)
-  Novelty detection and tick generation
-  MCP tool execution and tracing
-  Deduplication and pruning logic

**Integration Tests:**
-  Complete learning cycle (execute -> reflect -> curate)
-  Tick-gated reflection depths
-  Tool outcome learning
-  Cross-hemisphere promotion
-  Maintenance scheduling

### Running Tests

```bash
# All tests
python -m pytest tests/

# Specific phases
python tests/test_procedural_memory.py
python tests/test_learning_simple.py
python tests/test_tick_generation.py
python tests/test_mcp_integration.py
python tests/test_phase4_maintenance.py
```

---

## Architecture Diagrams

### Learning Cycle

```

                     Execute Task                              
  - Retrieve procedural bullets (hemisphere + shared)          
  - Retrieve knowledge facts (RAG)                             
  - Assemble prompt with strategies & failure modes            
  - Execute plan (potentially calling MCP tools)               
  - Log bullet IDs used                                        

                              

                   Generate Trace                              
  - Capture tool calls, results, errors                        
  - Record expected vs actual outcomes                         
  - Link to bullets used                                       

                              

                Calculate Novelty                              
  - Entropy delta (expected vs actual)                         
  - Conflict signal (hemisphere disagreement)                  
  - Tool failure rate                                          
  - Retrieval uncertainty                                      
  - User correction flag                                       
  -> Emit tick_rate (0.0 - 1.0)                                

                              

              Tick-Gated Reflection                            
  if tick_rate >= threshold:                                   
    - Shallow (tick < 0.5): "Did this work?"                   
    - Medium (0.5  tick < 0.8): "What helped/harmed?"         
    - Deep (tick  0.8): "Why? What's missing?"                
  else:                                                        
    - Skip reflection, proceed to scoring                      

                              

                 Extract Insights                              
  - Parse reflection output                                    
  - Tag with evidence and confidence                           
  - Produce candidate bullets                                  

                              

                     Curate                                    
  - Quality control (min_confidence filter)                    
  - Duplicate detection (semantic similarity)                  
  - Decide: add new bullet or update existing                  
  - All new bullets start QUARANTINED                          

                              

                Outcome Scoring                                
  - Success: helpful_count += 1 for top bullets                
  - Failure: harmful_count += 1 for implicated bullets         
  - Check promotion: helpful3, harmful=0 -> ACTIVE             

                              

            Shared Promotion (if eligible)                     
  - Verify cross-validation criteria                           
  - Optionally translate for other hemisphere                  
  - Copy to procedural_shared                                  

```

---

## Frequently Asked Questions

### Is this system actually "conscious"?

**No.** The "consciousness ticks" are a functional metaphor, not a claim of sentience.

**What the system has:**
- Discrete moments of self-evaluation (ticks)
- Ability to detect when it's uncertain
- Mechanisms to pause and reconsider
- Measurable "rate of deliberation"

**What the system does NOT have:**
- Subjective experience
- Feelings or emotions
- Self-awareness in the philosophical sense
- Qualia or phenomenal consciousness

**Why use "consciousness" terminology?**

Because the functional behavior closely mirrors attention and arousal in biological cognition:
- Low ticks = autopilot (subconscious processing)
- High ticks = deliberation (conscious thought)
- Tick spikes = "wait, something's wrong" moments

It's a useful engineering metaphor that makes the system's behavior interpretable without anthropomorphizing.

### Why not just fine-tune the model?

**Fine-tuning requires:**
- Large labeled datasets
- Expensive GPU training
- Risk of catastrophic forgetting
- Black-box weight updates

**ACE provides:**
- Learning from sparse feedback
- Transparent, inspectable knowledge
- Continuous adaptation without retraining
- User control over what's learned

### How is this different from RAG?

**Traditional RAG:**
- Retrieves facts from documents
- Single-pass, one-shot retrieval
- No learning mechanism
- No behavioral memory

**Bicameral Mind:**
- Retrieves facts AND strategies
- Iterative, agentic retrieval
- Learns from outcomes
- Procedural memory evolves

### Why two hemispheres instead of one agent?

**Single-agent systems:**
- Collapse into average behavior
- Lack specialized strategies
- No internal debate mechanism
- Limited exploration

**Bicameral architecture:**
- Preserves cognitive diversity
- Enables exploration-exploitation balance
- Provides built-in critique
- Supports complex reasoning

### Can I add more than two agents?

Yes, but carefully. The current architecture supports:
- Two primary hemispheres (left/right)
- Specialized sub-agents (future)
- Domain-expert agents (planned)

Adding agents requires:
- Clear role delineation
- Separate procedural memories
- Updated meta-controller logic

### What's the maximum memory size?

**Practical limits:**
- Bullets per hemisphere: ~100K (before pruning needed)
- Embeddings fit comfortably in RAM
- ChromaDB handles millions of vectors
- Retrieval speed remains fast with proper indexing

**Memory management:**
- Daily deduplication prevents bloat
- Weekly pruning removes low-value bullets
- Backup/restore enables rollback

---

## Contributing

This project follows ACE principles:

1. **Bullet-based**: No monolithic summaries
2. **Outcome-based**: Learning tied to execution results
3. **Incremental**: Add, don't rewrite
4. **Inspectable**: All knowledge is auditable

### Development Guidelines

**When adding features:**
- Preserve hemisphere separation
- Maintain bullet lifecycle invariants
- Add tests for new learning signals
- Document configuration options

**When modifying memory:**
- Never rewrite existing bullets in bulk
- Always use delta updates
- Respect quarantine -> active -> shared flow
- Log all destructive operations

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

**Theoretical Foundations:**
- Agentic Context Engineering (ACE) research
- Human brain lateralization studies
- Pattern recognition/mutation in adaptive systems

**Technical Inspirations:**
- ChromaDB for vector storage
- Ollama for local LLM serving
- Model Context Protocol (MCP) specification
- LangChain for tool orchestration

---

## Contact & Support

**Repository:** https://github.com/yourusername/Bicameral_Mind

**Documentation:**
- [Quick Start Guide](docs/QUICK_START.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Phase Documentation](docs/)

**For Questions:**
- Open an issue on GitHub
- Refer to inline code documentation
- Check example files in `examples/`

---

**Last Updated:** December 24, 2025  
**Current Version:** Phase 6 Complete  
**Next Milestone:** Phase 5 - Desktop UI Completion
