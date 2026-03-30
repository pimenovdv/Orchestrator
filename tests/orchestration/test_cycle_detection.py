import pytest
from app.orchestration.cycle_detection import detect_cycles, DeadlockDetectedError
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


def test_no_cycles() -> None:
    dag = {
        "A": create_mock_agent("A", []),
        "B": create_mock_agent("B", ["A"]),
        "C": create_mock_agent("C", ["A", "B"]),
    }
    # Should not raise any exception
    detect_cycles(dag)


def test_simple_cycle() -> None:
    dag = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["A"]),
    }
    with pytest.raises(
        DeadlockDetectedError, match="Deadlock Detected: Cycle in dependencies: "
    ):
        detect_cycles(dag)


def test_complex_cycle() -> None:
    dag = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["C"]),
        "C": create_mock_agent("C", ["A"]),
        "D": create_mock_agent("D", ["A"]),
    }
    with pytest.raises(
        DeadlockDetectedError, match="Deadlock Detected: Cycle in dependencies: "
    ):
        detect_cycles(dag)


def test_self_cycle() -> None:
    dag = {
        "A": create_mock_agent("A", ["A"]),
    }
    with pytest.raises(
        DeadlockDetectedError, match="Deadlock Detected: Cycle in dependencies: "
    ):
        detect_cycles(dag)


def test_disconnected_components_with_cycle() -> None:
    dag = {
        "A": create_mock_agent("A", []),
        "B": create_mock_agent("B", ["A"]),
        "X": create_mock_agent("X", ["Y"]),
        "Y": create_mock_agent("Y", ["X"]),
    }
    with pytest.raises(
        DeadlockDetectedError, match="Deadlock Detected: Cycle in dependencies: "
    ):
        detect_cycles(dag)
