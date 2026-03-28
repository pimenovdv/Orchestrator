import pytest
from typing import Optional, List

from app.models.agent import AgentIndexDocument
from app.models.manifest import AgentManifest, Prompts
from app.models.graph import MicroGraph


def create_mock_agent(agent_id: str, dependencies: Optional[List[str]] = None) -> AgentIndexDocument:
    return AgentIndexDocument(
        agent_id=agent_id,
        name=f"Test Agent {agent_id}",
        description="A test agent",
        capabilities_embedding=[0.0] * 1536,
        dependencies=dependencies or [],
        manifest=AgentManifest(
            input_schema={},
            output_schema={},
            prompts=Prompts(
                system_instructions="Test",
            ),
            graph=MicroGraph(
                nodes=[],
                edges=[],
            ),
        ),
    )


def test_topological_sort_empty() -> None:
    from app.orchestration.topological_sort import topological_sort
    assert topological_sort({}) == []


def test_topological_sort_independent_agents() -> None:
    from app.orchestration.topological_sort import topological_sort
    # Агенты без зависимостей могут выполняться параллельно (в одной волне)
    dag = {
        "agent_a": create_mock_agent("agent_a"),
        "agent_b": create_mock_agent("agent_b"),
        "agent_c": create_mock_agent("agent_c"),
    }

    waves = topological_sort(dag)
    assert len(waves) == 1
    assert sorted(waves[0]) == ["agent_a", "agent_b", "agent_c"]


def test_topological_sort_linear() -> None:
    from app.orchestration.topological_sort import topological_sort
    # agent_c -> agent_b -> agent_a
    dag = {
        "agent_a": create_mock_agent("agent_a"),
        "agent_b": create_mock_agent("agent_b", dependencies=["agent_a"]),
        "agent_c": create_mock_agent("agent_c", dependencies=["agent_b"]),
    }

    waves = topological_sort(dag)
    assert waves == [["agent_a"], ["agent_b"], ["agent_c"]]


def test_topological_sort_diamond() -> None:
    from app.orchestration.topological_sort import topological_sort
    # agent_d -> agent_b, agent_c
    # agent_b -> agent_a
    # agent_c -> agent_a
    dag = {
        "agent_a": create_mock_agent("agent_a"),
        "agent_b": create_mock_agent("agent_b", dependencies=["agent_a"]),
        "agent_c": create_mock_agent("agent_c", dependencies=["agent_a"]),
        "agent_d": create_mock_agent("agent_d", dependencies=["agent_b", "agent_c"]),
    }

    waves = topological_sort(dag)
    assert len(waves) == 3
    assert waves[0] == ["agent_a"]
    assert sorted(waves[1]) == ["agent_b", "agent_c"]
    assert waves[2] == ["agent_d"]


def test_topological_sort_complex() -> None:
    from app.orchestration.topological_sort import topological_sort
    # agent_a -> None
    # agent_b -> None
    # agent_c -> agent_a
    # agent_d -> agent_b
    # agent_e -> agent_c, agent_d
    dag = {
        "agent_a": create_mock_agent("agent_a"),
        "agent_b": create_mock_agent("agent_b"),
        "agent_c": create_mock_agent("agent_c", dependencies=["agent_a"]),
        "agent_d": create_mock_agent("agent_d", dependencies=["agent_b"]),
        "agent_e": create_mock_agent("agent_e", dependencies=["agent_c", "agent_d"]),
    }

    waves = topological_sort(dag)
    assert len(waves) == 3
    assert sorted(waves[0]) == ["agent_a", "agent_b"]
    assert sorted(waves[1]) == ["agent_c", "agent_d"]
    assert waves[2] == ["agent_e"]


def test_topological_sort_missing_dependency() -> None:
    from app.orchestration.topological_sort import topological_sort
    dag = {
        "agent_a": create_mock_agent("agent_a", dependencies=["agent_b"]),
    }

    with pytest.raises(ValueError, match="is not present in the DAG"):
        topological_sort(dag)


def test_topological_sort_cycle() -> None:
    from app.orchestration.topological_sort import topological_sort
    # Внутренняя проверка на цикл должна срабатывать, если не поймали раньше
    dag = {
        "agent_a": create_mock_agent("agent_a", dependencies=["agent_b"]),
        "agent_b": create_mock_agent("agent_b", dependencies=["agent_a"]),
    }

    with pytest.raises(ValueError, match="cyclic dependency detected"):
        topological_sort(dag)
