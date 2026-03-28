import pytest
from typing import Dict, List
from app.models.agent import AgentIndexDocument
from app.models.manifest import AgentManifest, Prompts, ExecutionLimits
from app.models.graph import MicroGraph
from app.orchestration.cycle_detection import detect_cycles, DeadlockDetectedError


def create_mock_agent(agent_id: str, dependencies: List[str]) -> AgentIndexDocument:
    manifest = AgentManifest(
        input_schema={},
        output_schema={},
        prompts=Prompts(system_instructions="You are a mock agent."),
        tools=[],
        graph=MicroGraph(nodes=[], edges=[]),
        execution_limits=ExecutionLimits(),
    )
    return AgentIndexDocument(
        agent_id=agent_id,
        name=f"Mock Agent {agent_id}",
        description=f"Description for {agent_id}",
        capabilities_embedding=[0.0] * 1536,
        dependencies=dependencies,
        manifest=manifest,
    )


def test_no_cycle_linear() -> None:
    """Тест линейного графа без циклов (A -> B -> C)."""
    dag: Dict[str, AgentIndexDocument] = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["C"]),
        "C": create_mock_agent("C", []),
    }
    # Ожидаем, что функция отработает без ошибок
    detect_cycles(dag)


def test_no_cycle_branching() -> None:
    """Тест ветвящегося графа без циклов (A -> B, A -> C, B -> D, C -> D)."""
    dag: Dict[str, AgentIndexDocument] = {
        "A": create_mock_agent("A", ["B", "C"]),
        "B": create_mock_agent("B", ["D"]),
        "C": create_mock_agent("C", ["D"]),
        "D": create_mock_agent("D", []),
    }
    # Ожидаем, что функция отработает без ошибок
    detect_cycles(dag)


def test_explicit_cycle() -> None:
    """Тест явного цикла (A -> B -> A)."""
    dag: Dict[str, AgentIndexDocument] = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["A"]),
    }
    with pytest.raises(DeadlockDetectedError) as exc_info:
        detect_cycles(dag)
    assert "Deadlock Detected: Cycle in dependencies: A -> B -> A" in str(
        exc_info.value
    ) or "Deadlock Detected: Cycle in dependencies: B -> A -> B" in str(exc_info.value)


def test_self_cycle() -> None:
    """Тест цикла агента на самого себя (A -> A)."""
    dag: Dict[str, AgentIndexDocument] = {
        "A": create_mock_agent("A", ["A"]),
    }
    with pytest.raises(DeadlockDetectedError) as exc_info:
        detect_cycles(dag)
    assert "Deadlock Detected: Cycle in dependencies: A -> A" in str(exc_info.value)


def test_complex_cycle() -> None:
    """Тест сложного цикла (A -> B -> C -> A)."""
    dag: Dict[str, AgentIndexDocument] = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["C"]),
        "C": create_mock_agent("C", ["A"]),
    }
    with pytest.raises(DeadlockDetectedError) as exc_info:
        detect_cycles(dag)
    assert "Deadlock Detected: Cycle in dependencies" in str(exc_info.value)


def test_cycle_not_in_root() -> None:
    """Тест цикла, который не включает корневую вершину (A -> B -> C -> D -> C)."""
    dag: Dict[str, AgentIndexDocument] = {
        "A": create_mock_agent("A", ["B"]),
        "B": create_mock_agent("B", ["C"]),
        "C": create_mock_agent("C", ["D"]),
        "D": create_mock_agent("D", ["C"]),
    }
    with pytest.raises(DeadlockDetectedError) as exc_info:
        detect_cycles(dag)
    assert "Deadlock Detected: Cycle in dependencies" in str(exc_info.value)
