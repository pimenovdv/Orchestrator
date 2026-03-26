from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from app.models.agent import AgentIndexDocument


class OpenSearchHit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    index: str = Field(alias="_index", description="Index name")
    id: str = Field(alias="_id", description="Document ID")
    score: Optional[float] = Field(
        default=None, alias="_score", description="Relevance score"
    )
    source: AgentIndexDocument = Field(
        alias="_source", description="Agent document source"
    )


class OpenSearchTotal(BaseModel):
    value: int = Field(description="Total number of hits")
    relation: str = Field(description="Relation of the total value (e.g. eq or gte)")


class OpenSearchHits(BaseModel):
    total: OpenSearchTotal = Field(description="Total number of hits")
    max_score: Optional[float] = Field(
        default=None, description="Maximum score among hits"
    )
    hits: List[OpenSearchHit] = Field(description="List of document hits")


class RegistrySearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    took: int = Field(description="Time taken to execute the search in milliseconds")
    timed_out: bool = Field(description="Whether the search timed out")
    shards: Dict[str, Any] = Field(alias="_shards", description="Shards information")
    hits: OpenSearchHits = Field(description="Search hits")
