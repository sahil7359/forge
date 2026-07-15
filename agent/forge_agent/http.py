"""API client with cold-start tolerance (POC S3, TechSpec §6)."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from forge_agent.config import settings

HEADERS = {"Authorization": f"Bearer {settings.agent_token}"}


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, max=60))
def api_get(path: str) -> dict:
    r = httpx.get(settings.api_base + path, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, max=60))
def api_post(path: str, json: dict) -> dict | None:
    r = httpx.post(settings.api_base + path, headers=HEADERS, json=json, timeout=60)
    r.raise_for_status()
    return r.json() if r.content else None
