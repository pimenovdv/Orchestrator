from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.models.tools import Tool
from app.models.graph import MicroGraph


class ExecutionLimits(BaseModel):
    max_tokens: int = Field(default=8000, description="Максимальное количество токенов")
    timeout_ms: int = Field(
        default=60000, description="Таймаут выполнения в миллисекундах"
    )


class Prompts(BaseModel):
    system_instructions: str = Field(
        description="Системные инструкции (описание роли, формат рассуждений)"
    )
    guardrails: Optional[str] = Field(
        default=None, description="Ограничения безопасности (опционально)"
    )


class AgentManifest(BaseModel):
    input_schema: Dict[str, Any] = Field(
        description="Контракт входящих данных: JSON Schema (RFC 8259)"
    )
    output_schema: Dict[str, Any] = Field(
        description="Контракт исходящих данных: JSON Schema (RFC 8259)"
    )
    prompts: Prompts = Field(description="Системные промпты и ролевые модели")
    tools: List[Tool] = Field(
        default_factory=list, description="Набор доступных инструментов агенту"
    )
    graph: MicroGraph = Field(description="Внутренняя машина состояний (микро-граф)")
    execution_limits: ExecutionLimits = Field(
        default_factory=ExecutionLimits, description="Ограничения по выполнению"
    )
