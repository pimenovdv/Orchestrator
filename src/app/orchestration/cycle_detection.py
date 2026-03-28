from typing import Dict, List
from app.models.agent import AgentIndexDocument


class DeadlockDetectedError(Exception):
    """Исключение, выбрасываемое при обнаружении циклической зависимости (deadlock)."""

    pass


def detect_cycles(dag: Dict[str, AgentIndexDocument]) -> None:
    """
    Проверяет граф зависимостей (DAG) на наличие циклов.
    Использует алгоритм поиска в глубину (DFS) с тремя состояниями (цветами):
    - 0 (белый): не посещен
    - 1 (серый): в процессе посещения (в текущем пути DFS)
    - 2 (черный): полностью обработан (все его зависимости проверены)

    Args:
        dag: Словарь, где ключ - ID агента, значение - AgentIndexDocument.

    Raises:
        DeadlockDetectedError: Если обнаружен цикл (зависимость от серой вершины).
    """
    # Состояния: 0 - не посещен, 1 - посещается, 2 - посещен
    visited: Dict[str, int] = {agent_id: 0 for agent_id in dag}

    def dfs(agent_id: str, path: List[str]) -> None:
        if agent_id not in visited:
            # Зависимость агента может отсутствовать в dag,
            # но мы проверяем только связи внутри переданного графа.
            # Если зависимость не в dag, мы не можем проверить ее зависимости,
            # но это означает, что она не является частью текущего набора,
            # и цикл с ней невозможен (в рамках данного графа).
            return

        state = visited[agent_id]
        if state == 1:
            # Нашли серую вершину - цикл!
            # Формируем цепочку для понятного сообщения об ошибке
            cycle_start_index = path.index(agent_id)
            cycle_path = path[cycle_start_index:] + [agent_id]
            cycle_str = " -> ".join(cycle_path)
            raise DeadlockDetectedError(
                f"Deadlock Detected: Cycle in dependencies: {cycle_str}"
            )

        if state == 2:
            return  # Уже проверили этого агента и все его зависимости

        # Помечаем как серую (в процессе)
        visited[agent_id] = 1
        path.append(agent_id)

        # Рекурсивно проверяем зависимости
        agent_doc = dag.get(agent_id)
        if agent_doc and agent_doc.dependencies:
            for dep_id in agent_doc.dependencies:
                dfs(dep_id, path)

        # Убираем из текущего пути и помечаем как черную (обработано)
        path.pop()
        visited[agent_id] = 2

    # Запускаем DFS для всех вершин графа
    for agent_id in dag:
        if visited[agent_id] == 0:
            dfs(agent_id, [])
