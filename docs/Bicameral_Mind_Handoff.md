Bicameral Mind AI System
Project Handoff / Continuation Document
Purpose of this document

This document describes the design, philosophy, architecture, and implementation goals of the Bicameral Mind AI system. It is intended as a continuity handoff so that another AI (or engineer) can pick up development without re-deriving the core ideas or making incorrect assumptions.

This system is not a standard chatbot, not simple RAG, and not RL fine-tuning. It is an agentic cognitive architecture inspired by:

Bicameral cognition (two complementary reasoning styles)

Agentic Context Engineering (ACE)

Learning from success/failure without weight updates

Persistent, inspectable procedural memory

Consciousness-like “ticks” as attention and learning gates

1. High-level goals

The system aims to:

Implement a two-hemisphere cognitive architecture

Allow self-learning from successes and failures without retraining weights

Maintain long-term procedural memory that evolves over time

Avoid context collapse, summary bias, and hallucinated learning

Operate locally, offline-capable, on a single desktop

Integrate with external tools via Model Context Protocol (MCP)

The system must remain:

Interpretable

Inspectable

Controllable by the owner

Free of hidden cloud dependencies

2. The Bicameral Architecture (Core Concept)
Two Hemispheres (Agents)

The system consists of two distinct agent roles, both powered by the same base LLM, but behaving differently due to context, memory, and retrieval strategy.

Left Hemisphere — Pattern Continuity

Role:

Logic

Determinism

Consistency

Tool correctness

Validation

“What has worked reliably before?”

Characteristics:

Precision-oriented

Risk-averse

Uses checklists, schemas, invariants

Optimized for correctness

Typical outputs:

Step-by-step plans

Tool usage rules

Schema validation

Error avoidance heuristics

Right Hemisphere — Pattern Violation

Role:

Novelty

Exploration

Hypothesis generation

Reframing

“What if the pattern is wrong?”

Characteristics:

Diversity-oriented

Tolerates uncertainty

Encourages creative angles

Optimized for discovery

Typical outputs:

Alternative interpretations

Clarifying questions

New approaches

Creative problem solving

Important constraint

Neither hemisphere is allowed to overwrite the other directly.
This preserves cognitive diversity and prevents collapse into a single “average” policy.

3. Procedural Memory (NOT RAG)
Key distinction

The system uses two different kinds of memory:

Memory Type	Purpose	Stored As
Knowledge RAG	Facts, docs, papers	Standard RAG vector store
Procedural Memory	“What works”	ACE-style bullet playbooks

Procedural memory is not factual knowledge.
It must never be mixed into standard RAG.

4. Procedural Memory Design
Playbook-based memory (ACE-inspired)

Procedural memory is stored as atomic bullets, not summaries.

Each bullet represents:

A strategy

A heuristic

A failure mode

A tool rule

A checklist item

Bullets are:

Added incrementally

Never rewritten wholesale

Scored over time

Pruned and deduplicated periodically

Memory layout

There are three procedural playbooks, implemented as separate vector collections:

procedural_left     # Left hemisphere memory
procedural_right    # Right hemisphere memory
procedural_shared   # High-confidence consensus memory


These live in:

One physical vector DB directory

Multiple collections / indexes

Each hemisphere queries only its own collection + shared

Bullet schema (required)

Each procedural memory item MUST include:

id                # stable unique ID
side              # left | right | shared
type              # tool_rule | heuristic | checklist | pitfall | template
text              # the actual bullet
tags              # tool/domain labels
confidence        # float 0–1
helpful_count
harmful_count
status            # active | quarantined | deprecated
created_at
last_used_at
source_trace_id   # link to episodic trace


Only text is embedded.
All other fields are metadata.

5. Learning WITHOUT weight updates (ACE-style)
Core principle

The model does not learn.
The context learns.

Learning occurs by:

Adding new bullets

Updating bullet confidence

Promoting bullets to shared memory

Deprecating harmful bullets

No gradient descent.
No fine-tuning.

6. Consciousness Ticks (Critical Concept)
What ticks are NOT

NOT emotions

NOT feelings

NOT learning themselves

NOT rewards

What ticks ARE

A cognitive clock and pressure signal.

A tick represents:

“Pause. Evaluate. Decide whether memory should change.”

Tick frequency as pressure
Tick Rate	Meaning
Low	Routine, known patterns
Medium	Mild uncertainty
High	Novelty, conflict, failure
Sustained High	Current procedural memory insufficient

Ticks gate:

Whether reflection occurs

How deep reflection goes

Whether new bullets are written

Whether promotion/demotion happens

CRITICAL RULE

Ticks must NEVER directly increment helpful/harmful counters.

If they do:

Time spent ≠ truth

Loops self-reinforce

Noise dominates

Ticks are necessary but not sufficient for learning.

7. Outcome-based learning (correct mechanism)
What increments helpful/harmful?

Only outcome-linked events:

Helpful signals:

Tool call succeeded as expected

Validator/test passed

User confirms success

RAG grounding verified

Harmful signals:

Tool/schema failure

Contradiction with evidence

User correction (“that’s wrong”)

Test failure

Learning pipeline

Agent executes plan

Procedural bullets used are logged

Outcome is observed

Reflector analyzes causality

Curator updates bullet scores

Ticks decide depth of update

8. Self-learning vs Cross-teaching
Default mode: Conservative (shared_only)

Each hemisphere primarily teaches itself

Cross-teaching happens only via shared memory

Shared memory contains only:

Repeated successes

Cross-validated bullets

High confidence rules

This prevents:

One hemisphere overwriting the other

Collapse into homogeneity

Loss of cognitive diversity

Optional future mode: Suggestions

One side can suggest bullets to the other

Suggestions are quarantined

Must be validated by the receiving side

Not implemented in v1.

9. Model Context Protocol (MCP)
MCP = Model Context Protocol (IMPORTANT)

MCP is used to:

Call external tools/APIs

Fetch structured tool responses

Receive success/failure signals

MCP is:

An execution environment

A learning signal source

A feedback loop

Procedural memory should heavily leverage MCP outcomes for learning.

10. Implementation priorities (for the next AI)
MUST implement first

Procedural vector store (Chroma or FAISS)

Bullet schema + CRUD

Per-hemisphere retrieval

Shared memory promotion rules

Used-bullet logging

Outcome-based scoring hooks

SHOULD implement next

Reflection module

Curator logic

Dedupe/pruning

Tool-specific sub-collections

OPTIONAL later

Cross-hemisphere suggestions

Episodic trace analytics

Multi-modal inputs

Generative self-play
