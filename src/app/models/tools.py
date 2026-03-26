from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal


class RestApiConfig(BaseModel):
    method: Literal["GET", "POST", "PATCH", "PUT", "DELETE"] = Field(
        description="HTTP метод (GET, POST, PATCH и др.)"
    )
    base_url: str = Field(description="Базовый URL")
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Конфигурация заголовков"
    )
    authentication: Optional[Dict[str, Any]] = Field(
        default=None, description="Правила аутентификации"
    )
    parameters_schema: Dict[str, Any] = Field(
        description="JSON Schema параметров, которые должна сгенерировать LLM (query/body)"
    )


class McpServerConfig(BaseModel):
    server_url: str = Field(description="URL сервера MCP")


class KafkaConfig(BaseModel):
    topic: str = Field(description="Топик Kafka для публикации/подписки")
    bootstrap_servers: str = Field(description="Адреса серверов брокера")
    message_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON Schema сообщения"
    )


class BuiltinConfig(BaseModel):
    function_name: str = Field(description="Имя внутренней функции/инструмента системы")


class Tool(BaseModel):
    name: str = Field(description="Имя инструмента")
    type: Literal["rest_api", "mcp_server", "kafka", "builtin"] = Field(
        description="Тип инструмента"
    )
    description: Optional[str] = Field(default=None, description="Описание инструмента")
    rest_api_config: Optional[RestApiConfig] = Field(
        default=None, description="Конфигурация для REST API инструмента"
    )
    mcp_server_config: Optional[McpServerConfig] = Field(
        default=None, description="Конфигурация для MCP сервера"
    )
    kafka_config: Optional[KafkaConfig] = Field(
        default=None, description="Конфигурация для Kafka"
    )
    builtin_config: Optional[BuiltinConfig] = Field(
        default=None, description="Конфигурация для встроенных инструментов"
    )
