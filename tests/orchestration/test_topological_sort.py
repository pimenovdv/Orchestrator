import pytest
from app.orchestration.topological_sort import topological_sort
from app.models.agent import AgentIndexDocument
from app.models.manifest import AgentManifest, Prompts, ExecutionLimits
from app.models.graph import MicroGraph


def create_mock_agent(agent_id: str, dependencies: list[str]) -> AgentIndexDocument:
    return AgentIndexDocument(
        agent_id=agent_id,
        name=agent_id,
        description="mock",
        capabilities_embedding=[],
        dependencies=dependencies,
        manifest=AgentManifest(
            input_schema={},
            output_schema={},
            prompts=Prompts(system_instructions="sys desc"),
            tools=[],
            graph=MicroGraph(nodes=[], edges=[]),
            execution_limits=ExecutionLimits(),
        ),
    )


def test_linear_graph() -> None:
    dag = {
        "A": create_mock_agent("A", []),
        "B": create_mock_agent("B", ["A"]),
        "C": create_mock_agent("C", ["B"]),
    }
    waves = topological_sort(dag)
    assert waves == [["A"], ["B"], ["C"]]


def test_branched_graph() -> None:
    dag = {
        "A": create_mock_agent("A", []),
        "B": create_mock_agent("B", ["A"]),
        "C": create_mock_agent("C", ["A"]),
        "D": create_mock_agent("D", ["B", "C"]),
    }
    waves = topological_sort(dag)
    assert waves == [["A"], ["B", "C"], ["D"]]


def test_multiple_roots() -> None:
    dag = {
        "A1": create_mock_agent("A1", []),
        "A2": create_mock_agent("A2", []),
        "B": create_mock_agent("B", ["A1", "A2"]),
    }
    waves = topological_sort(dag)
    assert waves == [["A1", "A2"], ["B"]]


def test_invalid_dependency() -> None:
    dag = {
        "A": create_mock_agent("A", ["UNKNOWN"]),
    }
    with pytest.raises(
        ValueError,
        match="Agent 'A' depends on 'UNKNOWN' which is not present in the DAG.",
    ):
        topological_sort(dag)


def test_cycle_detection_fallback() -> None:
    dag = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["A"]),
    }
    with pytest.raises(
        ValueError, match="Cannot perform topological sort: cyclic dependency detected."
    ):
        topological_sort(dag)
