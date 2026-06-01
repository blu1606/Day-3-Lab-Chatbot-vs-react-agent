---
title: "Real AI Provider with Real Tools over Demo Data"
description: "Replace canned mock provider with real LLM provider and ReAct tool flow while keeping current demo dataset as the source of truth."
status: pending
priority: P1
effort: 4h
branch: 2A202600699-HoTatBaoHoang
tags: [backend, ai, fastapi, react-agent, demo-data]
created: 2026-06-01
---

# Real AI Provider with Real Tools over Demo Data

## Context
Current frontend can call FastAPI `/api/v1/diagnose`, but backend still has mock/canned AI behavior in the diagnose path. Latest code already includes real AI building blocks: provider classes, `ReActAgent`, and Python diagnostic tools. The intended architecture is not fully production data yet. It should use real AI and real tool logic, while tools still read current demo/mock dataset.

## Target Architecture

```text
Next.js UI
→ FastAPI /api/v1/diagnose
→ Real LLM provider: OpenAI | Gemini | Local
→ Real ReActAgent loop
→ Real Python diagnostic tools
→ Demo/mock dataset: data/students.json or current session demo data
→ AI-generated mentor-facing answer + structured deterministic API payload
```

## What “Real” Means Here

| Layer | Target state | Notes |
|---|---|---|
| LLM provider | Real | Use `OpenAIProvider`, `GeminiProvider`, or `LocalProvider`, not `MockProvider`. |
| Agent loop | Real | Use `ReActAgent` to call tools and produce final answer. |
| Tools | Real | Tool functions run actual Python logic: risk detection, grouping, remediation. |
| Data source | Demo/mock for now | Tools use `data/students.json` / current demo session data, not DB yet. |
| Frontend | Real API path | Frontend calls FastAPI through Next proxy; mock trace only fallback/dev mode. |

## Non-goals
- Do not replace demo data with database yet.
- Do not make LLM generate structured fields like `student_groups` or `remediation_plan`.
- Do not reintroduce `/brainstorm`.
- Do not silently fall back to `MockProvider`.
- Do not implement SSE unless separately required.

## Existing Code to Reuse

### AI Providers
- `src/core/llm_provider.py` — provider interface.
- `src/core/openai_provider.py` — real OpenAI provider.
- `src/core/gemini_provider.py` — real Gemini provider.
- `src/core/local_provider.py` — local GGUF provider.

### Agent
- `src/agent/agent.py` — `ReActAgent` loop with tool execution.
- `src/agent/chat_cli.py` — reference for `.env`, OpenAI config, demo tools.

### Tools
- `src/tools/cohort_diagnostic_tools.py`
- `src/tools/student_analysis_tools.py`
- `src/tools/__init__.py`

### API / Frontend
- `src/api/main.py` — FastAPI diagnose endpoint.
- `src/api/schemas.py` — API response schema.
- `frontend/app/api/diagnose/route.ts` — Next proxy to FastAPI.
- `frontend/components/chat-panel-interactive.tsx` — chat UI calling `/api/diagnose`.

## API Behavior

### `POST /api/v1/diagnose`
Input stays:

```json
{
  "session_id": "session-03",
  "query": "Hãy chẩn đoán lớp và đề xuất hành động cho mentor"
}
```

Output stays structured:

```json
{
  "task_id": "diag-...",
  "session_id": "session-03",
  "summary": "AI-generated Vietnamese mentor answer",
  "student_groups": [],
  "remediation_plan": [],
  "telemetry": {},
  "steps": []
}
```

Important rule:
- `summary` comes from real AI.
- `student_groups`, `remediation_plan`, and core metrics come from deterministic tools.

## Implementation Phases

## Phase 1 — Confirm and clean provider configuration

### Files
- `src/api/main.py`
- `.env.example`
- `requirements.txt` or `src/pyproject.toml`

### Steps
1. Load `.env` in FastAPI path.
2. Read:
   - `DEFAULT_PROVIDER`
   - `DEFAULT_MODEL`
   - `OPENAI_API_KEY`
   - `GEMINI_API_KEY`
   - `LOCAL_MODEL_PATH`
3. Add provider factory:
   - `openai` → `OpenAIProvider`
   - `google` / `gemini` → `GeminiProvider`
   - `local` → `LocalProvider`
4. Do not instantiate provider at import time.
5. Missing provider config returns flat HTTP `503`:

```json
{
  "error_code": "AI_PROVIDER_NOT_CONFIGURED",
  "message": "Real AI provider is not configured. Set OPENAI_API_KEY or configure DEFAULT_PROVIDER."
}
```

### Done criteria
- No `MockProvider` in normal diagnose runtime path.
- API starts even when key is missing.
- Missing key fails clearly only when diagnose needs real AI.

## Phase 2 — Wire ReActAgent into diagnose endpoint

### Files
- `src/api/main.py`
- `src/agent/agent.py`

