---
title: "Frontend FastAPI Contract Wiring"
description: "Connect contract-defined FastAPI APIs to existing Next.js frontend with safe fallbacks."
status: pending
priority: P2
effort: 8h
branch: 2A202600699-HoTatBaoHoang
tags: [frontend, fastapi, contracts, integration]
created: 2026-06-01
---

## Goal
Wire Next.js to contract APIs only: sessions, cohort, diagnose, telemetry, student detail. Preserve demo fallback where useful. No `/brainstorm`.

## API Mapping
| Contract API | Backend work | Frontend route/client | UI consumer | Fallback |
|---|---|---|---|---|
| `GET /api/v1/sessions` | add schemas + endpoint from data/tool source | `GET /api/sessions` proxy or direct client helper | `SidebarUnified`, `AgentTraceViewer` session picker | mock sessions |
| `GET /api/v1/sessions/{session_id}/cohort` | add response schema wrapping cohort data | update `/api/cohort?session_id=` | `students/page.tsx` cohort + students table | `frontend/data/cohort_summary.json`, `students.json` |
| `POST /api/v1/diagnose` | keep endpoint, align response vs contract/SSE decision | existing `/api/diagnose` proxy | `ChatPanelInteractive`, trace update | current JSON/mock trace |
| `GET /api/v1/diagnose/{task_id}/telemetry` | persist in-memory/file telemetry by task_id | create `/api/diagnose/[taskId]/telemetry` | `TraceRailInteractive` historical trace | response telemetry from POST |
| `GET /api/v1/students/{student_id}?session_id=` | add schema + endpoint using student tool/data | update `/api/students/[id]?session_id=` | selected student details/report panel | mock student detail |

## Data Flow
1. UI selects `session_id` from sessions API; default first session, not hard-coded `session-cohort`.
2. Students page calls Next proxy routes with `session_id`; proxy forwards to FastAPI; transforms only status/errors, not payload shape unless existing component needs adapter.
3. Diagnose chat sends `{ session_id, query }` to Next proxy; FastAPI returns diagnosis + `task_id` + steps/telemetry; chat appends answer; trace rail receives steps immediately.
4. Telemetry rail can fetch `/api/diagnose/{task_id}/telemetry` for historical task; displays thinking logs/tool calls/metrics.
5. Student click fetches student detail by `student_id + session_id`; evidence/diagnosis/next_actions render in detail panel.

## Phases
| ID | Phase | Depends on | Files ownership | Done criteria |
|---|---|---|---|---|
| P1 | Backend contract gaps | none | `src/api/main.py`, `src/api/schemas.py`, tests under `tests/` | 4 missing FastAPI endpoints return contract payloads + 404/400 errors |
| P2 | Frontend API layer/proxies | P1 contracts known | `frontend/app/api/**`, `frontend/lib/api*.ts`, `frontend/lib/types.ts` | all proxy routes forward `session_id`, normalize unavailable backend to fallback |
| P3 | UI wiring | P2 | `frontend/components/**`, `frontend/app/u/0/**` | sessions/cohort/student/detail/telemetry use real APIs; mock only fallback |
| P4 | Diagnose streaming decision | P1,P2 | `src/api/main.py`, `frontend/app/api/diagnose/route.ts`, chat/trace files | either implement SSE per contract or document JSON compatibility adapter; no silent mismatch |
| P5 | Validation + docs sync | P1-P4 | `tests/**`, `frontend` test/build config, `docs/*` if behavior changes | backend tests pass, frontend build passes, manual flow validated |

## Phase Details
### P1 Backend contract gaps
- Add Pydantic models: `SessionSummary`, `CohortResponse`, `StudentDetailResponse`, `ToolCall`, `TelemetryResponse`.
- Implement `GET /api/v1/sessions` from available session data. Keep minimal: session id, title, concepts.
- Implement `GET /api/v1/sessions/{session_id}/cohort` via `get_session_cohort_data`; map `ValueError("SESSION_NOT_FOUND")` to contract error.
- Implement `GET /api/v1/students/{student_id}` with required `session_id`; return evidence/diagnosis/next_actions from existing analysis tools or deterministic adapter.
- Implement telemetry lookup. For demo, in-memory dict keyed by `task_id` is acceptable; optional seed from mock telemetry file only if already present.

