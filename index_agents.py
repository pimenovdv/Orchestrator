import json
import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, ApiError
from agent_models import AgentIndexDocument

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

INDEX_NAME = "agents_index"


def create_index_if_not_exists(es_client: Elasticsearch) -> None:
    """Creates the agents index with the required mappings."""
    # Mapping based on the PDF requirements for hybrid search
    mapping = {
        "mappings": {
            "properties": {
                "agent_id": {"type": "keyword"},
                "name": {"type": "text"},
                "description": {"type": "text"},
                "capabilities_embedding": {
                    "type": "dense_vector",
                    "dims": 1536,  # Example dimension
                    "index": True,
                    "similarity": "cosine",
                },
                "dependencies": {"type": "keyword"},
                "manifest": {
                    "type": "object",
                    "enabled": False,
                },  # The manifest is returned but not indexed deeply
            }
        }
    }

    try:
        if not es_client.indices.exists(index=INDEX_NAME):
            logger.info(f"Creating index '{INDEX_NAME}'...")
            es_client.indices.create(index=INDEX_NAME, body=mapping)
            logger.info(f"Index '{INDEX_NAME}' created successfully.")
        else:
            logger.info(f"Index '{INDEX_NAME}' already exists.")
    except ApiError as e:
        logger.error(f"Error creating index: {e}")


def index_agents_from_file(es_client: Elasticsearch, file_path: str) -> None:
    """Reads agents from a JSON file and indexes them into Elasticsearch."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            agents_data = json.load(f)

        if not isinstance(agents_data, list):
            logger.error("The JSON file should contain a list of agents.")
            return

        for idx, agent_dict in enumerate(agents_data):
            try:
                # Validate with Pydantic model
                agent = AgentIndexDocument(**agent_dict)
                doc = agent.model_dump()

                # Index the document
                res = es_client.index(index=INDEX_NAME, id=agent.agent_id, document=doc)
                logger.info(
                    f"Indexed agent '{agent.agent_id}' (Result: {res['result']})"
                )

            except Exception as e:
                logger.error(f"Failed to process agent at index {idx}: {e}")

    except FileNotFoundError:
        logger.error(f"File '{file_path}' not found.")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in file '{file_path}': {e}")


def main() -> None:
    # Connect to Elasticsearch
    # Assume default localhost:9200 without auth for this example
    es = Elasticsearch(hosts=["http://localhost:9200"])

    try:
        # Check connection
        if not es.ping():
            logger.warning(
                "Could not connect to Elasticsearch at http://localhost:9200. Is it running?"
            )
            # We don't exit immediately to allow testing when ES is not available but logic is fine
        else:
            logger.info("Connected to Elasticsearch successfully.")

        create_index_if_not_exists(es)
        index_agents_from_file(es, "sample_agents.json")

        # Verify indexing
        if es.ping():
            es.indices.refresh(index=INDEX_NAME)
            res = es.count(index=INDEX_NAME)
            logger.info(f"Total documents in index '{INDEX_NAME}': {res['count']}")

    except ConnectionError as e:
        logger.error(f"Connection to Elasticsearch failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
