"""
TruthAI SDK

Python client for the TruthAI uncertainty-analysis API.
Under development; not released.
"""

from .client import AsyncTruthAI, TruthAI
from .errors import (
    AnalysisFailedError,
    AnalysisTimeoutError,
    APIError,
    TruthAIError,
)

__version__ = "0.0.2"
__author__ = "TruthAI"
__email__ = "contact@truthai.com"

__all__ = [
    "TruthAI",
    "AsyncTruthAI",
    "TruthAIError",
    "APIError",
    "AnalysisFailedError",
    "AnalysisTimeoutError",
]
