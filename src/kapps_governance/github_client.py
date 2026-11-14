"""Configure the supported GitHubKit client without wrapping its API."""

import os
from typing import Final

from githubkit import GitHub

API_VERSION: Final = "2026-03-10"


def make_client() -> GitHub:
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("GH_TOKEN is required")
    # Reconciliation must read current state and must not retry ambiguous writes.
    return GitHub(token, http_cache=False, auto_retry=False, timeout=30)
