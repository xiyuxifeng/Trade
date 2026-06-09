# WEB-S9-001 Deployment Topology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write a production deployment topology for the Web stack that clearly explains API, frontend, worker, database, file storage, logs, and configuration injection in both single-machine and intranet deployment modes.

**Architecture:** Keep this task documentation-first. The plan should describe the runtime as four explicit pieces: FastAPI API, Web static frontend, Job Worker, and PostgreSQL-backed storage. Redis stays a candidate, not a requirement. The deployment doc should map those pieces to the existing `Dockerfile`, `docker-compose.yml`, `README.md`, and `web/README.md`, and should explain what is already supported versus what is only a future option.

**Tech Stack:** Markdown documentation, existing Docker/Compose files, current FastAPI + React + Vite runtime model.

---

### Task 1: Write the deployment topology document

**Files:**
- Create: `trade-strategy-ai/docs/WebDeployment.md`
- Modify: `trade-strategy-ai/docs/web-plan.md`

- [ ] **Step 1: Draft the topology sections**

Add a new `docs/WebDeployment.md` with these sections in order:

1. `# Web 部署拓扑`
2. `## 1. 目标和范围`
3. `## 2. 运行时组件`
4. `## 3. 单机本地部署`
5. `## 4. 内网部署`
6. `## 5. 配置与密钥注入`
7. `## 6. 文件目录约定`
8. `## 7. 日志与产物`
9. `## 8. Worker 运行方式`
10. `## 9. 暂不引入 Redis 的说明`
11. `## 10. 迁移和启动顺序`

The content should explicitly describe:
- API service: `uvicorn api.main:app`
- Web service: `web/` built with Vite, served as static assets after build
- Job Worker: separate process that polls the database and executes jobs
- PostgreSQL: primary persistence for jobs, settings, backups, and metadata
- Redis: optional future queue candidate, not part of the default topology

Add a concise topology diagram in fenced text:

```text
Browser -> Web static assets -> FastAPI API -> Services -> PostgreSQL
Browser -> FastAPI UI API -> Services -> PostgreSQL
Worker -> PostgreSQL
```

Document two deployment modes:
- Single-machine local deployment, with one API process, one worker, one PostgreSQL instance, and built frontend assets
- Intranet deployment, with the same logical components behind a reverse proxy

Document directory conventions:
- `config/`
- `data/`
- `logs/`
- `web/dist/`
- `data/backups/`
- `data/artifacts/`

Document configuration injection:
- environment variables
- `.env`
- `config/app.yaml`
- API keys and cookies kept out of Git

- [ ] **Step 2: Reconcile the doc with existing files**

Update `docs/web-plan.md` so the Stage 9 section points to `docs/WebDeployment.md` as the canonical deployment topology reference, and mention that `WEB-S9-001` defines the baseline topology used by the later Stage 9 tasks.

- [ ] **Step 3: Verify the document against the current repository**

Run:
`rg -n "WebDeployment|docker-compose|uvicorn api.main:app|web/dist|data/backups|data/artifacts|Job Worker|Redis" trade-strategy-ai/docs trade-strategy-ai/README.md trade-strategy-ai/web/README.md`

Expected:
- The new deployment terms appear in `docs/WebDeployment.md`
- The references in `docs/web-plan.md` remain consistent with the doc
- No stale claim says Redis is required by default

- [ ] **Step 4: Confirm the topology matches the current runtime**

Check the existing `Dockerfile`, `docker-compose.yml`, `README.md`, and `web/README.md` to ensure the doc does not promise unsupported commands or services.

Expected baseline facts to preserve:
- `docker-compose.yml` currently provides PostgreSQL and optional Redis only
- `README.md` still describes local Python install and CLI-driven flows
- `web/README.md` still describes Vite dev mode and `/api/ui/v1`

### Task 2: Align the task list wording with the deployment doc

**Files:**
- Modify: `trade-strategy-ai/docs/Web-TaskList.md`

- [ ] **Step 1: Update `WEB-S9-001` completion criteria wording if needed**

Keep the task focused on deployment topology, but ensure the output explicitly says:
- production deployment说明
- single-machine local deployment mode
- intranet deployment mode
- worker/database/logs/artifacts/config injection

- [ ] **Step 2: Keep the stage ordering consistent**

If `docs/web-plan.md` mentions Stage 9 as the deployment reference for later tasks, make sure `WEB-S9-002` through `WEB-S9-006` still point back to this topology doc instead of duplicating the architecture.

### Task 3: Verify and close `WEB-S9-001`

**Files:**
- Modify: `trade-strategy-ai/docs/Web-TaskList.md`
- Modify: `trade-strategy-ai/docs/web-plan.md`

- [ ] **Step 1: Run the documentation consistency check**

Run:
`rg -n "WEB-S9-001|WebDeployment|生产部署拓扑|单机本地部署|内网部署" trade-strategy-ai/docs`

Expected:
- `WEB-S9-001` points to the new deployment doc
- Stage 9 wording is consistent across the task list and web plan

- [ ] **Step 2: Mark the task complete**

Update `WEB-S9-001` completion status to `[x]` once the doc exists and the references are aligned.

- [ ] **Step 3: Commit the documentation change**

Use a commit message like:
`docs: add web deployment topology`

