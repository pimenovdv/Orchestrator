import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
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


@pytest.mark.asyncio
async def test_get_orchestrator_job_status_success() -> None:
    with patch(
        "app.api.endpoints.Client.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_client = AsyncMock()
        mock_connect.return_value = mock_client

        # get_workflow_handle needs to return something that is NOT a coroutine
        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        class MockStatus:
            name = "RUNNING"

        class MockDescription:
            status = MockStatus()

        # mock_handle.describe is what we await
        mock_handle.describe = AsyncMock(return_value=MockDescription())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                "/api/v1/orchestrator/jobs/orchestration-123/status",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "orchestration-123"
        assert data["status"] == "RUNNING"

        mock_connect.assert_called_once()
        mock_client.get_workflow_handle.assert_called_once_with("orchestration-123")
        mock_handle.describe.assert_called_once()


@pytest.mark.asyncio
async def test_get_orchestrator_job_status_not_found() -> None:
    from temporalio.service import RPCError
    import grpc

    with patch(
        "app.api.endpoints.Client.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_client = AsyncMock()
        mock_connect.return_value = mock_client

        mock_handle = AsyncMock()
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        # Make describe raise an RPCError simulating NOT_FOUND
        error_message = "Workflow execution not found"
        rpc_error = RPCError(error_message, status=grpc.StatusCode.NOT_FOUND, raw_grpc_status=b"")

        mock_handle.describe = AsyncMock(side_effect=rpc_error)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                "/api/v1/orchestrator/jobs/orchestration-123/status",
            )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
