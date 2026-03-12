# Contributing to Asset Manager

Thank you for your interest in contributing! This document describes how to set up your development environment, the branching strategy, and the standards expected for all pull requests.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Development Environment](#development-environment)
3. [Branching Strategy](#branching-strategy)
4. [Making Changes](#making-changes)
5. [Commit Message Format](#commit-message-format)
6. [Pull Request Guidelines](#pull-request-guidelines)
7. [Code Style](#code-style)
8. [Testing](#testing)

---

## Code of Conduct

All contributors are expected to act professionally and respectfully toward one another. Harassment, discrimination, or abusive communication of any kind will not be tolerated.

---

## Development Environment

### Option A — Replit (recommended)

Asset Manager is developed primarily on [Replit](https://replit.com). All runtime dependencies (Node.js, PostgreSQL, Redis) are pre-configured in the Replit environment.

1. Fork the repository on GitHub.
2. Import your fork into Replit via **Create Repl > Import from GitHub**.
3. Add the required secrets in the **Secrets** panel (see `.env.example` for the full list).
4. Click **Run** — dependencies are installed and the dev server starts automatically.

### Option B — Local / VS Code

1. Install Node.js >= 18, PostgreSQL >= 14, and Redis >= 7.
2. Clone the repository and run `npm install`.
3. Copy `.env.example` to `.env` and fill in the required values.
4. Run `npm run db:migrate` to apply database migrations.
5. Run `npm run dev` to start the development server.

---

## Branching Strategy

| Branch pattern | Purpose |
|---|---|
| `main` | Stable, production-ready code |
| `develop` | Integration branch for upcoming release |
| `feature/<short-description>` | New features or enhancements |
| `fix/<short-description>` | Bug fixes |
| `chore/<short-description>` | Tooling, dependency updates, or housekeeping |
| `docs/<short-description>` | Documentation-only changes |

All work should branch off `develop` and be merged back via a pull request. Direct pushes to `main` are not allowed.

---

## Making Changes

1. Create a branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-new-feature
   ```
2. Make your changes, keeping each commit focused on a single logical unit.
3. Run the test suite locally before pushing:
   ```bash
   npm test
   ```
4. Push your branch and open a pull request against `develop`.

---

## Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**

```
feat(export-engine): add JSON export format
fix(time-machine): correct off-by-one in event replay cursor
docs(architecture): update data-flow diagram
```

---

## Pull Request Guidelines

- **Title** must follow the commit message format above.
- Include a clear description of *what* changed and *why*.
- Reference any related issues using GitHub keywords (e.g. `Closes #42`).
- Ensure all CI checks pass before requesting a review.
- At least one approving review is required before merging.
- Squash-merge into `develop`; merge commits are used when promoting `develop` to `main`.

---

## Code Style

- **TypeScript**: strict mode enabled; no `any` types without a comment justifying the exception.
- **Formatting**: [Prettier](https://prettier.io/) with project defaults (`npm run format`).
- **Linting**: [ESLint](https://eslint.org/) with the project config (`npm run lint`).
- **Imports**: absolute imports using the configured path aliases; no relative `../../../` chains.

---

## Testing

- Unit tests live alongside the source files they test (`*.test.ts`).
- Integration tests live in the `tests/` directory at the project root.
- Run all tests: `npm test`
- Run tests with coverage: `npm run test:coverage`

New features should include unit tests. Bug fixes should include a regression test that reproduces the original issue.
