import pytest
from datetime import timedelta
from typing import Any, Dict, List, TypedDict

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity

from langgraph.graph import StateGraph, START, END

from app.temporal.workflows import OrchestratorWorkflow


# Define a simple State for LangGraph
class AgentState(TypedDict):
    input_context: Dict[str, Any]
    output: str
    agent_id: str


# Create a mock agent node for LangGraph
def process_agent(state: AgentState) -> Dict[str, Any]:
    agent_id = state.get("agent_id", "unknown")
    input_context = state.get("input_context", {})

    # Simulate processing based on previous agent's output
    messages = []
    for key, val in input_context.items():
        if isinstance(val, dict) and "output" in val:
            messages.append(val["output"])

    prev_msg = " | ".join(messages) if messages else "no prev"

    return {"output": f"Processed by {agent_id} (prev: {prev_msg})"}


@activity.defn(name="DiscoverRootAgentActivity")
async def mock_discover_root_agent_activity(query: str) -> str:
    return "agent-a"


@activity.defn(name="BuildExecutionPlanActivity")
async def mock_build_execution_plan_activity(target_agent_id: str) -> List[List[str]]:
    # A graph: C -> B -> A
    # Waves: [["agent-c"], ["agent-b"], ["agent-a"]]
    return [["agent-c"], ["agent-b"], ["agent-a"]]


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
    execution_id = request_dict.get("execution_id", "")

    agent_id_str = "unknown"
    for aid in ["agent-a", "agent-b", "agent-c"]:
        if aid in execution_id:
            agent_id_str = aid
            break

    input_context = request_dict.get("input_context", {})

    # Build and run a minimal LangGraph to mock the embedded player
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", process_agent)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)

    app = workflow.compile()

    initial_state: AgentState = {
        "input_context": input_context,
        "output": "",
        "agent_id": agent_id_str,
    }

    final_state: Any = await app.ainvoke(initial_state)  # type: ignore

    return {
        "status": "success",
        "agent_id": agent_id_str,
        "output": final_state["output"],
    }


@pytest.mark.asyncio
async def test_e2e_orchestrator_with_langgraph() -> None:
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
                "Process data via DAG",
                id="test-e2e-workflow",
                task_queue="orchestrator-task-queue",
                execution_timeout=timedelta(seconds=20),
            )

            assert "final_output" in result
            assert "state_store" in result

            state_store = result["state_store"]
            assert "agent-a" in state_store
            assert "agent-b" in state_store
            assert "agent-c" in state_store

            output_c = state_store["agent-c"]["output"]
            output_b = state_store["agent-b"]["output"]
            output_a = state_store["agent-a"]["output"]

            assert "Processed by agent-c" in output_c
            assert "Processed by agent-b" in output_b
            assert "Processed by agent-a" in output_a

            # Since input context accumulates, agent-b should see agent-c's output
            # and agent-a should see both agent-b's and agent-c's output.
            assert "Processed by agent-c" in output_b
            assert "Processed by agent-c" in output_a
            assert "Processed by agent-b" in output_a

            assert result["final_output"]["agent_id"] == "agent-a"
