# Asset Manager

> **Civic Intelligence Dashboard** — Real-time governance monitoring, event replay, and AI-assisted policy analysis.

---

## Overview

Asset Manager is a full-stack civic intelligence platform built to give operators, analysts, and administrators a single pane of glass over governance activity, system events, and trust networks. It surfaces structured insight through four integrated modules:

| Module | Description |
|---|---|
| **Mission-Control Dashboard** | Live feed of governance events, trust-score heatmaps, and operator alerts across monitored entities |
| **System Time Machine** | Scrubable event-replay engine that reconstructs any past system state from an immutable audit log |
| **Export Engine** | One-click export of any view or dataset to PDF, CSV, or JSON for offline analysis and compliance reporting |
| **Civic AI Operator** | Embedded AI analysis panel that answers natural-language queries about system behavior, policy impact, and anomaly detection |

---

## Tech Stack

- **Frontend**: React · TypeScript · Tailwind CSS
- **Backend**: Node.js · Express · TypeScript
- **Database**: PostgreSQL (primary store) · Redis (caching / pub-sub)
- **AI Layer**: OpenAI API (Civic AI Operator)
- **Dev Environment**: [Replit](https://replit.com) (primary) · VS Code compatible
- **CI/CD**: GitHub Actions

---

## Getting Started

### Prerequisites

- Node.js >= 18
- npm >= 9 (or pnpm / yarn)
- PostgreSQL >= 14
- Redis >= 7
- An OpenAI API key (optional — AI panel degrades gracefully without it)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ChefBones323/Asset-Manager.git
cd Asset-Manager

# 2. Install dependencies
npm install

# 3. Configure environment variables
cp .env.example .env
# Edit .env and fill in your database URL, Redis URL, and API keys

# 4. Run database migrations
npm run db:migrate

# 5. Start the development server
npm run dev
```

The app will be available at `http://localhost:3000` by default.

### Running on Replit

1. Open the project in Replit.
2. Set the required environment variables in the **Secrets** panel (see `.env.example`).
3. Click **Run** — Replit will install dependencies and start the dev server automatically.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `OPENAI_API_KEY` | No | OpenAI key for the Civic AI Operator |
| `SESSION_SECRET` | Yes | Secret used to sign session cookies |
| `NODE_ENV` | Yes | `development`, `production`, or `test` |
| `PORT` | No | HTTP port (default `3000`) |

> **Warning:** Never commit `.env` or any file containing real secrets. The `.gitignore` in this repo excludes them by default.

---

## Project Structure

```
Asset-Manager/
├── client/          # React frontend (TypeScript)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   └── public/
├── server/          # Express backend (TypeScript)
│   ├── routes/
│   ├── services/
│   └── db/
├── shared/          # Types and utilities shared by client & server
├── docs/            # Architecture diagrams and design documents
├── .env.example     # Template for required environment variables
└── README.md
```

See [docs/architecture.md](docs/architecture.md) for a detailed description of each layer.

---

## Contributing

Pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

---

## License

This project is licensed under the [MIT License](LICENSE).
