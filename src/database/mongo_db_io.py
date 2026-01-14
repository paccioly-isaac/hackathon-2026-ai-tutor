import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from loguru import logger

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))
from retrieval.embedding_generation import Embedder


def connect_to_mongo(input_uri):
    load_dotenv()

    if input_uri:
        uri = input_uri
    else:
        uri = os.getenv("MONGODB_DATA_STG_URI")
    if not uri:
        raise ValueError("MONGODB_DATA_STG_URI not found in environment variables")
    client = MongoClient(uri, server_api=ServerApi("1"))

    try:
        client.admin.command("ping")
        logger.info("✓ Connected to MongoDB")
        return client
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")


def get_cluster_paths(client: MongoClient):
    """
    Return all available database-collection combinations as a list of tuples.
    Each tuple contains (database_name, collection_name).
    """
    cluster_paths = []
    # System databases that require special permissions
    system_databases = ["admin", "config", "local"]

    try:
        database_names = client.list_database_names()
        for db_name in database_names:
            # Skip system databases
            if db_name in system_databases:
                logger.info(f"Skipping system database: {db_name}")
                continue

            db = client[db_name]
            collection_names = db.list_collection_names()
            for coll_name in collection_names:
                cluster_paths.append((db_name, coll_name))
    except Exception as e:
        logger.error(f"Error fetching cluster paths: {e}")
        raise
    return cluster_paths


def load_mongo_collection(
    database_name: str, collection_name: str, limit: int | None = None
) -> list:
    """
    Connect to MongoDB and load documents from the specified collection.

    Args:
        database_name: Name of the MongoDB database.
        collection_name: Name of the collection to load.
        limit: Optional maximum number of documents to load. If None, loads all documents.

    Returns:
        list: List of documents from the collection.

    Raises:
        ValueError: If the MongoDB URI is not found.
        ConnectionError: If connection to MongoDB fails.
    """
    logger.info("Connecting to db")
    client = connect_to_mongo()
    db = client[database_name]
    collection_evaluations_view = db[collection_name]

    if limit:
        logger.info(f"Loading {limit} documents from collection...")
        evaluations = list(collection_evaluations_view.find().limit(limit))
    else:
        logger.info("Loading all documents from collection...")
        evaluations = list(collection_evaluations_view.find())

    logger.info(f"Loaded {len(evaluations)} documents")
    return evaluations


def upload_asset_to_mongo(
    client: MongoClient,
    database_name: str,
    collection_name: str,
    asset_to_upload: dict,
    validate: bool = True,
) -> dict:
    """
    Upload an asset (document) to a specified MongoDB collection.

    Args:
        client: MongoClient instance.
        database_name: Name of the MongoDB database.
        collection_name: Name of the collection to upload to.
        asset_to_upload: Dictionary containing the asset data to upload.
        validate: Whether to validate against schema before uploading (default: True).

    Returns:
        dict: Status dictionary with keys:
            - 'success': bool indicating if upload was successful
            - 'inserted_id': ObjectId of the inserted document (if successful)
            - 'message': str describing the result
            - 'error': str error message (if failed)

    Raises:
        ValueError: If asset_to_upload is not a dictionary.
    """
    if not isinstance(asset_to_upload, dict):
        raise ValueError("asset_to_upload must be a dictionary")

    # Optional schema validation
    if validate:
        try:
            from infra.databases.mongo_db.schemas.asset_schemas import validate_asset

            validated_model = validate_asset(
                database_name, collection_name, asset_to_upload
            )
            # Convert back to dict for MongoDB (excludes None values, uses aliases, etc.)
            asset_to_upload = validated_model.model_dump(
                by_alias=True, exclude_none=True
            )
            logger.info("✓ Asset validated against schema")
        except ValueError as e:
            logger.warning(f"No schema validation available: {e}")
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                "success": False,
                "inserted_id": None,
                "message": "Schema validation failed",
                "error": str(e),
            }

    try:
        db = client[database_name]
        collection = db[collection_name]

        logger.info(f"Uploading asset to {database_name}.{collection_name}")
        result = collection.insert_one(asset_to_upload)

        logger.info(f"✓ Asset uploaded successfully with ID: {result.inserted_id}")
        return {
            "success": True,
            "inserted_id": result.inserted_id,
            "message": f"Asset uploaded successfully to {database_name}.{collection_name}",
        }
    except Exception as e:
        logger.error(f"Failed to upload asset: {e}")
        return {
            "success": False,
            "inserted_id": None,
            "message": "Failed to upload asset",
            "error": str(e),
        }