### P2 Frontend API layer/proxies
- Create shared FastAPI fetch helper: base URL, timeout, error JSON parsing, demo fallback toggle.
- Update existing mock routes to proxy real backend first:
  - `/api/students?session_id=` -> cohort students or list endpoint adapter.
  - `/api/students/[id]?session_id=` -> student detail.
  - `/api/cohort?session_id=` -> cohort summary computed from cohort response if backend returns raw students.
  - `/api/student-groups?session_id=` and `/api/weak-concepts?session_id=` -> either diagnose-derived data or keep fallback until backend exposes through diagnose only.
- Create `/api/sessions` and `/api/diagnose/[taskId]/telemetry`.

### P3 UI wiring
- Replace hard-coded `session-cohort` with first session from `/api/sessions`; keep fallback list when unavailable.
- Pass selected `session_id` through chat, students page, cohort, groups, student details.
- Convert local report generation to call `/api/diagnose` where possible; generated report can still render locally from response.
- Trace rail: prefer live `steps`; fetch telemetry by `task_id` if selected previous result.
- Add loading/error states per panel; keep stale data visible with warning, not blank screen.

### P4 Diagnose streaming decision
- Contract says SSE; current backend/frontend use JSON. Choose one before implementation:
  - Preferred KISS: keep JSON for current UI, create explicit compatibility note in docs/contracts follow-up, because frontend already updates trace after response.
  - If strict contract required: change backend to `StreamingResponse(text/event-stream)` and update Next route/chat reader to parse `data:` events.
- Do not mix partial SSE backend with JSON frontend.

### P5 Validation
- Backend: pytest endpoint tests for success, unknown session, unknown student, prompt injection, telemetry task lookup.
- Frontend: typecheck/build; route handler tests if available; manual browser validation.
- Manual E2E matrix:
  - backend up/down fallback
  - valid/invalid session
  - student selection changes detail
  - diagnose success updates chat + trace + telemetry
  - prompt injection shows guardrail error
  - timeout/slow query shows fallback trace

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Contract says SSE but backend is JSON | High | High | Decide in P4 before UI work; implement one path end-to-end |
| Shape mismatch between FastAPI data and frontend types | High | Medium | Add adapters in `frontend/lib`, keep backend contract pure |
| No persistent telemetry store | Medium | Medium | Demo in-memory store; document reset on restart; add durable store only if required |
| Existing mock routes hide backend failures | Medium | Medium | Return `source: backend|fallback` or warning state in UI |
| Session id hard-coded across UI | High | Medium | Centralize selected session state; pass as query/body everywhere |
| Parallel edits collide | Medium | Medium | File ownership table above; P1/P2/P3 sequential unless files split |

## Backwards Compatibility
- Existing mock JSON files remain fallback; UI still works without FastAPI.
- Existing `/api/diagnose` frontend route remains stable for chat callers.
- Existing component types extended, not renamed; adapters bridge contract payload to current UI fields.
- No breaking UI route changes (`/u/0/app`, `/u/0/students` unchanged).

## Rollback
- P1: remove new endpoints/schemas; existing `/health` and `/diagnose` unaffected if changes isolated.
- P2: revert proxy helper/routes to static JSON handlers.
- P3: restore hard-coded mock session state and existing fetch URLs.
- P4: rollback SSE/JSON decision as a single commit; do not leave mixed protocol.
- P5: tests/docs only; revert independently.

## Success Criteria
- All 5 contract APIs reachable through FastAPI with expected status/error semantics.
- Next.js UI can load sessions, cohort, students, student detail, diagnose result, and telemetry from FastAPI.
- With FastAPI stopped, demo fallback still renders students page and chat error/fallback cleanly.
- `pytest` passes; frontend `pnpm build` or `pnpm typecheck` passes.
- No invented endpoints beyond Next proxy routes and contract APIs.

## Unresolved Questions
- Should `/api/v1/diagnose` strictly become SSE now, or is JSON compatibility accepted for demo?
- Where should telemetry persist after backend restart: in-memory only, JSON file, or database?
