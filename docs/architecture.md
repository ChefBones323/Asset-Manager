# Architecture Overview

Asset Manager is a mission-control civic intelligence platform.

## Frontend (client)
- React/TypeScript dashboard and Mission Control UI
- Pages for Time Machine, Trust graph, Governance console, and AI Operator
- Shared UI components and state management

## Backend (server)
- Event-driven services for ingesting and replaying system events
- Replay / "System Time Machine" reconstruction
- Export engine (PDF/CSV/JSON) and reporting utilities
- API endpoints consumed by the dashboard

## Data
- Event log + derived views used by replay, trust analysis, and reporting
- Settings/config history for reproducible state

## Development workflow
- Code in Replit, versioned in GitHub
- Small PRs; keep features modular; do not expose secrets
