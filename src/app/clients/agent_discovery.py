import os
import httpx
from typing import List, Optional
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import NotFoundError
from app.models.registry import RegistrySearchResponse
from app.models.agent import AgentIndexDocument


class AgentDiscoveryClient:
    def __init__(self, opensearch_client: AsyncOpenSearch, index_name: str = "agents"):
        self.opensearch = opensearch_client
        self.index_name = index_name
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    async def get_embedding(self, text: str) -> List[float]:
        """
        Векторизует входящий запрос через OpenAI API.
        Если ключ не задан, возвращает заглушку для локального тестирования.
        """
        if not self.openai_api_key:
            # Fallback for local testing if no API key is provided
            return [0.0] * 1536

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "model": "text-embedding-ada-002",
                },
            )
            response.raise_for_status()
            data = response.json()
            return list(data["data"][0]["embedding"])

    async def search_candidates(
        self, query: str, top_k: int = 5
    ) -> RegistrySearchResponse:
        """
        Ищет релевантных кандидатов (агентов) на основе запроса и вектора.
        """
        vector = await self.get_embedding(query)

        search_query = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "knn_score",
                        "lang": "knn",
                        "params": {
                            "field": "capabilities_embedding",
                            "query_value": vector,
                            "space_type": "cosinesimil",
                        },
                    },
                }
            },
        }

        response = await self.opensearch.search(
            index=self.index_name, body=search_query
        )
        return RegistrySearchResponse.model_validate(response)

    async def get_agent_by_id(self, agent_id: str) -> Optional[AgentIndexDocument]:
        """
        Получает агента по его agent_id из OpenSearch.
        """
        search_query = {
            "query": {
                "term": {
                    "agent_id": agent_id
                }
            }
        }
        try:
            response = await self.opensearch.search(
                index=self.index_name, body=search_query, size=1
            )
            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                return None
            return AgentIndexDocument.model_validate(hits[0]["_source"])
        except NotFoundError:
            return None
