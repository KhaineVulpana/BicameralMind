# Staging Area Design: Hemisphere Assignment for New Bullets

## Problem Statement

Currently, bullets are assigned to hemispheres (`side: Hemisphere.LEFT/RIGHT`) immediately upon creation based on which agent executed the task. This causes issues:

1. **No validation** that bullet content matches hemisphere cognitive style
2. **No opportunity** for human review before assignment
3. **Risk of contamination**: Left brain could learn exploratory strategies, Right could learn rigid rules
4. **Loss of cognitive diversity** over time

## Solution: Staging Area (4-State Lifecycle)

### Current 3-State Lifecycle
```
QUARANTINED -> ACTIVE -> SHARED
```

### Proposed 4-State Lifecycle
```
STAGED -> QUARANTINED -> ACTIVE -> SHARED
       
   [Assignment Gate]
```

## New Bullet States

### 1. STAGED (New State)
- **Purpose**: Hold new bullets until hemisphere assignment
- **Storage**: New `procedural_staging` collection
- **Duration**: Until reviewed (manual or automatic)
- **Metadata**: Includes `source_hemisphere` (hint) but no final assignment

### 2. QUARANTINED (Enhanced)
- **Purpose**: Validate usefulness after assignment
- **Storage**: Assigned to `procedural_left` or `procedural_right`
- **Duration**: Until `helpful_count >= 2`
- **Change**: Now requires hemisphere assignment before entering this state

### 3. ACTIVE (Unchanged)
- Proven useful in assigned hemisphere
- Available for retrieval during execution

### 4. SHARED (Unchanged)
- Cross-validated consensus knowledge
- Available to both hemispheres

## Staging Collection Schema

### ChromaDB Collection: `procedural_staging`

```python
{
    "id": "staging_abc123",
    "text": "When API call fails, try exponential backoff",
    "metadata": {
        "status": "staged",
        "source_hemisphere": "left",  # Hint from executing agent
        "source_trace_id": "trace_xyz",
        "insight_type": "strategy",
        "confidence": 0.7,
        "tags": ["retry", "api"],
        "created_at": "2025-01-15T10:30:00Z",

        # Assignment hints
        "suggested_hemisphere": null,  # Set by auto-classifier
        "classification_confidence": null,
        "review_priority": "medium"  # low/medium/high
    }
}
```

## Assignment Mechanisms

### Option 1: Manual Review (UI)
User interface shows staged bullets with:
- Bullet text
- Source hemisphere (hint)
- LLM classification suggestion
- Action buttons: [Assign to Left] [Assign to Right] [Reject]

### Option 2: Automatic Classification (LLM)
```python
def classify_bullet_hemisphere(bullet_text: str, source_hint: str) -> tuple[Hemisphere, float]:
    """
    Classify bullet into left/right hemisphere based on cognitive style.

    Returns:
        (hemisphere, confidence)
    """
    prompt = f"""
Analyze this procedural bullet and determine which cognitive hemisphere it belongs to:

BULLET: "{bullet_text}"
SOURCE HINT: {source_hint} brain originally executed this

LEFT HEMISPHERE (Pattern Continuity):
- Confirmatory rules: "Always X", "When Y, must Z"
- Validation steps: "Check", "Verify", "Ensure"
- Precise, specific, actionable
- Binary decisions
- Examples: "Validate schema before API call", "Always check auth expiry"

RIGHT HEMISPHERE (Pattern Violation):
- Exploratory strategies: "Try X", "Consider Y"
- Alternative perspectives: "What if", "Maybe"
- Open-ended, possibility-oriented
- Hypothesis generation
- Examples: "When stuck, try analogies", "Explore edge cases"

Classify this bullet:
HEMISPHERE: [left/right]
CONFIDENCE: [0.0-1.0]
REASONING: [1-2 sentences]
"""

    response = llm.invoke(prompt)
    # Parse response
    return (hemisphere, confidence)
```

### Option 3: Hybrid (Auto + Manual Review)
- Auto-classify all staged bullets
- High-confidence (>0.8): Auto-assign
- Low-confidence (<0.8): Flag for human review
- Regular review queue in UI

## API Changes

### ProceduralMemory.add() - Add to Staging

