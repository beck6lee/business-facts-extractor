---
name: business-facts-extractor
description: Extract auditable business facts from a codebase (frontend, backend, and/or DB schema; frontend-only supported). Produces BUSINESS_FACTS.md (human-readable handbook with Mermaid diagrams) and facts.json (machine-readable, every fact carries file:line sources). Covers user task flows, entity relationships, business rules (validation/state machines/permissions), and edge cases. Use when asked to 识别业务逻辑 / 输出业务事实 / document what a system does from its code / business spec from code.
---

# Business Facts Extractor

Turn code into an auditable statement of business facts. Every claim carries a
`file:line` source; anything that can't be sourced doesn't get written.

## Input / Output

- **Input:** path to a project root (default: current working directory)
- **Output:** `<project>/BUSINESS_FACTS.md` and `<project>/facts.json`
- `<skill_dir>` below = the directory containing this SKILL.md

## Pipeline

Run phases in order. Read `references/recon.md`, `references/fact-schema.md`,
and `references/authoring.md` at the phase where they're needed.

### Phase 0 — Recon (read `references/recon.md`)

1. Detect stack(s) from marker files.
2. Build the three inventories: data models, backend route table, frontend pages.
3. Partition into business domains.
4. Scale decision: ≤ 30 source files or ≤ 2 domains → **degraded path** (do
   everything yourself, sequentially). Otherwise **fan-out path** (subagents in
   Phase 2).

### Phase 1 — Data model (bottom-up; read references/fact-schema.md first)

Read schemas/migrations/ORM models. Emit `entity` and `relationship` facts
(with `relation` objects). No DB found → skip, and note it in the appendix
coverage report. Frontend-only projects: entity shapes embedded in forms/state
still count — extract them as entities with `kind: frontend` sources.

### Phase 2 — Per-domain deep-read

Every subagent prompt must embed the full fact schema from
`references/fact-schema.md` (already read in Phase 1).

- **Degraded path:** for each domain, read its routes → handlers → pages/forms.
  Accumulate facts into `<project>/facts.json` as you go. Record sources
  at the moment you read the code — never backfill line numbers from memory.
- **Fan-out path:** dispatch one subagent per domain. The subagent prompt must
  include the domain's route/page/model file list (plus the embedded schema,
  per above). Have the subagent write the facts array to a scratch file
  scoped per project and domain (e.g. `/tmp/bfe-<project>-<domain>.json`,
  avoiding collisions) and return ONLY the scratch file path — more robust
  than parsing chat output; fall back to returning the JSON array itself
  if the write fails.
  Run `scripts/validate_facts.py` on each returned array (wrapped in
  the envelope). On failure:
  - If the errors are only source line ranges that overrun the file's actual
    length by a few lines (≤ 5 lines; subagents often guess tail lines), the
    orchestrator may re-read the implicated files itself and fix the ranges
    in place, confirming each fact's statement is still supported by the
    corrected range — clamping a range to EOF without re-checking the
    statement is not a fix. This still satisfies "recorded while reading".
    Then re-run the validator. Larger overruns or structural errors →
    redispatch (max 2 retries, then blind spot) as before.
  - Otherwise redispatch with the error output — max 2 retries,
    then record the domain as a blind spot in the appendix.

Hunt for: API contracts, input validation, permission middleware/decorators,
frontend form rules, field linkage logic, enum-driven state machines, error
branches. Frontend vs backend rule mismatch → `discrepancy` fact with both
sides' sources. Never reconcile silently.

### Phase 3 — Reconcile & verify

1. Merge all facts; dedupe identical statements (keep richest sources).
   Re-assign ids sequentially (`F-0001`, `F-0002`, …) after merging —
   subagent-scoped ids collide.
2. Coverage check: every route-table entry and page from Phase 0 must appear in
   at least one fact's sources. Unreferenced ones go to the appendix 盲区清单.
3. Citation spot-check: the validator proves a line range exists, not that it
   supports the statement. Re-read a random sample of ≥ 5% of facts (minimum
   5), one source each, and confirm the cited lines actually back the
   statement. Fix the range or delete the fact on failure; if more than one
   sampled fact from the same domain fails, re-check that entire domain.
4. Run:
   ```bash
   python3 <skill_dir>/scripts/validate_facts.py <project>/facts.json --root <project>
   ```
   Must print `OK`. Fix and re-run until it passes.

### Phase 4 — Author (read `references/authoring.md`)

1. Write the prose parts of `BUSINESS_FACTS.md`: section 1 (overview),
   section 2 (actor×task matrix + user-flow narratives with Mermaid
   flowcharts), section 3 entity field tables (the ER diagram embed is
   mechanical, step 2).
2. Generate mechanical sections:
   ```bash
   python3 <skill_dir>/scripts/render_md.py <project>/facts.json --section er
   python3 <skill_dir>/scripts/render_md.py <project>/facts.json --section rules
   ```
   Embed the output verbatim into sections 3 (ER) and 4 (rules).
3. Section 5 narrative on dangerous edge cases; section 6 appendix with
   coverage report and blind spots.
4. Final pass: every rule/edge-case/constraint line in the md has a source;
   every `low` confidence fact shows ⚠️.

## Hard rules

- **No source, no fact.** A claim without `file:lines` is deleted, not kept.
  Low-confidence facts still require sources — `low` marks uncertain
  interpretation, never missing evidence.
- Line numbers are recorded while reading, never reconstructed afterwards.
- Discrepancies are recorded, never resolved by the agent.
- md and json stay in sync: mechanical md sections come from `render_md.py`.
