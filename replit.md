# Cognitive Control Plane

## Overview
A human-supervised AI execution control plane with approval workflows and transparent reasoning. Implements a strict state machine where all execution requires explicit human approval. Features autonomous lease management, heartbeat monitoring, runaway detection, and destructive gating.

## Architecture
- **Frontend**: React + TypeScript with Vite, TailwindCSS, shadcn/ui components
- **Backend**: Express.js with session-based authentication
- **Database**: PostgreSQL with Drizzle ORM
- **State Machine**: Draft -> Awaiting_Approval -> Approved -> Running -> Paused/Escalated/Completed/Failed/Cancelled
- **Governance Level**: Level 3+ — Human pause/resume/escalation/cancel, worker lease management, heartbeat monitoring, autonomous watchdog, destructive gating

## Key Invariants
1. Worker cannot approve jobs
2. Worker cannot transition non-Running states
3. Execution only occurs after human approval
4. No job skips Awaiting_Approval
5. Pause only from Running, Resume only from Paused/Escalated
6. Worker cooperatively checks status after each step (pause polling, escalation exit, cancel exit)
7. Automatic escalation if execution exceeds 2x estimatedTimeSeconds (watchdog)
8. Worker lease expires after 30 seconds without heartbeat renewal
9. Destructive jobs require explicit destructive approval before worker can claim them
10. Worker ID must match for updates and heartbeats (worker isolation)

## Key Files
- `shared/schema.ts` - Database schema and types (jobs table with status enum, lease/heartbeat/destructive fields)
- `server/routes.ts` - API routes (auth, jobs CRUD, worker API, heartbeat, destructive approval)
- `server/storage.ts` - Database storage layer (includes lease management, expired/runaway queries)
- `server/index.ts` - Server startup with autonomous watchdog interval (every 5s)
- `server/proposal-builder.ts` - Simulated cognitive engine that generates proposals from intents (legacy, no longer used in job creation)
- `blueprint_update_github.py` - Idempotent script to add GitHub capabilities to the governed blueprint registry
- `registry/capabilities.json` - Governed blueprint capability registry (7 GitHub functions, sorted by ID)
- `lint/blueprint_validator.py` - Python registry validator (JSON schema, duplicates, required fields, sort order)
- `lint/validate-registry.cjs` - Node.js registry validator (same checks + module file existence verification)
- `capabilities/github/*.py` - GitHub capability function stubs (7 modules matching registry entries)
- `server/seed.ts` - Database seeding with sample jobs
- `server/db.ts` - Database connection (Neon/PostgreSQL)
- `client/src/pages/dashboard.tsx` - Main dashboard with proposal creation, approval, governance tab, and live feed
- `client/src/pages/login.tsx` - Admin authentication page
- `client/src/components/proposal-card.tsx` - Job proposal display with governance buttons and worker info
- `client/src/components/live-feed.tsx` - Real-time execution log viewer
- `client/src/components/stats-bar.tsx` - Job status statistics (9 columns)
- `client/src/components/status-badge.tsx` - Status indicator badges (paused=yellow, escalated=orange)
- `client/src/components/theme-provider.tsx` - Dark/light mode toggle
- `client/src/hooks/use-auth.ts` - Authentication hook

## API Routes
- `POST /api/auth/login` - Admin login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Check auth status
- `GET /api/jobs` - List all jobs (admin)
- `POST /api/jobs` - Create new proposal (admin)
- `POST /api/jobs/:id/approve` - Approve job (admin)
- `POST /api/jobs/:id/reject` - Reject job (admin)
- `POST /api/jobs/:id/pause` - Pause running job (admin)
- `POST /api/jobs/:id/resume` - Resume paused/escalated job (admin)
- `POST /api/jobs/:id/escalate` - Escalate running job for review (admin)
- `POST /api/jobs/:id/cancel` - Cancel active job (admin)
- `POST /api/jobs/:id/delete` - Delete terminal-state job (admin)
- `POST /api/jobs/:id/approve-destructive` - Authorize destructive execution (admin)
- `GET /api/jobs/:id/status` - Check job status (worker, Bearer token)
- `GET /api/worker/next` - Poll for next approved job (worker, Bearer token, X-Worker-Id header)
- `POST /api/worker/heartbeat` - Renew lease (worker, Bearer token, body: jobId + workerId)
- `POST /api/worker/update` - Update job status/logs (worker, Bearer token, validates workerId match)

