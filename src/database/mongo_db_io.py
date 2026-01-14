import os

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from loguru import logger


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
