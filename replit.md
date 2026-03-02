# Cognitive Control Plane

## Overview
A human-supervised AI execution control plane with approval workflows and transparent reasoning. Implements a strict state machine where all execution requires explicit human approval.

## Architecture
- **Frontend**: React + TypeScript with Vite, TailwindCSS, shadcn/ui components
- **Backend**: Express.js with session-based authentication
- **Database**: PostgreSQL with Drizzle ORM
- **State Machine**: Draft -> Awaiting_Approval -> Approved -> Running -> Completed/Failed

## Key Invariants
1. Worker cannot approve jobs
2. Worker cannot transition non-Running states
3. Execution only occurs after human approval
4. No job skips Awaiting_Approval

## Key Files
- `shared/schema.ts` - Database schema and types (jobs table with status enum)
- `server/routes.ts` - API routes (auth, jobs CRUD, worker API)
- `server/storage.ts` - Database storage layer
- `server/proposal-builder.ts` - Simulated cognitive engine that generates proposals from intents
- `server/seed.ts` - Database seeding with sample jobs
- `server/db.ts` - Database connection (Neon/PostgreSQL)
- `client/src/pages/dashboard.tsx` - Main dashboard with proposal creation, approval, and live feed
- `client/src/pages/login.tsx` - Admin authentication page
- `client/src/components/proposal-card.tsx` - Job proposal display with approve/reject
- `client/src/components/live-feed.tsx` - Real-time execution log viewer
- `client/src/components/stats-bar.tsx` - Job status statistics
- `client/src/components/status-badge.tsx` - Status indicator badges
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
- `GET /api/worker/next` - Poll for next approved job (worker, Bearer token)
- `POST /api/worker/update` - Update running job status/logs (worker, Bearer token)

## Environment Secrets
- `ADMIN_PASSWORD` - Admin login password
- `WORKER_TOKEN` - Worker API authentication token
- `SESSION_SECRET` - Express session secret
- `DATABASE_URL` - PostgreSQL connection string

## Design
- Deep blue/indigo dark theme with cyan accent (primary: 199 89% 48%)
- Font stack: Inter (sans), Merriweather (serif), JetBrains Mono (mono)
- Terminal-inspired execution feed with green-on-dark log display