```python
def add(
    self,
    text: str,
    source_hemisphere: Hemisphere,  # Renamed from 'side' (now just a hint)
    bullet_type: BulletType = BulletType.HEURISTIC,
    tags: Optional[List[str]] = None,
    confidence: float = 0.5,
    source_trace_id: str = "",
    auto_assign: bool = False,  # New parameter
) -> Bullet:
    """Add bullet to staging area.

    Args:
        source_hemisphere: Which agent created this (hint only)
        auto_assign: If True, auto-classify and assign immediately

    Returns:
        Bullet in STAGED status (or QUARANTINED if auto_assign=True)
    """
    bullet = Bullet.create(
        text=text,
        side=Hemisphere.STAGING,  # New enum value
        bullet_type=bullet_type,
        tags=tags,
        confidence=confidence,
        source_trace_id=source_trace_id,
    )
    bullet.status = BulletStatus.STAGED
    bullet.metadata["source_hemisphere"] = source_hemisphere.value

    # Store in staging collection
    self.store.add_bullet(
        side="staging",
        text=bullet.text,
        bullet_type=bullet_type.value,
        tags=tags,
        status=BulletStatus.STAGED.value,
        confidence=confidence,
        source_trace_id=source_trace_id,
        metadata=bullet.metadata,
        bullet_id=bullet.id,
    )

    # Optional: Auto-assign if requested
    if auto_assign:
        assigned_side, conf = self._auto_classify(bullet)
        if conf > 0.8:
            self.assign_staged_bullet(bullet.id, assigned_side)

    return bullet
```

### New: ProceduralMemory.assign_staged_bullet()

```python
def assign_staged_bullet(
    self,
    bullet_id: str,
    target_hemisphere: Hemisphere,
    reviewer: str = "auto"
) -> Bullet:
    """Move bullet from staging to target hemisphere (quarantined).

    Args:
        bullet_id: Staged bullet ID
        target_hemisphere: LEFT or RIGHT
        reviewer: "auto" or username for audit trail

    Returns:
        Bullet in QUARANTINED status in target hemisphere
    """
    # Retrieve from staging
    staged_bullet = self.store.get_bullet("staging", bullet_id)

    # Delete from staging
    self.store.delete_bullet("staging", bullet_id)

    # Add to target hemisphere as QUARANTINED
    assigned = self.add_to_hemisphere(
        text=staged_bullet.text,
        side=target_hemisphere,
        bullet_type=BulletType(staged_bullet.type),
        tags=staged_bullet.tags,
        confidence=staged_bullet.confidence,
        source_trace_id=staged_bullet.source_trace_id,
        status=BulletStatus.QUARANTINED,
        metadata={
            **staged_bullet.metadata,
            "assigned_by": reviewer,
            "assigned_at": datetime.now().isoformat(),
            "original_staging_id": bullet_id,
        }
    )

    logger.info(
        f"OK Assigned {bullet_id[:12]}... from staging to {target_hemisphere.value} "
        f"(reviewer: {reviewer})"
    )

    return assigned
```

### New: ProceduralMemory.list_staged()

```python
def list_staged(
    self,
    review_priority: Optional[str] = None,
    limit: int = 50
) -> List[Bullet]:
    """List bullets in staging area awaiting assignment.

    Args:
        review_priority: Filter by priority (low/medium/high)
        limit: Max bullets to return

    Returns:
        List of staged bullets
    """
    bullets = self.store.list_bullets(
        side="staging",
        limit=limit,
        include_deprecated=False
    )

    if review_priority:
        bullets = [
            b for b in bullets
            if b.metadata.get("review_priority") == review_priority
        ]

    return bullets
```

### New: ProceduralMemory.reject_staged_bullet()

```python
def reject_staged_bullet(
    self,
    bullet_id: str,
    reason: str = "",
    reviewer: str = "auto"
) -> None:
    """Reject and delete a staged bullet.

    Args:
        bullet_id: Staged bullet ID
        reason: Rejection reason for audit log
        reviewer: Who rejected it
    """
    # Log rejection before deletion
    logger.info(
        f"X Rejected staged bullet {bullet_id[:12]}... "
        f"(reviewer: {reviewer}, reason: {reason})"
    )

    # Delete from staging
    self.store.delete_bullet("staging", bullet_id)
```

## Enum Updates

### BulletStatus

```python
class BulletStatus(str, Enum):
    STAGED = "staged"              # NEW: In staging, awaiting assignment
    QUARANTINED = "quarantined"    # In hemisphere, needs validation
    ACTIVE = "active"              # Validated and in use
    DEPRECATED = "deprecated"      # Marked for removal
```

### Hemisphere

```python
class Hemisphere(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    SHARED = "shared"
    STAGING = "staging"  # NEW: Not yet assigned
```

## Configuration

### config.yaml additions

