import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.mark.asyncio
async def test_dispatch_orchestrator_success() -> None:
    # Mock Temporal Client
    with patch(
        "app.api.endpoints.Client.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_client = AsyncMock()
        mock_connect.return_value = mock_client
        mock_client.start_workflow = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/orchestrator/dispatch",
                json={"query": "Test user query for agents"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "orchestration_job_id" in data
        assert data["orchestration_job_id"].startswith("orchestration-")

        mock_connect.assert_called_once()
        mock_client.start_workflow.assert_called_once()
        args, kwargs = mock_client.start_workflow.call_args
        assert args[1] == "Test user query for agents"
        assert kwargs["task_queue"] == "orchestrator-task-queue"


@pytest.mark.asyncio
async def test_dispatch_orchestrator_invalid_payload() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/orchestrator/dispatch", json={"wrong_field": "test"}
        )

    assert response.status_code == 422
