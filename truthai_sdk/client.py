"""Sync and async clients for the TruthAI REST API."""

import asyncio
import time

import httpx

from .errors import (
    AnalysisFailedError,
    AnalysisTimeoutError,
    APIError,
)

DEFAULT_BASE_URL = "http://127.0.0.1:3000"


def _headers(api_key):
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _unwrap(response):
    """Return the `data` field of an API response, or raise APIError."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if response.status_code >= 400:
        message = body.get("error") if isinstance(body, dict) else None
        raise APIError(response.status_code, message or response.text)
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _analyze_body(options):
    body = {"mode": "async"}
    if options:
        body["options"] = options
    return body


class _Config:
    def __init__(self, poll_interval, poll_timeout):
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout


def _check_job(job):
    """Return True when the job is done, raise if it failed."""
    state = job.get("state")
    if state == "failed":
        raise AnalysisFailedError(job)
    return state == "completed"


class _Claims:
    def __init__(self, client):
        self._c = client
        self.evidence = _Evidence(client)

    def create(self, title, description, content, **fields):
        return self._c._request(
            "POST",
            "/api/claims",
            json={"title": title, "description": description, "content": content, **fields},
        )

    def get(self, claim_id):
        return self._c._request("GET", f"/api/claims/{claim_id}")

    def analyses(self, claim_id):
        return self._c._request("GET", f"/api/claims/{claim_id}/analyses")

    def analyze(self, claim_id, options=None, wait=True):
        job = self._c._request(
            "POST", f"/api/claims/{claim_id}/analyze", json=_analyze_body(options)
        )
        if not wait:
            return job
        return self._c._poll(job["jobId"])


class _Evidence:
    def __init__(self, client):
        self._c = client

    def add(self, claim_id, title, content, type, **fields):
        return self._c._request(
            "POST",
            f"/api/claims/{claim_id}/evidence",
            json={"title": title, "content": content, "type": type, **fields},
        )

    def list(self, claim_id):
        return self._c._request("GET", f"/api/claims/{claim_id}/evidence")


class _AsyncClaims:
    def __init__(self, client):
        self._c = client
        self.evidence = _AsyncEvidence(client)

    async def create(self, title, description, content, **fields):
        return await self._c._request(
            "POST",
            "/api/claims",
            json={"title": title, "description": description, "content": content, **fields},
        )

    async def get(self, claim_id):
        return await self._c._request("GET", f"/api/claims/{claim_id}")

    async def analyses(self, claim_id):
        return await self._c._request("GET", f"/api/claims/{claim_id}/analyses")

    async def analyze(self, claim_id, options=None, wait=True):
        job = await self._c._request(
            "POST", f"/api/claims/{claim_id}/analyze", json=_analyze_body(options)
        )
        if not wait:
            return job
        return await self._c._poll(job["jobId"])


class _AsyncEvidence:
    def __init__(self, client):
        self._c = client

    async def add(self, claim_id, title, content, type, **fields):
        return await self._c._request(
            "POST",
            f"/api/claims/{claim_id}/evidence",
            json={"title": title, "content": content, "type": type, **fields},
        )

    async def list(self, claim_id):
        return await self._c._request("GET", f"/api/claims/{claim_id}/evidence")


class TruthAI:
    """Synchronous client."""

    def __init__(
        self,
        base_url=DEFAULT_BASE_URL,
        api_key=None,
        timeout=30.0,
        poll_interval=1.0,
        poll_timeout=120.0,
        transport=None,
    ):
        self._http = httpx.Client(
            base_url=base_url,
            headers=_headers(api_key),
            timeout=timeout,
            transport=transport,
        )
        self._cfg = _Config(poll_interval, poll_timeout)
        self.claims = _Claims(self)

    def _request(self, method, path, json=None):
        return _unwrap(self._http.request(method, path, json=json))

    def _poll(self, job_id):
        deadline = time.monotonic() + self._cfg.poll_timeout
        while True:
            job = self._request("GET", f"/api/analyses/jobs/{job_id}")
            if _check_job(job):
                return job
            if time.monotonic() >= deadline:
                raise AnalysisTimeoutError(job_id, self._cfg.poll_timeout)
            time.sleep(self._cfg.poll_interval)

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class AsyncTruthAI:
    """Asynchronous client."""

    def __init__(
        self,
        base_url=DEFAULT_BASE_URL,
        api_key=None,
        timeout=30.0,
        poll_interval=1.0,
        poll_timeout=120.0,
        transport=None,
    ):
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=_headers(api_key),
            timeout=timeout,
            transport=transport,
        )
        self._cfg = _Config(poll_interval, poll_timeout)
        self.claims = _AsyncClaims(self)

    async def _request(self, method, path, json=None):
        return _unwrap(await self._http.request(method, path, json=json))

    async def _poll(self, job_id):
        deadline = time.monotonic() + self._cfg.poll_timeout
        while True:
            job = await self._request("GET", f"/api/analyses/jobs/{job_id}")
            if _check_job(job):
                return job
            if time.monotonic() >= deadline:
                raise AnalysisTimeoutError(job_id, self._cfg.poll_timeout)
            await asyncio.sleep(self._cfg.poll_interval)

    async def aclose(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()
