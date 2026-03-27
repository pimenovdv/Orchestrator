from typing import Dict, Set

from app.clients.agent_discovery import AgentDiscoveryClient
from app.models.agent import AgentIndexDocument


async def build_dependency_graph(
    target_agent_id: str, client: AgentDiscoveryClient
) -> Dict[str, AgentIndexDocument]:
    """
    Выполняет алгоритм обратной трассировки (Backward Tracing) для поиска
    зависимостей целевого агента до корневых агентов (у которых dependencies == []).

    Args:
        target_agent_id: ID целевого агента, с которого начинается трассировка.
        client: Экземпляр AgentDiscoveryClient для поиска агентов в реестре.

    Returns:
        Словарь (DAG), где ключ — agent_id, значение — AgentIndexDocument.
    """
    dag: Dict[str, AgentIndexDocument] = {}
    visited: Set[str] = set()
    queue = [target_agent_id]

    while queue:
        current_agent_id = queue.pop(0)

        if current_agent_id in visited:
            continue

        visited.add(current_agent_id)

        # Если мы уже загрузили этого агента (например, как зависимость другого),
        # пропускаем повторный запрос. В текущей логике это покрывается `visited`,
        # но для защиты оставим проверку.
        if current_agent_id in dag:
            continue

        agent_doc = await client.get_agent_by_id(current_agent_id)
        if not agent_doc:
            raise ValueError(f"Agent with ID '{current_agent_id}' not found in the registry.")

        dag[current_agent_id] = agent_doc

        for dependency_id in agent_doc.dependencies:
            if dependency_id not in visited and dependency_id not in queue:
                queue.append(dependency_id)

    return dag
