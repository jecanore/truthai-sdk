# TruthAI SDK: v0.1 Spec (DRAFT)

## Purpose
A thin Python client for the TruthAI REST API (server code: `../truth-ai/server/routes.ts`).
It lets users submit a claim, run an uncertainty analysis, and read the results.

## Decisions
- Client style: sync and async (`TruthAI` and `AsyncTruthAI`).
- HTTP library: `httpx`.
- API target: the local `truth-ai` server for now. No PyPI release until the API is stable.

## v0.1 scope
| Method | API route |
|---|---|
| `claims.create(...)` | `POST /api/claims` |
| `claims.get(id)` | `GET /api/claims/:id` |
| `claims.analyze(id)` | `POST /api/claims/:id/analyze` (returns a job id), then polls `GET /api/analyses/jobs/:jobId` until `completed` |
| `claims.analyses(id)` | `GET /api/claims/:id/analyses` |
| `claims.evidence.add(id, ...)` | `POST /api/claims/:id/evidence` |
| `claims.evidence.list(id)` | `GET /api/claims/:claimId/evidence` |

Every API response is wrapped as `{ success, data }`. The SDK unwraps `data`.

## Out of scope for v0.1
Waitlist, analytics, CSV and Excel export, system metrics, SSE streaming, calibration profiles.

## Resolved decisions: CTO calls
1. Authentication: the API has none today (no auth middleware in `truth-ai/server/`; the only `Authorization` header is an outbound waitlist call). Decision: `api_key` is optional and, when set, sent as `Authorization: Bearer <key>`. Revisit when the API adds auth.
2. Field names: `claims.create` takes `title`, `description`, `content` (all required by the schema at `truth-ai/shared/schema.ts:105-110`). Evidence takes `title`, `content`, `type` (required, `schema.ts:145-152`). Results come back as plain dicts in v0.1. Typed models wait until the API stops changing.
3. Polling: default interval 1s, timeout 120s, both configurable. A timeout raises `AnalysisTimeoutError`.
4. Failed jobs: a job state of `failed` raises `AnalysisFailedError`. Other states are treated as still running. The failed state is my assumption from BullMQ and is not confirmed in `routes.ts`.
5. Python floor: raise from 3.8 to 3.9 (3.8 is end-of-life). Confirm when `pyproject.toml` is edited.
6. `httpx`: pin `>=0.27,<1.0`. It is pre-1.0 and its last release is 2024-12-06.
7. Release policy: no PyPI release until the API is stable. The publish workflow stays untouched. The version stays 0.0.2 until then.

## Not yet verified
- No code has been run or written.
- The API has not been called.
- Claim status and evidence type enum values are not yet read.
