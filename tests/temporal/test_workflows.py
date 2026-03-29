import pytest
from datetime import timedelta
from typing import Any, Dict, List

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity

from app.temporal.workflows import OrchestratorWorkflow


@activity.defn(name="DiscoverRootAgentActivity")
async def mock_discover_root_agent_activity(query: str) -> str:
    return "root-agent-1"


@activity.defn(name="BuildExecutionPlanActivity")
async def mock_build_execution_plan_activity(target_agent_id: str) -> List[List[str]]:
    return [["agent-3", "agent-2"], ["root-agent-1"]]


@activity.defn(name="GetAgentManifestActivity")
async def mock_get_agent_manifest_activity(agent_id: str) -> Dict[str, Any]:
    return {
        "input_schema": {"type": "object", "properties": {}},
        "output_schema": {"type": "object", "properties": {}},
        "prompts": {"system_instructions": f"Instruction for {agent_id}"},
        "tools": [],
        "graph": {"nodes": [], "edges": []},
        "execution_limits": {"max_tokens": 1000, "timeout_ms": 10000},
    }


@activity.defn(name="ExecuteAgentActivity")
async def mock_execute_agent_activity(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Need to extract agent_id from the execution_id
    execution_id = request_dict.get("execution_id", "")
    if "root-agent-1" in execution_id:
        agent_id_str = "root-agent-1"
    elif "agent-2" in execution_id:
        agent_id_str = "agent-2"
    elif "agent-3" in execution_id:
        agent_id_str = "agent-3"
    else:
        agent_id_str = "unknown"

    return {
        "status": "success",
        "agent_id": agent_id_str,
        "output": f"Output from {agent_id_str}",
    }


@pytest.mark.asyncio
async def test_orchestrator_workflow() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="orchestrator-task-queue",
            workflows=[OrchestratorWorkflow],
            activities=[
                mock_discover_root_agent_activity,
                mock_build_execution_plan_activity,
                mock_execute_agent_activity,
                mock_get_agent_manifest_activity,
            ],
        ):
            result = await env.client.execute_workflow(
                OrchestratorWorkflow.run,
                "some query text",
                id="test-orchestrator-workflow-1",
                task_queue="orchestrator-task-queue",
                execution_timeout=timedelta(seconds=10),
            )

            assert "final_output" in result
            assert "state_store" in result

            state_store = result["state_store"]
            assert "agent-3" in state_store
            assert "agent-2" in state_store
            assert "root-agent-1" in state_store

            assert state_store["agent-3"]["output"] == "Output from agent-3"
            assert state_store["agent-2"]["output"] == "Output from agent-2"
            assert state_store["root-agent-1"]["output"] == "Output from root-agent-1"
