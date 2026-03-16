# Cognitive Control Plane

## Overview
The Cognitive Control Plane is a human-supervised AI execution control plane designed for managing AI-driven tasks with strict oversight. It ensures all execution steps require explicit human approval, operating within a defined state machine. Key features include autonomous lease management, heartbeat monitoring, runaway job detection, and destructive action gating. This system aims to provide transparent reasoning and robust governance over AI operations, making AI execution predictable and auditable.

## User Preferences
I want iterative development.
I prefer detailed explanations.
Do not make changes to the folder `app/social_platform/`.
Do not make changes to the file `client/src/services/api.ts`.

## System Architecture
The application features a React + TypeScript frontend with Vite, TailwindCSS, and shadcn/ui components. The backend is built with Express.js, utilizing session-based authentication. PostgreSQL serves as the database, managed by Drizzle ORM.

The system operates on a strict state machine with states: Draft, Awaiting_Approval, Approved, Running, Paused, Escalated, Completed, Failed, Cancelled. Governance is at Level 3+, incorporating human pause/resume/escalation/cancel capabilities, worker lease management, heartbeat monitoring, an autonomous watchdog, and destructive action gating.

**Key Invariants:**
1. Workers cannot approve jobs or transition non-Running states.
2. Execution requires explicit human approval.
3. Jobs must pass through `Awaiting_Approval`.
4. Pause is only from Running; Resume only from Paused/Escalated.
5. Workers cooperatively check status after each step.
6. Automatic escalation occurs if execution exceeds 2x `estimatedTimeSeconds`.
7. Worker leases expire after 30 seconds without a heartbeat.
8. Destructive jobs require explicit destructive approval.
9. Worker ID must match for updates and heartbeats.

The system includes a governed blueprint capability registry (`registry/capabilities.json`) for AI functions, with validation mechanisms to ensure consistency and correctness. Capabilities are implemented as Python modules.

A significant part of the system is the "Social Civic Infrastructure Engine" (`app/social_platform/`), which employs a deterministic event-sourcing architecture. All mutations flow through an `ExecutionEngine` to an `EventStore` and then a `ProjectionEngine`. It uses Python 3.11, FastAPI, SQLAlchemy, and PostgreSQL, with extensive administrative dashboards for event streams, feed debugging, worker health, and policy management.

**Core Invariants (Social Civic Infrastructure Engine):**
1. EventStore is append-only.
2. Event and AuditLog writes are transactional.
3. All writes originate from `ExecutionEngine` → `EventStore` → `ProjectionEngine` → Worker handlers.
4. Projection tables are exclusively written by `ProjectionEngine` handlers.
5. Workers require a valid lease.
6. Feed ranking is fully deterministic.
7. Trust scores derive only from trust_events.
8. Governance proposals execute through `ExecutionEngine`.

The UI/UX adheres to an "Industrial-Glass Dark Graphite" design with a dark palette, electric blue accent, and specific signal colors. It uses Inter, Merriweather, and JetBrains Mono fonts. The Mission Control UI features common components for cards, metrics, and modals, state management with Zustand, and services for typed API interactions and SSE websockets. Performance is a key consideration, with mechanisms like CircularBuffer and `React.memo`.

## AppShell Architecture (SPA Layout)
The UI is a persistent single-page application using an AppShell layout:
- `AppShell.tsx` — persistent shell with NavigationRail + SystemTopBar + content outlet + status bar footer
- `NavigationRail.tsx` — left vertical rail (56px collapsed, 192px on hover) with icons, active indicator, tooltips via hover-expand
- `SystemTopBar.tsx` — top bar with CIVIC MISSION CONTROL title, Compose button, connection status, event rate, palette trigger, logout
- `SocialComposer.tsx` — modal overlay for creating posts and governance proposals (no page navigation)
- All create actions open in modals; no per-page headers or back buttons
- Routes: `/dashboard`, `/governance`, `/feed`, `/trust`, `/events`, `/settings`; `/` redirects to `/dashboard`
- `CommandPalette` (Cmd+K) and `SocialComposer` are rendered at the App level, accessible from all pages
- `uiState.ts` manages `paletteOpen`, `composerOpen`, `activePage`

