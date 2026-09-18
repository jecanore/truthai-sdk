"""Exceptions raised by the TruthAI SDK."""


class TruthAIError(Exception):
    """Base class for all SDK errors."""


class APIError(TruthAIError):
    """The API answered with an HTTP error status."""

    def __init__(self, status_code, message):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class AnalysisFailedError(TruthAIError):
    """The analysis job finished in the `failed` state."""

    def __init__(self, job):
        super().__init__(f"Analysis job {job.get('jobId')} failed")
        self.job = job


class AnalysisTimeoutError(TruthAIError):
    """The analysis job did not finish before the poll timeout."""

    def __init__(self, job_id, timeout):
        super().__init__(f"Analysis job {job_id} not finished after {timeout}s")
        self.job_id = job_id
        self.timeout = timeout