def vector_search(
    client: MongoClient,
    database_name: str,
    collection_name: str,
    search_query: str,
    embedder: Embedder,
    vector_field_path: str,
    vector_index_name: str,
    top_k: int,
    num_candidates: int | None = None,
    filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Perform semantic vector search on a MongoDB Atlas collection.

    Uses MongoDB Atlas Vector Search to find documents semantically similar to
    the search query. The query is embedded using the provided embedder, then
    MongoDB's $vectorSearch aggregation stage finds the top_k nearest neighbors.

    Args:
        client: MongoClient instance connected to MongoDB Atlas.
        database_name: Name of the MongoDB database.
        collection_name: Name of the collection to search.
        search_query: Text query to search for (will be embedded).
        embedder: Embedder instance (e.g., OpenAIEmbedder) to generate query embedding.
        vector_field_path: Field path in documents containing vector embeddings.
        vector_index_name: Name of the MongoDB Atlas Vector Search index.
        top_k: Number of nearest neighbors to return.
        num_candidates: Optional number of candidates for ANN search. If None, defaults
            to min(top_k * 10, 10000) following MongoDB best practices (10x top_k).
        filter: Optional pre-filter conditions to apply before vector search.
            Only documents matching the filter will be considered.
            Must use indexed fields. Example: {"category": "tutorial", "year": {"$gte": 2020}}

    Returns:
        list[dict[str, Any]]: List of documents sorted by similarity (highest first).
            Each document includes a 'vectorSearchScore' field with the similarity score.

    Raises:
        ValueError: If search_query is empty or embedder fails to generate embedding.
        ConnectionError: If MongoDB connection fails.
        Exception: If vector search query fails (e.g., invalid index name, field path).

    Example:
        >>> from retrieval.embedding_generation import OpenAIEmbedder
        >>> client = connect_to_mongo(None)
        >>> embedder = OpenAIEmbedder(model="text-embedding-3-large")
        >>> results = vector_search(
        ...     client=client,
        ...     database_name="knowledge_base",
        ...     collection_name="documents",
        ...     search_query="How do I implement authentication?",
        ...     embedder=embedder,
        ...     vector_field_path="embedding",
        ...     vector_index_name="vector_index",
        ...     top_k=5,
        ...     num_candidates=50,
        ...     filter={"category": "tutorial"}
        ... )
        >>> for doc in results:
        ...     print(f"Score: {doc['vectorSearchScore']:.4f}, Title: {doc['title']}")
    """
    # Validate search query
    if not search_query or search_query.strip() == "":
        raise ValueError("search_query cannot be empty")

    # Generate query embedding
    logger.info(f"Embedding search query: '{search_query}'")
    try:
        query_vector = embedder.embed(search_query)
        if query_vector is None:
            raise ValueError("Embedder returned None for search query")
        logger.info(f"Generated query embedding with {len(query_vector)} dimensions")
    except Exception as e:
        logger.error(f"Failed to embed search query: {e}")
        raise ValueError(f"Failed to generate embedding for search query: {e}")

    # Set default num_candidates if not provided (MongoDB best practice: 10x top_k, capped at 10000)
    if num_candidates is None:
        num_candidates = min(top_k * 10, 10000)
        logger.info(f"Using default num_candidates={num_candidates} (10x top_k)")

    # Build vector search aggregation pipeline
    vector_search_stage: dict[str, Any] = {
        "$vectorSearch": {
            "index": vector_index_name,
            "path": vector_field_path,
            "queryVector": query_vector,
            "numCandidates": num_candidates,
            "limit": top_k,
        }
    }

    # Add optional pre-filter
    if filter is not None:
        vector_search_stage["$vectorSearch"]["filter"] = filter
        logger.info(f"Applying pre-filter: {filter}")

    # Add projection stage to include vectorSearchScore
    project_stage = {
        "$project": {
            "vectorSearchScore": {"$meta": "vectorSearchScore"},
            # Include all document fields (MongoDB includes all fields by default, but we
            # explicitly request vectorSearchScore via $meta)
        }
    }

    pipeline = [vector_search_stage, project_stage]

    # Execute vector search
    try:
        db = client[database_name]
        collection = db[collection_name]

        logger.info(
            f"Executing vector search on {database_name}.{collection_name} "
            f"(index={vector_index_name}, top_k={top_k}, num_candidates={num_candidates})"
        )

        results = list(collection.aggregate(pipeline))

        logger.info(f"Vector search returned {len(results)} documents")

        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise Exception(f"Failed to execute vector search: {e}")
