# Phase 0 Recon Cheatsheet

Goal of recon: build the **project map** without deep-reading business code.
Use fast file listings and targeted greps only. Output: stack list, route table,
model list, page list, domain partition.

## Stack detection

| stack | marker files | framework hints |
|---|---|---|
| Node/TS frontend | `package.json` | `next` → `app/` or `pages/`; `react-router` → route config in src; `vue`/`nuxt` → `pages/` |
| Node backend | `package.json` | `express`/`fastify` → `routes/`, `app.use(`; `nestjs` → `*.controller.ts` |
| Python | `requirements.txt` / `pyproject.toml` | `fastapi` → `@app.get|@router.`; `django` → `urls.py`, `models.py`; `flask` → `@app.route` |
| Java | `pom.xml` / `build.gradle` | Spring → `@RestController`, `@Entity` |
| Go | `go.mod` | `gin`/`echo` → `router.`, `*.HandleFunc` |
| Ruby | `Gemfile` | Rails → `config/routes.rb`, `app/models`, `db/migrate` |

**Monorepo / mixed stack:** multiple marker files in subdirectories (e.g.
`frontend/package.json` + `api/pyproject.toml`) mean multiple stacks — detect
each subtree independently, build one combined route table (prefixed by
subtree), and treat the repo as one project for domain partitioning.

## Where to find the three inventories

**Data models (Phase 1 input):**
- SQL DDL / migrations: `migrations/`, `db/migrate/`, `*.sql`, `alembic/versions/`
- ORM models: `models.py`, `app/models/`, `*.entity.ts`, `prisma/schema.prisma`, `schema.rb`, `@Entity` classes, Django `models.Model` subclasses

**Backend routes:**
- Grep: `@app.(get|post|put|delete|patch)`, `@router.`, `@RequestMapping|@GetMapping|@PostMapping`, `router.(GET|POST)`, `path(` in `urls.py`, `resources?` in `routes.rb`
- Record: HTTP method + path + handler file — this becomes the **route table** used for coverage checking in Phase 3

**Frontend pages/flows:**
- Route files: `app/**/page.tsx` (Next), `pages/`, router config (`createBrowserRouter`, `routes: [`)
- Multi-step forms / wizards: grep `step`, `Stepper`, `wizard`, `currentStep`

## Domain partition

Cluster routes/pages into business domains by URL prefix or module directory
(`/api/employees/*`, `/api/billing/*` → `employees`, `billing`). Each domain =
one Phase 2 analysis unit. Aim for 3–10 domains; merge tiny ones, split huge ones.

## Scale decision (degraded vs fan-out)

Count source files (exclude `node_modules`, tests, lockfiles):

- **≤ 30 source files OR ≤ 2 domains** → degraded path: main agent analyzes
  sequentially, no subagents
- **otherwise** → fan-out: one subagent per domain in Phase 2

Single-file projects (e.g. a lone `index.html`) are the extreme degraded case:
Phase 1 finds no data model — record "无独立数据模型，字段定义内嵌于前端" in the
coverage report and continue.

## Recon output format (kept in agent context, feeds Phase 2 prompts)

```
STACK: [React SPA (vite), FastAPI, PostgreSQL + SQLAlchemy]
ROUTE TABLE: POST /api/employees → api/employee.py:70 ; GET /api/departments → api/dept.py:12 ; ...
MODELS: api/models.py (Employee, Department) ; migrations/001_init.sql
PAGES: src/pages/Onboarding/* (4-step wizard) ; src/pages/Admin/*
DOMAINS: onboarding (routes 1-3, pages Onboarding/*) ; admin (routes 4-6, pages Admin/*)
SCALE: 87 source files, 2 domains → degraded path
```
