from app.models.api import ExecuteRequest
from app.models.manifest import AgentManifest, Prompts, ExecutionLimits
from app.models.graph import MicroGraph


def test_mapping_input_context() -> None:
    """
    Test mapping outputs of previous agents (Agent A) to the input_context of a subsequent agent (Agent B).
    In the system, this logic is handled by setting input_context = state_store.copy()
    and injecting the '_query' field, as seen in workflows.py.
    """

    # Simulate a scenario where Agent A has completed its execution
    query = "analyze this data"
    state_store = {
        "agent_a": {
            "status": "success",
            "output_data": {"extracted_metrics": [1, 2, 3]},
            "telemetry": {},
        }
    }

    # Create the input_context for Agent B mapping Agent A's output
    input_context = state_store.copy()
    input_context["_query"] = query  # type: ignore

    # Define Agent B's manifest expecting Agent A's output in input_context
    agent_b_manifest = AgentManifest(
        input_schema={
            "type": "object",
            "properties": {
                "agent_a": {
                    "type": "object",
                    "properties": {
                        "output_data": {
                            "type": "object",
                            "properties": {"extracted_metrics": {"type": "array"}},
                        }
                    },
                },
                "_query": {"type": "string"},
            },
        },
        output_schema={"type": "object"},
        prompts=Prompts(system_instructions="You are Agent B"),
        tools=[],
        graph=MicroGraph(nodes=[], edges=[]),
        execution_limits=ExecutionLimits(),
    )

    # Create the ExecutionRequest which relies on this mapping
    req = ExecuteRequest(
        execution_id="exec-wave1-agent_b",
        agent_manifest=agent_b_manifest,
        input_context=input_context,
        execution_limits=agent_b_manifest.execution_limits,
    )

    # Verify the mapping successfully populated the context
    assert req.input_context["_query"] == "analyze this data"
    assert "agent_a" in req.input_context
    assert req.input_context["agent_a"]["output_data"]["extracted_metrics"] == [1, 2, 3]
