from pydantic import BaseModel, Field
from typing import List

from app.models.manifest import AgentManifest


class AgentIndexDocument(BaseModel):
    agent_id: str = Field(
        description="Уникальный детерминированный идентификатор агента (например, finance_auditor_v1)"
    )
    name: str = Field(
        description="Человекочитаемое имя агента для визуализации и лексического поиска"
    )
    description: str = Field(
        description="Подробное описание компетенций, бизнес-логики и ограничений агента"
    )
    capabilities_embedding: List[float] = Field(
        description="Плотный вектор (например, 1536 измерений), сгенерированный на основе поля description"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Массив идентификаторов других агентов, от вывода которых зависит данный узел",
    )
    manifest: AgentManifest = Field(
        description="Полная декларативная JSON-структура агента (manifest)"
    )
