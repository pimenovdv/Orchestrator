from typing import Dict, List

from app.models.agent import AgentIndexDocument


def topological_sort(dag: Dict[str, AgentIndexDocument]) -> List[List[str]]:
    """
    Выполняет топологическую сортировку (алгоритм Кана) графа зависимостей агентов.
    Разделяет выполнение агентов на независимые волны (Execution Waves).
    Агенты внутри одной волны могут выполняться параллельно.

    Args:
        dag: Словарь, где ключ — agent_id, значение — AgentIndexDocument.

    Returns:
        Список волн. Каждая волна — это список agent_id, которые можно
        безопасно выполнить параллельно на данном этапе.

    Raises:
        ValueError: Если в графе есть зависимости на агентов, которых нет в dag,
                    или если обнаружен цикл (хотя предполагается предварительная проверка).
    """
    if not dag:
        return []

    # wait_counts: сколько невыполненных зависимостей осталось у агента
    wait_counts: Dict[str, int] = {agent_id: 0 for agent_id in dag}

    # dependent_on: какие агенты ждут выполнения данного агента
    # ключ: agent_id, значение: список agent_id, зависящих от него
    dependent_on: Dict[str, List[str]] = {agent_id: [] for agent_id in dag}

    # Строим графы ожидания и зависимостей
    for agent_id, agent_doc in dag.items():
        dependencies = agent_doc.dependencies

        # Уникальные зависимости для защиты от дублей в массиве
        unique_dependencies = list(set(dependencies))

        valid_dependencies_count = 0
        for dep_id in unique_dependencies:
            if dep_id not in dag:
                # В контексте оркестратора, отсутствие зависимости в DAG — это ошибка
                raise ValueError(
                    f"Agent '{agent_id}' depends on '{dep_id}' which is not present in the DAG."
                )

            dependent_on[dep_id].append(agent_id)
            valid_dependencies_count += 1

        wait_counts[agent_id] = valid_dependencies_count

    waves: List[List[str]] = []

    # Находим агентов без зависимостей (корневые агенты)
    current_wave = [agent_id for agent_id, count in wait_counts.items() if count == 0]

    executed_count = 0

    while current_wave:
        # Добавляем текущую волну (сортируем для детерминированности, полезно для тестов)
        current_wave.sort()
        waves.append(current_wave)
        executed_count += len(current_wave)

        next_wave: List[str] = []

        # Имитируем выполнение агентов текущей волны
        for agent_id in current_wave:
            # Для каждого агента, который ждал выполнения current_wave
            for waiting_agent_id in dependent_on[agent_id]:
                wait_counts[waiting_agent_id] -= 1
                # Если все зависимости удовлетворены, агент готов к выполнению в следующей волне
                if wait_counts[waiting_agent_id] == 0:
                    next_wave.append(waiting_agent_id)

        current_wave = next_wave

    # Если мы выполнили не всех агентов, но волн больше нет — значит есть цикл
    if executed_count < len(dag):
        raise ValueError("Cannot perform topological sort: cyclic dependency detected.")

    return waves
