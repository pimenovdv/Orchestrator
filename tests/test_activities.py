import pytest
import respx
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from temporalio.testing import ActivityEnvironment

from app.temporal.activities import (
    discover_root_agent_activity,
    build_execution_plan_activity,
    execute_agent_activity,
)


@pytest.mark.asyncio
async def test_discover_root_agent_activity() -> None:
    activity_env = ActivityEnvironment()

    mock_response = MagicMock()
    mock_response.hits.hits = [
        MagicMock(source=MagicMock(agent_id="finance_auditor_v1"))
    ]

    # Чтобы await client.close() работал, нам нужно чтобы AsyncOpenSearch возвращал объект с асинхронным close()
    mock_opensearch_client = MagicMock()
    mock_opensearch_client.close = AsyncMock()

    with (
        patch(
            "app.temporal.activities.AsyncOpenSearch",
            return_value=mock_opensearch_client,
        ),
        patch("app.temporal.activities.AgentDiscoveryClient") as mock_client_class,
    ):

        mock_instance = mock_client_class.return_value
        mock_instance.search_candidates = AsyncMock(return_value=mock_response)

        result = await activity_env.run(discover_root_agent_activity, "finance audit")
        assert result == "finance_auditor_v1"
        mock_instance.search_candidates.assert_called_once_with(
            "finance audit", top_k=1
        )
        mock_opensearch_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_discover_root_agent_activity_not_found() -> None:
    activity_env = ActivityEnvironment()

    mock_response = MagicMock()
    mock_response.hits.hits = []

    mock_opensearch_client = MagicMock()
    mock_opensearch_client.close = AsyncMock()

    with (
        patch(
            "app.temporal.activities.AsyncOpenSearch",
            return_value=mock_opensearch_client,
        ),
        patch("app.temporal.activities.AgentDiscoveryClient") as mock_client_class,
    ):

        mock_instance = mock_client_class.return_value
        mock_instance.search_candidates = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError, match="No agents found for query"):
            await activity_env.run(discover_root_agent_activity, "unknown")

        mock_opensearch_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_build_execution_plan_activity() -> None:
    activity_env = ActivityEnvironment()

    mock_dag = {
        "agent_a": MagicMock(dependencies=[]),
        "agent_b": MagicMock(dependencies=["agent_a"]),
        "agent_c": MagicMock(dependencies=["agent_a"]),
        "agent_d": MagicMock(dependencies=["agent_b", "agent_c"]),
    }

    expected_waves = [["agent_a"], ["agent_b", "agent_c"], ["agent_d"]]

    mock_opensearch_client = MagicMock()
    mock_opensearch_client.close = AsyncMock()

    with (
        patch(
            "app.temporal.activities.AsyncOpenSearch",
            return_value=mock_opensearch_client,
        ),
        patch("app.temporal.activities.AgentDiscoveryClient"),
        patch(
            "app.temporal.activities.build_dependency_graph", new_callable=AsyncMock
        ) as mock_build_dag,
        patch("app.temporal.activities.topological_sort") as mock_sort,
    ):

        mock_build_dag.return_value = mock_dag
        mock_sort.return_value = expected_waves

        result = await activity_env.run(build_execution_plan_activity, "agent_d")

        assert result == expected_waves
        mock_build_dag.assert_called_once()
        mock_sort.assert_called_once_with(mock_dag)
        mock_opensearch_client.close.assert_called_once()


@pytest.mark.asyncio
@respx.mock
async def test_execute_agent_activity_success() -> None:
    activity_env = ActivityEnvironment()

    request_dict = {
        "execution_id": "exec-123",
        "agent_manifest": {
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "prompts": {"system_instructions": "You are a helpful assistant"},
            "tools": [],
            "graph": {
                "nodes": [{"id": "node1", "type": "reasoning", "name": "Start"}],
                "edges": [],
                "starting_node": "node1",
            },
            "execution_limits": {"max_tokens": 1000, "timeout_ms": 30000},
        },
        "input_context": {"query": "test"},
        "execution_limits": {"max_tokens": 1000, "timeout_ms": 30000},
    }

    response_dict = {
        "status": "success",
        "output_data": {"result": "ok"},
        "telemetry": {"tokens": 42},
    }

    respx.post("http://localhost:8001/api/v1/player/execute").mock(
        return_value=httpx.Response(200, json=response_dict)
    )

    result = await activity_env.run(execute_agent_activity, request_dict)

    assert result["status"] == "success"
    assert result["output_data"] == {"result": "ok"}
    assert result["telemetry"] == {"tokens": 42}


@pytest.mark.asyncio
@respx.mock
async def test_execute_agent_activity_error() -> None:
    activity_env = ActivityEnvironment()

    request_dict = {
        "execution_id": "exec-123",
        "agent_manifest": {
            "input_schema": {},
            "output_schema": {},
            "prompts": {"system_instructions": "test"},
            "tools": [],
            "graph": {
                "nodes": [{"id": "node1", "type": "reasoning", "name": "Start"}],
                "edges": [],
                "starting_node": "node1",
            },
            "execution_limits": {},
        },
        "input_context": {},
        "execution_limits": {},
    }

    # Имитируем ошибку соединения
    respx.post("http://localhost:8001/api/v1/player/execute").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    result = await activity_env.run(execute_agent_activity, request_dict)

    assert result["status"] == "error"
    assert "error" in result["output_data"]
    assert "Failed to connect" in result["output_data"]["error"]
