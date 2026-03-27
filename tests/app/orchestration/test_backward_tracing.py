import pytest
from typing import Dict, Any, List

from app.clients.agent_discovery import AgentDiscoveryClient
from app.models.agent import AgentIndexDocument
from app.models.manifest import AgentManifest, Prompts, ExecutionLimits
from app.models.graph import MicroGraph
from app.orchestration.backward_tracing import build_dependency_graph


def create_mock_agent(agent_id: str, dependencies: List[str]) -> AgentIndexDocument:
    manifest = AgentManifest(
        input_schema={},
        output_schema={},
        prompts=Prompts(system_instructions="You are a mock agent."),
        tools=[],
        graph=MicroGraph(nodes=[], edges=[]),
        execution_limits=ExecutionLimits()
    )
    return AgentIndexDocument(
        agent_id=agent_id,
        name=f"Mock Agent {agent_id}",
        description=f"Description for {agent_id}",
        capabilities_embedding=[0.0] * 1536,
        dependencies=dependencies,
        manifest=manifest
    )


class MockAgentDiscoveryClient:
    def __init__(self, agents_map: Dict[str, AgentIndexDocument]):
        self.agents_map = agents_map

    async def get_agent_by_id(self, agent_id: str) -> Any:
        return self.agents_map.get(agent_id)


@pytest.mark.asyncio
async def test_single_agent() -> None:
    """Тестирование трассировки для агента без зависимостей."""
    agent_a = create_mock_agent("A", [])
    mock_client = MockAgentDiscoveryClient({"A": agent_a})
    # Type ignore because we are passing a mock client, not real AgentDiscoveryClient
    client: Any = mock_client

    dag = await build_dependency_graph("A", client)
    assert len(dag) == 1
    assert "A" in dag
    assert dag["A"].dependencies == []


@pytest.mark.asyncio
async def test_linear_dependency() -> None:
    """Тестирование линейной зависимости A -> B -> C."""
    agent_a = create_mock_agent("A", ["B"])
    agent_b = create_mock_agent("B", ["C"])
    agent_c = create_mock_agent("C", [])

    mock_client = MockAgentDiscoveryClient({
        "A": agent_a,
        "B": agent_b,
        "C": agent_c,
    })
    client: Any = mock_client

    dag = await build_dependency_graph("A", client)
    assert len(dag) == 3
    assert set(dag.keys()) == {"A", "B", "C"}
    assert dag["A"].dependencies == ["B"]
    assert dag["B"].dependencies == ["C"]
    assert dag["C"].dependencies == []


@pytest.mark.asyncio
async def test_branching_dependency() -> None:
    """Тестирование ветвящейся зависимости: A зависит от B и C; B зависит от D; C зависит от D (алмазная зависимость)."""
    agent_a = create_mock_agent("A", ["B", "C"])
    agent_b = create_mock_agent("B", ["D"])
    agent_c = create_mock_agent("C", ["D"])
    agent_d = create_mock_agent("D", [])

    mock_client = MockAgentDiscoveryClient({
        "A": agent_a,
        "B": agent_b,
        "C": agent_c,
        "D": agent_d,
    })
    client: Any = mock_client

    dag = await build_dependency_graph("A", client)
    assert len(dag) == 4
    assert set(dag.keys()) == {"A", "B", "C", "D"}
    assert dag["D"].dependencies == []


@pytest.mark.asyncio
async def test_missing_dependency() -> None:
    """Тестирование ситуации, когда зависимость отсутствует в реестре."""
    agent_a = create_mock_agent("A", ["B"])
    # Agent B is missing in the mock client
    mock_client = MockAgentDiscoveryClient({"A": agent_a})
    client: Any = mock_client

    with pytest.raises(ValueError) as exc:
        await build_dependency_graph("A", client)
    assert "Agent with ID 'B' not found" in str(exc.value)
