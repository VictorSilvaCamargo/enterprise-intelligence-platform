# ADR-005: Use React, TypeScript, and Vite for the Frontend Application

## Status
Accepted

## Date
2026-11-19

## Context
The frontend must present a responsive, accessible enterprise SaaS interface capable of growing into rich knowledge management, BI visualization, and workflow studio views while enforcing strict type safety and fast developer iteration on Windows and Linux.

## Decision
Use **React 19**, **TypeScript (strict mode)**, and **Vite 8**, paired with **ESLint 10**, **Prettier 3**, and **Vitest 5 + Testing Library**, served in containers via **Nginx 1.27-alpine**.

## Alternatives Considered

### Next.js (Full-Stack SSR)
- **Pros:** Server-side rendering and built-in API routes.
- **Cons:** Duplicates routing/BFF responsibilities already owned cleanly by FastAPI, and increases container build/runtime complexity when Python owns the backend.
- **Rejected:** A decoupled SPA talks directly to FastAPI's typed OpenAPI contracts with minimal complexity.

### Vanilla JavaScript / Unstyled Templates
- **Pros:** Zero build step.
- **Cons:** Lacks compile-time type contracts and component modularity needed for multi-stage enterprise UIs.
- **Rejected:** TypeScript strict checking and modular CSS Modules prevent regressions as UI scope grows.

## Consequences
- Sub-second production bundling and instant local HMR with Vite.
- Clean separation between `config/`, `services/`, `hooks/`, `layouts/`, `components/`, and `pages/`.
- Strict linting (`eslint-plugin-react-hooks` + `typescript-eslint`) and formatting (`prettier`) ensure uniform code quality.
