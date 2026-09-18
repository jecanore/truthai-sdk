import asyncio
import json

import httpx
import pytest

from truthai_sdk import (
    AnalysisFailedError,
    AnalysisTimeoutError,
    APIError,
    AsyncTruthAI,
    TruthAI,
)


def make_handler(job_states, seen):
    """Fake server. `job_states` is consumed one per job poll."""
    states = list(job_states)

    def handler(request):
        seen.append(request)
        path, method = request.url.path, request.method
        if method == "POST" and path == "/api/claims":
            return httpx.Response(201, json={"success": True, "data": {"id": "c1"}})
        if method == "GET" and path == "/api/claims/missing":
            return httpx.Response(404, json={"error": "Claim not found"})
        if method == "POST" and path == "/api/claims/c1/analyze":
            return httpx.Response(
                202, json={"success": True, "data": {"jobId": "j1", "claimId": "c1", "state": "waiting"}}
            )
        if path == "/api/analyses/jobs/j1":
            state = states.pop(0) if len(states) > 1 else states[0]
            data = {"jobId": "j1", "claimId": "c1", "state": state, "result": None}
            if state == "completed":
                data["result"] = {"confidenceScore": 0.9}
            return httpx.Response(200, json={"success": True, "data": data})
        if method == "POST" and path == "/api/claims/c1/evidence":
            return httpx.Response(201, json={"success": True, "data": {"id": "e1"}})
        return httpx.Response(500, json={"error": "unexpected " + path})

    return handler


def sync_client(states, seen, **kw):
    return TruthAI(
        transport=httpx.MockTransport(make_handler(states, seen)),
        poll_interval=0,
        **kw,
    )


def test_create_unwraps_data_and_sends_body():
    seen = []
    with sync_client(["completed"], seen) as c:
        claim = c.claims.create("t", "d", "body", modelProvider="openai")
    assert claim == {"id": "c1"}
    assert json.loads(seen[0].content) == {
        "title": "t", "description": "d", "content": "body", "modelProvider": "openai",
    }


def test_api_key_sent_as_bearer_only_when_set():
    seen = []
    with sync_client(["completed"], seen, api_key="k") as c:
        c.claims.create("t", "d", "b")
    assert seen[0].headers["authorization"] == "Bearer k"
    seen2 = []
    with sync_client(["completed"], seen2) as c:
        c.claims.create("t", "d", "b")
    assert "authorization" not in seen2[0].headers


def test_http_error_raises_api_error():
    with sync_client(["completed"], []) as c:
        with pytest.raises(APIError) as e:
            c.claims.get("missing")
    assert e.value.status_code == 404 and e.value.message == "Claim not found"


def test_analyze_polls_until_completed():
    seen = []
    with sync_client(["waiting", "active", "completed"], seen) as c:
        job = c.claims.analyze("c1")
    assert job["result"] == {"confidenceScore": 0.9}
    assert json.loads(seen[0].content) == {"mode": "async"}
    assert sum(r.url.path == "/api/analyses/jobs/j1" for r in seen) == 3


def test_analyze_wait_false_returns_job_without_polling():
    seen = []
    with sync_client(["completed"], seen) as c:
        job = c.claims.analyze("c1", wait=False)
    assert job["jobId"] == "j1" and len(seen) == 1


def test_analyze_failed_raises():
    with sync_client(["active", "failed"], []) as c:
        with pytest.raises(AnalysisFailedError):
            c.claims.analyze("c1")


def test_analyze_timeout_raises():
    with sync_client(["active"], [], poll_timeout=0) as c:
        with pytest.raises(AnalysisTimeoutError):
            c.claims.analyze("c1")


def test_evidence_add():
    seen = []
    with sync_client(["completed"], seen) as c:
        assert c.claims.evidence.add("c1", "t", "body", "document") == {"id": "e1"}
    assert json.loads(seen[0].content) == {"title": "t", "content": "body", "type": "document"}


def test_async_analyze_and_error():
    async def run():
        transport = httpx.MockTransport(make_handler(["active", "completed"], []))
        async with AsyncTruthAI(transport=transport, poll_interval=0) as c:
            job = await c.claims.analyze("c1")
            with pytest.raises(APIError):
                await c.claims.get("missing")
            return job

    assert asyncio.run(run())["state"] == "completed"