## Universal Social Connector Layer
Multi-platform social publishing via event-sourced worker pipeline:
- **Interface**: `interfaces/socialPost.ts` — `SocialPostPayload` (content, media, tags, platforms), `SUPPORTED_PLATFORMS` (civic, facebook, twitter, linkedin, instagram, youtube, reddit, discord)
- **Connectors**: `services/integrations/[platform]Connector.ts` — each implements `SocialConnector { platform, publish() }` interface from `connectorRegistry.ts`
- **Dispatcher**: `services/integrations/publishDispatcher.ts` — routes payloads to registered connectors, imports all connectors to trigger self-registration
- **Worker**: `workers/socialPublisherWorker.ts` — subscribes to Zustand eventStore, processes `content_created` events with `platforms` payload, dispatches to connectors, emits `[platform]_post_sent` or `platform_publish_failed` events back to eventStore
- **Composer**: `SocialComposer.tsx` has platform toggle grid; submission pushes `content_created` event to eventStore with platforms array; worker picks it up
- **Flow**: Composer → event → worker → dispatcher → connector → result events (observable in EventPulsePanel)
- **Security**: API tokens stored as env vars (FACEBOOK_TOKEN, TWITTER_API_KEY, etc.); connectors currently simulate publishing

## Intelligence Layer
Three intelligence capabilities integrated into Mission Control:

### System Time Machine (`/timeline`)
- **Service**: `services/replay/replayService.ts` — `reconstructState()` rebuilds feed/trust/governance/worker state from events up to a cursor position
- **Page**: `pages/SystemTimeline.tsx` — timeline slider, step controls, domain-colored event track, filter by domain/type/actor, jump-to-event, replay state cards (Feed, Trust, Governance, Workers), event detail modal
- **Pattern**: Combines backend-fetched events with Zustand store events; slider controls cursor position; state cards update reactively

### Print & Export Engine
- **Service**: `services/export/printService.ts` — `printGovernanceReport()`, `printFeedSnapshot()`, `printTrustGraph()`, `printEventLog()`, `printConfigurationHistory()` — each accepts `"pdf" | "csv" | "json"` format
- **Component**: `components/common/ExportMenu.tsx` — reusable dropdown with PDF/CSV/JSON options
- **Integration**: Export buttons added to GovernanceConsole, FeedDebugger, TrustGraphView, EventExplorer pages
- **Print CSS**: `styles/print.css` — media query overrides for clean printing (hides nav, normalizes glass panels)
- **Dependency**: `jspdf` for PDF generation

### Civic AI Operator (`/ai-operator`)
- **Service**: `services/ai/analysisService.ts` — `processQuery()` routes natural language to analysis functions: `analyzeFeedRanking`, `explainTrustScore`, `tracePolicyImpact`, `findInfluentialNodes`, `detectAnomalies`, `summarizeEvents`, `explainEventChain`
- **Component**: `components/ai/CivicOperatorPanel.tsx` — chat interface with suggested queries sidebar, conversation history, confidence scores, referenced event links
- **Page**: `pages/AIOperator.tsx` — wrapper for CivicOperatorPanel
- **Pattern**: Read-only analysis; never modifies system state; `AnalysisResult` has type/title/summary/details/referencedEvents/confidence

