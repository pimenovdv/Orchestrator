import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from opensearchpy import AsyncOpenSearch
from app.clients.agent_discovery import AgentDiscoveryClient
from app.models.registry import RegistrySearchResponse


@pytest.fixture
def mock_opensearch():
    return AsyncMock(spec=AsyncOpenSearch)


@pytest.fixture
def agent_discovery_client(mock_opensearch):
    client = AgentDiscoveryClient(opensearch_client=mock_opensearch)
    return client


@pytest.mark.asyncio
async def test_get_embedding_fallback(agent_discovery_client):
    # Ensure OPENAI_API_KEY is not set
    with patch.dict("os.environ", {}, clear=True):
        agent_discovery_client.openai_api_key = None
        embedding = await agent_discovery_client.get_embedding("test query")
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(v, float) for v in embedding)
        assert embedding[0] == 0.0


@pytest.mark.asyncio
async def test_get_embedding_with_api_key(agent_discovery_client):
    agent_discovery_client.openai_api_key = "test_key"
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        embedding = await agent_discovery_client.get_embedding("test query")
        assert embedding == [0.1, 0.2, 0.3]
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_search_candidates(agent_discovery_client, mock_opensearch):
    # Mock get_embedding
    agent_discovery_client.get_embedding = AsyncMock(return_value=[0.1] * 1536)

    # Mock OpenSearch response
    mock_response = {
        "took": 10,
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
        "hits": {
            "total": {"value": 1, "relation": "eq"},
            "max_score": 1.0,
            "hits": [
                {
                    "_index": "agents",
                    "_id": "test_agent_id",
                    "_score": 1.0,
                    "_source": {
                        "agent_id": "finance_auditor_v1",
                        "name": "Finance Auditor",
                        "description": "Audits finances",
                        "capabilities_embedding": [0.1] * 1536,
                        "dependencies": [],
                        "manifest": {
                            "name": "finance_auditor_v1",
                            "description": "Finance Auditor",
                            "input_schema": {"type": "object", "properties": {}},
                            "output_schema": {"type": "object", "properties": {}},
                            "nodes": {},
                            "edges": [],
                            "tools": [],
                            "dependencies": [],
                            "prompts": {"system_instructions": "sys desc"},
                            "graph": {"nodes": [], "edges": []},
                        },
                    },
                }
            ],
        },
    }
    mock_opensearch.search = AsyncMock(return_value=mock_response)

    response = await agent_discovery_client.search_candidates("audit finances", top_k=5)

    assert isinstance(response, RegistrySearchResponse)
    assert response.hits.total.value == 1
    assert response.hits.hits[0].source.agent_id == "finance_auditor_v1"
    agent_discovery_client.get_embedding.assert_called_once_with("audit finances")
    mock_opensearch.search.assert_called_once()

    call_args = mock_opensearch.search.call_args[1]
    assert call_args["index"] == "agents"
    assert call_args["body"]["size"] == 5
    assert (
        call_args["body"]["query"]["script_score"]["script"]["params"]["query_value"]
        == [0.1] * 1536
    )
