# Architecture

This document describes the high-level architecture of Asset Manager, the responsibilities of each layer, and the data flows between them.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Directory Structure](#directory-structure)
3. [Frontend (Client)](#frontend-client)
4. [Backend (Server)](#backend-server)
5. [Shared Layer](#shared-layer)
6. [Database Layer](#database-layer)
7. [Civic AI Operator](#civic-ai-operator)
8. [Data Flows](#data-flows)
9. [Replit Compatibility](#replit-compatibility)

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│   ┌───────────────────────────────────────────────────┐ │
│   │  React SPA  (Mission Control · Time Machine ·     │ │
│   │             Export Engine · Civic AI Panel)       │ │
│   └───────────────────────┬───────────────────────────┘ │
└───────────────────────────│─────────────────────────────┘
                            │ HTTPS / WebSocket
┌───────────────────────────▼─────────────────────────────┐
│                    Express API Server                   │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Routes    │  │   Services   │  │  AI Service   │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
└─────────│────────────────│──────────────────│───────────┘
          │                │                  │
    ┌─────▼──────┐   ┌─────▼──────┐   ┌──────▼──────┐
    │ PostgreSQL │   │   Redis    │   │ OpenAI API  │
    │  (events, │   │  (cache,   │   │  (Civic AI  │
    │  entities)│   │  pub-sub)  │   │   Operator) │
    └────────────┘   └────────────┘   └─────────────┘
```

---

## Directory Structure

```
Asset-Manager/
├── client/                  # React frontend
│   ├── public/              # Static assets
│   └── src/
│       ├── components/      # Reusable UI components
│       ├── pages/           # Top-level route components
│       │   ├── Dashboard/   # Mission-Control Dashboard
│       │   ├── TimeMachine/ # System Time Machine
│       │   ├── Export/      # Export Engine
│       │   └── AiOperator/  # Civic AI Operator panel
│       ├── lib/             # API client, hooks, utilities
│       └── main.tsx         # Application entry point
│
├── server/                  # Express backend
│   ├── routes/              # HTTP and WebSocket route handlers
│   ├── services/            # Business logic (events, export, AI)
│   ├── db/                  # Database access layer (queries, migrations)
│   └── index.ts             # Server entry point
│
├── shared/                  # Code shared between client and server
│   ├── types/               # TypeScript interfaces and enums
│   └── utils/               # Pure utility functions
│
├── docs/                    # Architecture and design documents
├── tests/                   # Integration and end-to-end tests
├── .env.example             # Environment variable template
└── package.json
```

---

## Frontend (Client)

The client is a single-page React application written in TypeScript. It is divided into four main feature areas:

### Mission-Control Dashboard
- Displays a real-time event stream pushed over WebSocket from the server.
- Renders trust-score heatmaps and operator alert banners.
- Supports filtering by entity type, severity, and time window.

### System Time Machine
- Presents a scrubable timeline that replays the event log at any historical point.
- Fetches paginated event snapshots from the `/api/events/replay` endpoint.
- State is stored locally in the component; no Redux/global store required for replay mode.

### Export Engine
- Allows any dashboard view or raw dataset to be exported as PDF, CSV, or JSON.
- PDF rendering is handled server-side; CSV and JSON are streamed directly to the browser.
- Export jobs are tracked with a progress indicator backed by a polling endpoint.

### Civic AI Operator
- Provides a chat-style interface for natural-language queries.
- Messages are sent to `/api/ai/query`; the server forwards them to the OpenAI API with a system prompt that constrains responses to the platform's data context.
- If `OPENAI_API_KEY` is not set the panel renders a graceful degradation message.

---

## Backend (Server)

The Express server exposes a REST API and a WebSocket endpoint.

| Path prefix | Purpose |
|---|---|
| `GET /api/events` | Paginated event log |
| `GET /api/events/replay` | Historical snapshot for Time Machine |
| `GET /api/entities` | Monitored entity registry |
| `POST /api/export` | Trigger an export job |
| `GET /api/export/:jobId` | Poll export job status / download result |
| `POST /api/ai/query` | Civic AI Operator chat endpoint |
| `WS /ws` | Real-time event push channel |

---

## Shared Layer

The `shared/` directory contains TypeScript types and pure utility functions that are imported by both `client/` and `server/`. This avoids duplicating type definitions and ensures the API contract is enforced at compile time on both sides.

---

## Database Layer

- **PostgreSQL** is the primary data store. It holds the immutable event log, entity registry, and export job metadata.
- **Redis** is used for:
  - Caching frequently-read entity data.
  - The pub-sub channel that fans out new events to connected WebSocket clients.
- Migrations are managed with a lightweight migration runner invoked via `npm run db:migrate`.

---

## Civic AI Operator

The AI service in `server/services/ai.ts` wraps the OpenAI Chat Completions API. Each request:

1. Loads a system prompt that describes the platform's data model and instructs the model to restrict answers to that context.
2. Appends the user's message and recent conversation history.
3. Returns the model's response to the client.

The service degrades gracefully if `OPENAI_API_KEY` is absent — it returns a static message rather than crashing.

---

## Data Flows

### Real-Time Event Ingestion

```
External source → POST /api/events/ingest
  → Validate & persist to PostgreSQL
  → Publish to Redis pub-sub channel
  → All connected WebSocket clients receive the event push
```

### Time Machine Replay

```
User selects timestamp in UI
  → GET /api/events/replay?before=<ISO timestamp>&limit=<n>
  → Server queries PostgreSQL for events up to that point
  → Client renders the reconstructed state
```

### Export Job

```
User clicks Export
  → POST /api/export { format, filters }
  → Server creates a job record in PostgreSQL (status: pending)
  → Background worker queries data, renders output file
  → Job status updated to complete; download URL returned
  → Client polls GET /api/export/:jobId until complete, then triggers download
```

---

## Replit Compatibility

Asset Manager is designed to run without modification in the Replit environment:

- **Single `npm run dev` command** starts both the frontend dev server (Vite) and the backend (ts-node-dev) via a process manager.
- **Environment variables** are read from Replit Secrets, which are exposed as `process.env` variables at runtime — no `.env` file is needed on Replit.
- **Port binding**: the server binds to `process.env.PORT || 3000`; Replit injects the correct port automatically.
- **Database**: the `DATABASE_URL` and `REDIS_URL` secrets point to Replit-managed or external database instances.
- The `.replit` and `replit.nix` files are listed in `.gitignore` so Replit-specific config does not pollute the repository.
