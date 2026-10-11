---
name: frontend-tables
description: How CoopRadar builds React pages, tables, forms, and API hooks (TanStack Query + TanStack Table, server-side sort/filter/pagination, URL state, apiFetch/ApiError). Use when creating or editing any frontend page, component, table, filter bar, form, or API hook.
---

# CoopRadar frontend conventions

## Data access
- Every request goes through `src/api/client.ts`:
  - `apiFetch<T>(path, { method, json, body })` — sends cookies (`credentials: 'include'`), sets the JSON header,
    throws `ApiError` on non-2xx, returns `undefined` for 204.
  - `ApiError` has `.status`, `.code` (backend `code`, or `VALIDATION_ERROR` for 422s), `.message`.
- Wrap calls in TanStack Query hooks in `src/api/<resource>.ts` (`useX` for queries, `useDoX` for mutations).
  **No `fetch` inside components.** Mutations invalidate the query keys they affect.
- Branch on `err instanceof ApiError && err.code === 'DUPLICATE'`, never on message text.
- URLs are relative (`/api/...`). In dev, Vite proxies `/api` to the backend (`API_PROXY_TARGET`), so cookies are
  first-party; `VITE_API_URL` is only for a backend on another origin.
- Types in `src/api/*.ts` mirror the Pydantic schemas in `backend/app/schemas/`. When you change a schema, update the
  TS type in the same commit (or regenerate with `npm run gen:api` against a running API).

## Tables and lists
- TanStack Table in `manualSorting` / `manualPagination` mode — the server sorts, filters, and pages. Never sort or
  filter in the browser.
- Search, filters, sort, page, and page size live in the URL query string (`useSearchParams`, `replace: true`), so
  views are shareable and survive refresh/back. Reset to page 1 when a filter changes.
- Show skeleton rows while loading, an empty state ("no postings match — clear filters"), and an error state with retry.
- First click on a text/date column sorts ascending (TanStack default) — e.g. soonest deadline first.

## Forms
- Omit empty optional fields before sending (the API rejects `""` for enums/URLs).
- Show server errors near the form with `role="alert"`; success with `role="status"`.

## UI
- Tailwind only, mobile-first; tables collapse to cards below `md`; usable at 375 px.
- Every interactive element is keyboard reachable with a visible focus ring; inputs have labels; WCAG AA contrast.

## Tests (`frontend/tests/`, Vitest + Testing Library)
- Each table/filter component: renders rows, empty and error states, and header clicks call the sort callback.
- Mock network with `vi.stubGlobal('fetch', ...)`; never hit a real API.
- Before finishing: `npm run lint && npm run typecheck && npm test && npm run build`.
