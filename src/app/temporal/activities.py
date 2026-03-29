import os
import httpx
from typing import Dict, List, Any
from temporalio import activity
from opensearchpy import AsyncOpenSearch

from app.clients.agent_discovery import AgentDiscoveryClient
from app.models.agent import AgentIndexDocument
from app.models.api import ExecuteRequest, ExecuteResponse, ExecutionStatus
from app.models.registry import RegistrySearchResponse
from app.orchestration.backward_tracing import build_dependency_graph
from app.orchestration.topological_sort import topological_sort


@activity.defn(name="DiscoverRootAgentActivity")
async def discover_root_agent_activity(query: str) -> str:
    """
    Вызов семантического поиска.
    Ищет релевантных кандидатов на основе текстового запроса и возвращает agent_id лучшего.
    """
    opensearch_url = os.getenv("OPENSEARCH_URL", "https://localhost:9200")
    client = AsyncOpenSearch(
        hosts=[opensearch_url],
        http_auth=("admin", "admin"),  # default creds
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

    try:
        discovery_client = AgentDiscoveryClient(client)
        response: RegistrySearchResponse = await discovery_client.search_candidates(
            query, top_k=1
        )

        if not response.hits.hits:
            raise RuntimeError(f"No agents found for query: {query}")

        return response.hits.hits[0].source.agent_id
    finally:
        await client.close()


@activity.defn(name="BuildExecutionPlanActivity")
async def build_execution_plan_activity(target_agent_id: str) -> List[List[str]]:
    """
    Вызов алгоритма обратной трассировки и топологической сортировки.
    Строит DAG зависимостей и возвращает волны выполнения.
    """
    opensearch_url = os.getenv("OPENSEARCH_URL", "https://localhost:9200")
    client = AsyncOpenSearch(
        hosts=[opensearch_url],
        http_auth=("admin", "admin"),
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

    try:
        discovery_client = AgentDiscoveryClient(client)

        # Строим DAG
        dag: Dict[str, AgentIndexDocument] = await build_dependency_graph(
            target_agent_id, discovery_client
        )

        # Сортируем топологически
        waves: List[List[str]] = topological_sort(dag)

        return waves
    finally:
        await client.close()


@activity.defn(name="ExecuteAgentActivity")
async def execute_agent_activity(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Вызов микро-исполнения.
    Вариант А (External Player): Отправка HTTP-запроса POST /api/v1/player/execute
    во внешний микросервис.
    """
    request = ExecuteRequest.model_validate(request_dict)

    player_url = os.getenv("PLAYER_SERVICE_URL", "http://localhost:8001")
    endpoint = f"{player_url}/api/v1/player/execute"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                endpoint,
                json=request.model_dump(mode="json"),
                timeout=request.execution_limits.timeout_ms / 1000.0,
            )
            response.raise_for_status()

            result = ExecuteResponse.model_validate(response.json())
            return result.model_dump(mode="json")

        except httpx.HTTPStatusError as e:
            error_response = ExecuteResponse(
                status=ExecutionStatus.ERROR,
                output_data={"error": str(e), "details": e.response.text},
                telemetry={},
            )
            return error_response.model_dump(mode="json")
        except httpx.RequestError as e:
            error_response = ExecuteResponse(
                status=ExecutionStatus.ERROR,
                output_data={
                    "error": "Failed to connect to player service",
                    "details": str(e),
                },
                telemetry={},
            )
            return error_response.model_dump(mode="json")
