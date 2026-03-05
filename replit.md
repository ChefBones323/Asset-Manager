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
- `blueprint_update_github.py` - Script to add GitHub capabilities to the governed blueprint registry (idempotent)
- `registry/capabilities.json` - Governed blueprint capability registry (7 GitHub functions)
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