### Steps
1. Keep existing deterministic pipeline:
   - `get_session_cohort_data`
   - `analyze_concept_mastery`
   - `detect_learning_risks`
   - `group_students`
   - `generate_remediation_plan`
2. After these results exist, build API-local ReAct tools:
   - `get_diagnosis_snapshot({})`
   - optional `get_student_detail_for_session({"student_id": "..."})`
3. Build `ReActAgent(llm=provider, tools=tools, max_steps=3)`.
4. Build a strict prompt:
   - answer Vietnamese
   - use tools before final answer
   - do not invent student data
   - explain claim → evidence → recommendation
   - do not change structured groups/remediation
5. Set response `summary` to `agent.run(prompt)`.

### Done criteria
- AI summary changes based on real provider output.
- Agent uses tool observations from demo data.
- Structured response remains stable and deterministic.

## Phase 3 — Telemetry and trace alignment

### Files
- `src/agent/agent.py`
- `src/api/main.py`

### Steps
1. Add provider metadata into `ReActAgent.history`:

```python
{
  "step": 1,
  "prompt": "...",
  "response": "...",
  "usage": result.get("usage", {}),
  "provider": result.get("provider", "unknown"),
  "latency_ms": result.get("latency_ms", 0),
}
```

2. Aggregate telemetry in API:
   - prompt tokens
   - completion tokens
   - total tokens
   - total AI latency
3. Update `thinking_logs` wording:
   - no “mock provider” text
   - mention real provider + ReAct tool flow
4. Add trace step for real AI summary generation.

### Done criteria
- Telemetry is nonzero when provider succeeds.
- Trace clearly shows real provider path.
- No mock wording in live response.

## Phase 4 — Runtime fallback policy

### Files
- `src/api/main.py`
- `src/api/schemas.py` if needed

### Policy
- Prompt injection: keep `400 PROMPT_INJECTION_DETECTED`.
- Bad session: keep `404 SESSION_NOT_FOUND`.
- Missing provider config: return `503 AI_PROVIDER_NOT_CONFIGURED`.
- Provider runtime failure: return `200 DiagnoseResponse` with:
  - deterministic fallback summary
  - `telemetry.is_fallback_triggered = true`
  - trace step `errorCode = AI_PROVIDER_ERROR`

### Done criteria
- No silent mock fallback.
- Frontend can show fallback but knows AI failed.
- Structured tool output still available during provider failure.

## Phase 5 — Frontend behavior check

### Files
- `frontend/app/api/diagnose/route.ts`
- `frontend/components/chat-panel-interactive.tsx`
- `frontend/components/trace-rail-interactive.tsx`

### Steps
1. Keep frontend calling `/api/diagnose`.
2. Ensure 503 flat payload displays clear error.
3. Keep local mock trace only as explicit fallback/dev mode, not as hidden “success”.
4. Ensure trace rail receives custom trace from real API response.

### Done criteria
- User can see when real provider is not configured.
- Successful call shows AI-generated summary.
- Failed backend does not pretend to be real AI.

## Validation

### Static checks
```powershell
python -m compileall src
pnpm --dir frontend build
```

### Backend tests
```powershell
python -m pytest
```

### FastAPI checks without AI key
```powershell
python -c "from fastapi.testclient import TestClient; from src.api.main import app; c=TestClient(app); r=c.post('/api/v1/diagnose', json={'session_id':'session-03','query':'Chẩn đoán cohort'}); print(r.status_code, r.json())"
```

Expected:
- `503 AI_PROVIDER_NOT_CONFIGURED` if no real provider config exists.

### FastAPI checks with real key
```powershell
$env:DEFAULT_PROVIDER='openai'
$env:OPENAI_API_KEY='<real-key>'
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/diagnose' `
  -ContentType 'application/json' `
  -Body '{"session_id":"session-03","query":"Hãy chẩn đoán lớp và đề xuất hành động cho mentor"}'
```

Expected:
- `summary` is real AI text.
- `student_groups` populated by Python tools.
- `remediation_plan` populated by Python tools.
- `telemetry.prompt_tokens > 0`.
- `steps` include real AI summary step.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| LLM does not follow `Action:` format | Agent may hit max steps | Use strict prompt, `max_steps=3`, deterministic fallback on runtime failure. |
| Tests accidentally call real API | Cost / flaky tests | Monkeypatch provider or agent in tests. |
| AI invents data | Misleading diagnosis | Feed only tool snapshot; structured fields remain deterministic. |
| Missing env key breaks app startup | Bad DX | Lazy provider creation inside request. |
| Frontend silently falls back to mock | User thinks AI works | Show explicit provider/config error. |

## Success Criteria
- `/api/v1/diagnose` no longer uses `MockProvider` in normal runtime.
- Real configured provider produces the mentor-facing `summary`.
- ReActAgent uses real Python tools over demo data.
- Demo data remains current source of truth until DB/API work is planned.
- Frontend clearly distinguishes real AI response from fallback/error.
