# Copilot instructions

This repository is actively developed in Replit and versioned in GitHub. Copilot should make small, production-safe changes and avoid sweeping rewrites.

## Project context
Asset Manager is a civic intelligence and mission-control dashboard for monitoring governance activity, event-driven system activity, trust networks, and worker operations.

## Working rules
- Preserve existing architecture and naming unless there is a strong reason to improve it.
- Keep the app compatible with Replit workflows and deployment.
- Do not hardcode or expose secrets.
- Use environment variables for sensitive config.
- Prefer TypeScript-safe changes and modular components.
- Minimize route changes; keep exports, event replay, and analytics stable.

## Output style for Copilot
1. Summarize the requested change.
2. Identify files likely involved.
3. Provide code changes.
4. Note dependencies/env updates.
5. Flag risks/testing steps.

## Feature guidance
- Inspect relevant files first; extend the current architecture rather than replacing it.
- For large changes, provide an implementation plan before touching many files.
- For debugging, show the smallest fix that preserves behavior.

## Avoid
- Introducing new external dependencies without justification.
- Global refactors driven by stylistic preference.
- Unapproved destructive actions.