```yaml
procedural_memory:
  # Staging configuration
  staging:
    enabled: true
    auto_assign: false              # Auto-classify and assign high-confidence bullets
    auto_assign_threshold: 0.8      # Confidence needed for auto-assignment
    manual_review_threshold: 0.6    # Below this, flag as high priority for review
    max_staging_age_days: 30        # Auto-reject bullets older than this

  # Assignment classifier
  classifier:
    model: "qwen3:14b"              # LLM for classification
    temperature: 0.3                # Low temp for consistent classification
    prompt_template: "default"      # Or custom prompt path
```

## UI Integration (Phase 5)

### New Page: "Bullet Review Queue"

**Staged Bullets Table:**
```

 Bullet Review Queue                              [50 pending]        

 Text                            Source  Suggested  Confidence   

 "When API fails, try backoff"   Left    Left OK     0.92        -> 
 "Explore edge cases first"      Right   Right OK    0.88        -> 
 "Always validate schema"        Left    Left OK     0.95        -> 
 "Maybe try analogies?"          Left    Right     0.65         


[Bulk Assign High-Confidence] [Review Flagged]
```

**Bullet Detail Modal (for flagged items):**
```

 Review Bullet: staging_abc123                    

 Text:                                            
   "Maybe try analogies when stuck"               
                                                  
 Source: Left brain (executed task)               
 Classification: Right brain (confidence: 0.65)   
                                                  
 Reasoning:                                       
   "Uses exploratory language ('maybe', 'try')    
    suggesting hypothesis generation - typical    
    right hemisphere behavior"                    
                                                  
 Evidence:                                        
   - Trace: trace_xyz                             
   - Outcome: success                             
   - Used by: left brain                          
                                                  
 Actions:                                         
 [Assign to Left] [Assign to Right] [Reject]     

```

## Migration Strategy

### Phase 1: Add Staging Collection
1. Update `Hemisphere` enum to include `STAGING`
2. Update `BulletStatus` enum to include `STAGED`
3. Create `procedural_staging` collection in ChromaDB
4. Add staging methods to `ProceduralMemory`

### Phase 2: Update Curator
1. Modify `Curator.curate()` to call `memory.add()` with staging
2. Set `auto_assign=False` initially
3. Test that bullets go to staging

### Phase 3: Implement Auto-Classifier
1. Create `HemisphereClassifier` class
2. Add LLM-based classification
3. Test classification accuracy on existing bullets

### Phase 4: UI Integration
1. Add "Review Queue" page to Desktop UI
2. Implement manual assignment interface
3. Add bulk operations

### Phase 5: Enable Auto-Assignment (Optional)
1. Set `auto_assign=True` for high-confidence bullets
2. Monitor assignment accuracy
3. Adjust threshold as needed

## Backward Compatibility

**For existing bullets:**
- Already assigned to hemispheres -> no change
- `Bullet.side` already exists -> just add STAGING option
- `add()` method -> add `auto_assign` parameter (default `False`)

**For new code:**
- All new bullets go to staging first
- Can still bypass staging for testing: `add_to_hemisphere()` method

## Testing Plan

### Unit Tests
1. Test staging collection CRUD
2. Test hemisphere classification logic
3. Test assignment workflow
4. Test rejection workflow

### Integration Tests
1. End-to-end: Insight -> Staging -> Assignment -> Quarantine
2. Auto-classification accuracy on sample bullets
3. Manual review workflow simulation

### Test Data
```python
# Left hemisphere bullets (should classify as LEFT)
left_examples = [
    "Always validate schema before API call",
    "Check authentication token expiry",
    "Ensure required fields are present",
    "Verify response status code is 200",
]

# Right hemisphere bullets (should classify as RIGHT)
right_examples = [
    "Try exponential backoff when stuck",
    "Consider alternative API endpoints",
    "Explore edge cases first",
    "What if we reframe the problem?",
]

# Ambiguous (should flag for review)
ambiguous_examples = [
    "Use retry logic",  # Could be left (precise) or right (exploratory)
    "Handle errors gracefully",  # Generic
]
```

## Advantages

 **Clean separation**: Staging prevents premature assignment
 **Human oversight**: Optional manual review for quality
 **Cognitive integrity**: Ensures bullets match hemisphere style
 **Auditable**: Track who/what assigned each bullet
 **Flexible**: Auto-assign or manual, configurable
 **Backward compatible**: Existing code continues working

## Next Steps

1. **Decision**: Auto-assign only, manual only, or hybrid?
2. **Implementation**: Start with Phase 1 (add staging collection)
3. **Testing**: Validate classification accuracy
4. **UI**: Design review queue interface
