from typing import Any

import httpx

from app.llm.settings import LLMSettings


class Project1KnowledgeClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        settings = LLMSettings()

        self.base_url = (
            base_url or settings.project1_base_url
        ).rstrip("/")

        self.timeout = timeout

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/search",
            json={
                "query": query,
                "top_k": top_k,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()