## Schema Extensions (Lease/Governance/Manifest)
- `workerId` (text, nullable) - Assigned worker identifier
- `leaseExpiresAt` (timestamp, nullable) - Worker lease expiry (30s default)
- `lastHeartbeatAt` (timestamp, nullable) - Last heartbeat from worker
- `destructiveApprovedAt` (timestamp, nullable) - Destructive execution authorization timestamp
- `executableManifest` (jsonb, nullable) - Manifest-based execution instructions

## Executable Manifest
- Generated server-side during job creation (POST /api/jobs)
- Structure: `{ version: 1, requiresRollback: boolean, steps: [{ id, type, command, allowed }] }`
- Returned to worker via /api/worker/next
- Worker validates manifest before execution (version must be 1, steps array required)

## Worker (src/worker.py)
- Manifest-driven execution engine (Python)
- Polls /api/worker/next for approved jobs
- Validates manifest version and structure before execution
- Safe command whitelist: echo, ls, mkdir, cat, touch, python3 (single script), node (single script)
- Blocked patterns: rm, sudo, chmod, chown, >, >>, &&, ||, ;, backticks, $(, curl, wget, scp, ssh
- Blocked commands trigger escalation with reason logged
- Heartbeat every 10 seconds in background thread
- Rollback on failure: tracks created files, removes them if requiresRollback is true
- Environment: WORKER_TOKEN, WORKER_ID, API_BASE, POLL_INTERVAL

## Blueprint Registry (registry/capabilities.json)
- Governed capability registry for the control plane
- Each capability entry has: id, name, type, description, function, language, module
- Sorted by id for deterministic hashing and diff-friendly output
- Currently contains 7 GitHub capabilities:
  - `github_check_repo_initialized` — Check if a repo is initialized
  - `github_compare_commits` — Compare two commits/refs
  - `github_create_pull_request` — Create a pull request
  - `github_fetch_commit` — Retrieve commit metadata
  - `github_fetch_file` — Fetch file contents at a specific ref
  - `github_merge_pull_request` — Merge an existing pull request
  - `github_search_repository` — Search files by keywords/patterns
- Module files live at `capabilities/github/<function_name>.py` — each exports a single function matching the registry entry
- Update script: `python3 blueprint_update_github.py` (idempotent, deduplicates by id)
- Validation (Node.js, no Python required): `node lint/validate-registry.cjs`
- Validation (Python): `python3 lint/blueprint_validator.py`
- Both validators check: JSON structure, 7 required fields, no duplicate IDs/names, sort order, valid language values
- The Node.js validator additionally verifies that each module path resolves to a real file on disk
- Example usage:
  ```
  node lint/validate-registry.cjs          # validate registry (recommended, works everywhere)
  python3 blueprint_update_github.py       # add missing capabilities (idempotent)
  ```

## Social Civic Infrastructure Engine (app/social_platform/)
- **Architecture**: Deterministic event sourcing — all mutations flow through ExecutionEngine → EventStore → ProjectionEngine
- **Stack**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL
- **Entry point**: `app/social_platform/main.py` (FastAPI app, 37 routes)
- **Tests**: `python3 -m pytest app/social_platform/tests/ -v` (106 unit tests across 16 test files)
- **Projection Rebuild CLI**: `python -m app.social_platform.tools.replay_social_system [--force]`
- **Event Stream Inspector**: `GET /admin/events` (SSE streaming + paginated history), `GET /admin/event_stream` (admin UI)
- **Feed Debugger**: `GET /admin/feed_explain` (ranking explanation API), `GET /admin/feed_debugger` (admin UI)
- **Worker Health Dashboard**: `GET /admin/workers` (worker/lease/heartbeat data), `GET /admin/worker_dashboard` (admin UI with 5s auto-refresh)
- **Event Metrics**: `GET /admin/event_metrics` (events/s, domain breakdown, retry/dead-letter rates)
- **Shared Ranking**: `app/social_platform/domains/social/feed_ranking.py` — single source of truth for deterministic ranking used by both FeedGenerateWorker and FeedExplainService
- **Event Sequence Index**: `event_sequence BIGSERIAL` column on events table for stronger deterministic ordering; EventStore falls back to timestamp+event_id ordering if column unavailable

### Core Invariants (8 verified by audit)
1. EventStore is append-only (no UPDATE/DELETE)
2. append_event writes Event + AuditLog in a single transaction
3. All writes originate from ExecutionEngine → EventStore → ProjectionEngine → Worker handlers
4. No projection tables written outside ProjectionEngine handlers — services are read-only
5. Workers require a valid lease before executing (via ExecutionEngine)
6. Feed ranking is fully deterministic (epoch fallback, content_id tiebreak, no random/datetime.now)
7. Trust scores derive only from trust_events
8. Governance proposals execute through ExecutionEngine
- Additional: Approval required before execution, deterministic manifests (SHA-256), domain isolation, full audit logs, replayable state

### Phase 1 — Platform Foundation
- `app/social_platform/infrastructure/event_store.py` — Append-only event ledger with SERIALIZABLE isolation, optimistic concurrency control, auto-retry on serialization conflicts (3 attempts), transactional dual-write (events + audit_logs in single commit)
- `app/social_platform/infrastructure/projection_engine.py` — Processes events into projection tables
- `app/social_platform/infrastructure/redis_queue.py` — Redis queue with in-memory fallback
- `app/social_platform/infrastructure/worker_runtime.py` — Worker lifecycle with Pydantic manifest validation (WorkerManifest schema); invalid manifests immediately transition job to failed + audit record written; heartbeat thread runs during task execution
- `app/social_platform/models/event_models.py` — Event + AuditLog SQLAlchemy models (audit_logs references events via event_id FK)
- `app/social_platform/platform/execution_engine.py` — Orchestrates proposal→approval→manifest→lease→execute→audit
- `app/social_platform/platform/proposal_service.py` — Proposal CRUD
- `app/social_platform/platform/approval_service.py` — Approval/rejection with enforcement
- `app/social_platform/platform/manifest_compiler.py` — Deterministic manifest generation
- `app/social_platform/platform/lease_manager.py` — Lease acquire/release/renew/heartbeat (one per job); stale lease detection via heartbeat timeout; automatic recovery with retry limit (3) and dead-letter queue
- `app/social_platform/platform/audit_logger.py` — Full audit trail
- `app/social_platform/platform/replay_engine.py` — Rebuild state from events
- `app/social_platform/tools/replay_social_system.py` — CLI to wipe projection tables and rebuild from event log

### Phase 2 — Content Domain
- Content service (create_post, create_comment, add_reaction, share_post) — all generate proposals
- Events: content_created, comment_created, reaction_added, post_shared
- Projections: posts, comments, threads, reaction_summary
- Routes: POST /content/post, /content/comment, /content/react, /content/share

### Phase 3 — Feed Engine
- Deterministic ranking: timestamp × weight + reaction_count × weight + trust_score × weight + policy_weight
- Feed index table: feed_owner, content_id, policy_scope, distribution_time
- Policy engine with compiler, executor, simulator (simulate_ranking: dry-run ranking without DB commits, returns computed_score + position_changes + is_dry_run)
- Routes: GET /feed/user, POST /feed/simulate (dry-run ranking)

### Phase 4 — Trust, Delegation, Knowledge
- Trust system: trust_events + trust_profiles, scores clamped [-100, 100], recomputed from events
- Delegation graph: max depth 3, loop prevention
- Knowledge system: artifacts + citations, knowledge_score recomputed
- Routes: /api/trust/* endpoints

### Phase 5 — Governance + Admin
- governance_proposals + governance_votes tables
- Weighted voting with quorum and approval threshold
- Approved proposals trigger execution engine
- Admin dashboards: governance, moderation, policy management
- Routes: /api/governance/* endpoints

## Watchdog (Autonomous)
- Runs every 5 seconds in server startup
- Detects expired leases (leaseExpiresAt < now) and auto-escalates
- Detects runaway jobs (elapsed > 2x estimatedTimeSeconds) and auto-escalates
- Appends [WATCHDOG] log entries for transparency

## Environment Secrets
- `ADMIN_PASSWORD` - Admin login password
- `WORKER_TOKEN` - Worker API authentication token
- `SESSION_SECRET` - Express session secret
- `DATABASE_URL` - PostgreSQL connection string

## Design
- Deep blue/indigo dark theme with cyan accent (primary: 199 89% 48%)
- Font stack: Inter (sans), Merriweather (serif), JetBrains Mono (mono)
- Terminal-inspired execution feed with green-on-dark log display
