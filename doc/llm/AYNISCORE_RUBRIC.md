# AyniScore Rubric

This rubric defines how to interpret the `AyniScore` produced by the `AyniGuard` system. It helps determine whether a prompt is fit for execution, needs revision, or should be blocked entirely.

| AyniScore | Interpretation              | Action                                                 |
|-----------|-----------------------------|--------------------------------------------------------|
| **1.00**  | Perfect mutualism            | ✅ Send to LLM                                         |
| **0.90–0.99** | Minor preferences tension     | ✅ Send with confidence; optionally annotate            |
| **0.70–0.89** | Some misalignment             | ⚠️ Send, but flag for possible refinement               |
| **0.50–0.69** | Weak Ayni compliance          | ❌ Do not send automatically; require human review      |
| **< 0.50**    | Fails Ayni test               | ❌ Block prompt; log issue and return feedback to user  |

## Modifiers and Notes

- Contradictions in Tier 1 (Immutable Context) or Tier 2 (Hard Constraints) apply a critical penalty of `-0.5`.
- Warnings in Tier 3 (Soft Preferences) subtract `-0.1` each.
- Duplicate or ambiguous directives may further reduce score by `-0.05` each.
- Repeated violations from a prompt pattern may trigger increasing severity or stricter enforcement.

This scoring framework supports Ayni-aligned systems where both human and LLM benefit, and where coherence, clarity, and respect are maintained throughout prompt execution.