### OpenClaw Operator Runtime
- **Module**: `app/social_platform/agent_runtime/` — AI operator layer that plans tasks, selects tools, and executes actions
- **Core**: `agent_runtime.py` — `AgentRuntime` class with task pattern matching, tool execution loop, memory storage, event logging
- **Tool Registry**: `tool_registry.py` — `ToolSpec` + `ToolRegistry` for registering and listing available tools
- **Tool Router**: `tool_router.py` — routes tool calls through `PolicyGuard`; auto-approved tools execute directly, others create governance proposals via `ExecutionEngine`
- **Policy Guard**: `policy_guard.py` — approval levels: `auto` (filesystem_read, web_search), `confirmation` (browser_open, skill_run), `destructive` (filesystem_write, database_write)
- **Tools**: `tools/filesystem_read.py`, `filesystem_write.py`, `web_search.py`, `browser_open.py`, `skill_run.py` — each exposes `name`, `description`, `input_schema`, `execute()`
- **Memory**: `memory_service.py` + `models/agent_memory.py` — persistent agent memory with categories (profile/preference/project/operational/open_loop)
- **Scheduler**: `scheduler_service.py` — background task scheduler with default health check and governance report tasks
- **Config**: `config/system_prompt.yaml`, `developer_prompt.yaml`, `agent_config.yaml` — YAML-based configuration
- **Skills**: `skills/system_health_check.yaml`, `governance_audit.yaml`, `feed_analysis.yaml` — predefined multi-step tool sequences
- **Routes**: `routes_agent.py` — FastAPI endpoints: POST `/admin/agent/run`, GET/POST `/admin/agent/memory`, DELETE `/admin/agent/memory/{id}`, GET `/admin/agent/tools`, GET `/admin/agent/scheduler`, POST `/admin/agent/scheduler/{task_id}/run`
- **Frontend**: `services/agentApi.ts` (typed fetch wrapper), `components/ai/AgentTaskModal.tsx` (modal with task input, plan display, tool call steps with expand/collapse)
- **UI Integration**: `uiState.ts` has `agentModalOpen`/`agentModalTask`; `CommandPalette` has 4 `operator` category commands; `AgentTaskModal` rendered at App level
- **Governance Flow**: All write/destructive tools route through `ExecutionEngine.submit_proposal()` → governance pipeline → human approval → execution

### Worker Orchestration Layer
- **DB Models**: `models/worker_models.py` — `WorkerNode`, `JobQueueEntry`, `DeadLetterEntry` (Postgres-backed)
- **Queue Service**: `queue/job_queue_service.py` — `enqueue_job()`, `claim_job()` (with `SELECT FOR UPDATE SKIP LOCKED`), `fail_job()` (auto-DLQ after max_retries), `get_queue_depth()`, `get_stats()`
- **Worker Registry**: `workers/worker_registry.py` — `register_worker()`, `heartbeat()`, `assign_job()`, `release_job()`, `sweep_unhealthy()` (30s timeout)
- **Worker Executor**: `workers/worker_executor.py` — poll loop: heartbeat → claim → execute via ExecutionEngine → emit events → release
- **Heartbeat Monitor**: `workers/heartbeat_monitor.py` — background sweep thread for stale workers
- **Run Worker**: `workers/run_worker.py` — standalone entrypoint: reads WORKER_TOKEN, registers, starts executor loop
- **ExecutionEngine.enqueue()**: New async path that writes jobs to `JobQueueService` instead of executing synchronously; `execute()` retained for agent runtime fast-path
- **Routes**: `routes_worker.py` — GET `/admin/workers`, `/admin/workers/{id}`, `/admin/queue`, `/admin/queue/depth`, `/admin/queue/jobs`, POST `/admin/workers/register`, `/admin/workers/heartbeat`
- **Metrics**: `metrics/worker_metrics.py` — GET `/metrics` returns active_workers, busy_workers, queue_depth, jobs_processed_total, jobs_failed_total, retry_rate
- **Frontend**: `services/workerApi.ts` (typed fetch), `InfrastructurePanel.tsx` updated to use new DB-backed endpoints
- **Events**: worker_registered, worker_heartbeat, job_claimed, job_started, job_completed, job_failed, job_dlq emitted to EventStore

### Navigation & Commands
- NavigationRail: Added "Time Machine" (Clock icon) and "AI Operator" (Brain icon) nav items
- CommandPalette: Added `intelligence`, `export`, and `operator` command categories with commands for timeline, AI operator, replay, analysis, exports, and agent tasks
- Routes: `/timeline` → SystemTimeline, `/ai-operator` → AIOperator

## External Dependencies
- **Frontend Framework**: React
- **Backend Framework**: Express.js
- **Database**: PostgreSQL (via Neon)
- **ORM**: Drizzle ORM
- **UI Toolkit**: TailwindCSS, shadcn/ui
- **State Management**: Zustand
- **Charting Library**: D3 (for Trust Graph)
- **Python Framework**: FastAPI
- **Python ORM**: SQLAlchemy
- **Queueing**: Redis (with in-memory fallback)