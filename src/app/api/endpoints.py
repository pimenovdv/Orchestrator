import uuid
import os
from fastapi import APIRouter, HTTPException, status
from temporalio.client import Client
from temporalio.service import RPCError

from app.models.api import DispatchRequest, DispatchResponse, JobStatusResponse
from app.temporal.workflows import OrchestratorWorkflow

router = APIRouter(prefix="/api/v1/orchestrator", tags=["orchestrator"])


@router.post(
    "/dispatch", response_model=DispatchResponse, status_code=status.HTTP_200_OK
)
async def dispatch_orchestrator(request: DispatchRequest) -> DispatchResponse:
    """
    Прием неструктурированного запроса.
    Парсинг контекста и запуск Temporal Workflow.
    Возврат orchestration_job_id пользователю.
    """
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

    try:
        client = await Client.connect(temporal_address)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Temporal: {e}",
        )

    job_id = f"orchestration-{uuid.uuid4()}"

    try:
        # According to the TODO, we launch Temporal Workflow
        # (client.execute_workflow is mentioned in TODO, but usually we use start_workflow
        # to immediately return job_id to the user, allowing status checks later via the other endpoint)
        await client.start_workflow(
            OrchestratorWorkflow.run,
            request.query,
            id=job_id,
            task_queue="orchestrator-task-queue",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Orchestrator Workflow: {e}",
        )

    return DispatchResponse(orchestration_job_id=job_id)


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_orchestrator_job_status(job_id: str) -> JobStatusResponse:
    """
    Проверка статуса выполнения задачи в Temporal.
    """
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

    try:
        client = await Client.connect(temporal_address)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Temporal: {e}",
        )

    try:
        handle = client.get_workflow_handle(job_id) # This is synchronous
        description = await handle.describe()
    except RPCError as e:
        # Handle case where workflow is not found (usually gRPC NOT_FOUND)
        if "not found" in str(e).lower() or "not exist" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to describe workflow: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}",
        )

    if description.status is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow status is None",
        )

    return JobStatusResponse(
        job_id=job_id,
        status=description.status.name,
    )
