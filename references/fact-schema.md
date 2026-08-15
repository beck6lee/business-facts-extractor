# Fact Schema Reference

Every extracted fact is a JSON object in the `facts` array of `facts.json`.
Enforced mechanically by `scripts/validate_facts.py`.

## Envelope

```json
{
  "version": "1",
  "project": { "name": "<project name>", "stack": ["React", "FastAPI", "PostgreSQL"], "generated_at": "<ISO-8601>" },
  "facts": [ ... ]
}
```

## Fact fields

| field | required | values / notes |
|---|---|---|
| `id` | yes | `F-0001`, `F-0002`, … unique, zero-padded, assigned in extraction order; after a fan-out merge, ids are re-assigned sequentially (see SKILL.md Phase 3) |
| `type` | yes | `entity` / `relationship` / `user_flow` / `rule` / `constraint` / `edge_case` / `discrepancy` |
| `domain` | yes | business domain from Phase 0 recon (e.g. `onboarding`, `billing`) |
| `statement` | yes | one sentence, user/business language, NOT code identifiers |
| `entities` | no | entity names involved (PascalCase, matching `entity` facts) |
| `actors` | no | user roles involved (e.g. `新员工`, `HR`) |
| `sources` | yes | non-empty list, see below |
| `enforcement` | yes | `frontend` / `backend` / `database` / `multiple` — where the fact is enforced in code |
| `confidence` | yes | `high` = explicit in code; `medium` = inferred from multiple clues; `low` = inferred from weak/ambiguous evidence — sources are still mandatory (⚠️ in the handbook) |
| `relation` | required iff `type=relationship` | `{ "from": "...", "to": "...", "cardinality": "1-1|1-N|N-1|N-N", "label": "..." }` |

## Source objects

```json
{ "file": "src/pages/Onboarding/Step2.tsx", "lines": "140-158", "kind": "frontend" }
```

- `file`: path relative to the analyzed project root (POSIX separators)
- `lines`: `"N"` or `"N-M"`, must exist in the file — cite only line numbers
  actually seen in read-tool output; never guess a file's tail line number
- `kind`: `frontend` / `backend` / `database` / `config` / `other`

## Type guide

- **entity** — a business object with a lifecycle. One fact per entity; `entities: [name]`; `statement` describes what it represents in business terms.
- **relationship** — how two entities relate. Must include `relation` (from/to/cardinality/label) so the ER diagram can be rendered.
- **user_flow** — a task an actor completes end-to-end (e.g. "新员工填写入职登记表并提交"). The `statement` summarizes the goal; the step list lives in the handbook narrative, keyed by this fact's id.
- **rule** — business logic: validation, calculation, conditional behavior (e.g. "选了异地办公才显示社保缴纳地").
- **constraint** — data-level invariants: required, unique, length, enum values.
- **edge_case** — error handling and boundary behavior (e.g. "重复提交相同身份证号返回 409").
- **discrepancy** — frontend/backend (or code/docs) disagree. **Never silently reconcile** — record both sides' sources (≥ 2 sources required).

## Per-type minimal examples

```json
{ "id": "F-0010", "type": "entity", "domain": "org", "statement": "Employee 代表一名待入职或已入职的员工", "entities": ["Employee"], "sources": [{"file": "api/models.py", "lines": "10-30", "kind": "backend"}], "enforcement": "database", "confidence": "high" }
```

```json
{ "id": "F-0011", "type": "relationship", "domain": "org", "statement": "一个部门下有多个员工，一个员工只属于一个部门", "entities": ["Department", "Employee"], "sources": [{"file": "api/models.py", "lines": "31-35", "kind": "backend"}], "enforcement": "database", "confidence": "high", "relation": { "from": "Department", "to": "Employee", "cardinality": "1-N", "label": "employs" } }
```

```json
{ "id": "F-0012", "type": "user_flow", "domain": "onboarding", "statement": "新员工分四步填写入职信息并提交，提交后不可再修改", "entities": ["Employee"], "actors": ["新员工"], "sources": [{"file": "src/pages/Onboarding/index.tsx", "lines": "1-220", "kind": "frontend"}], "enforcement": "frontend", "confidence": "high" }
```

```json
{ "id": "F-0013", "type": "rule", "domain": "onboarding", "statement": "选择异地办公时才需要填写社保缴纳地", "entities": ["Employee"], "actors": ["新员工"], "sources": [{"file": "src/pages/Onboarding/Step2.tsx", "lines": "140-158", "kind": "frontend"}], "enforcement": "frontend", "confidence": "high" }
```

```json
{ "id": "F-0014", "type": "constraint", "domain": "onboarding", "statement": "身份证号必填、18 位、全库唯一", "entities": ["Employee"], "sources": [{"file": "api/employee.py", "lines": "85-92", "kind": "backend"}, {"file": "migrations/001_init.sql", "lines": "12-12", "kind": "database"}], "enforcement": "multiple", "confidence": "high" }
```

```json
{ "id": "F-0015", "type": "edge_case", "domain": "onboarding", "statement": "重复提交相同身份证号时后端返回 409 并提示已存在", "entities": ["Employee"], "sources": [{"file": "api/employee.py", "lines": "95-101", "kind": "backend"}], "enforcement": "backend", "confidence": "high" }
```

```json
{ "id": "F-0016", "type": "discrepancy", "domain": "onboarding", "statement": "前端限制姓名最多 20 字，后端无任何长度校验", "entities": ["Employee"], "sources": [{"file": "src/pages/Onboarding/Step1.tsx", "lines": "40-42", "kind": "frontend"}, {"file": "api/employee.py", "lines": "80-84", "kind": "backend"}], "enforcement": "frontend", "confidence": "high" }
```
