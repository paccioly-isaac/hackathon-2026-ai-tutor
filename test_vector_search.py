#!/usr/bin/env python3
"""
Test script for vector_search function.

This script tests the vector_search functionality with MongoDB Atlas.
Requires OPENAI_API_KEY and MONGODB_DATA_STG_URI environment variables.
"""

import os
from src.database.mongo_db_io import connect_to_mongo, vector_search
from src.retrieval.embedding_generation import OpenAIEmbedder


def main():
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return

    if not os.getenv("MONGODB_DATA_STG_URI"):
        print("ERROR: MONGODB_DATA_STG_URI environment variable not set")
        return

    print("=== Testing vector_search ===\n")

    # Connect to MongoDB
    print("Test 1: Connecting to MongoDB")
    try:
        client = connect_to_mongo(None)
        print("✓ Connected to MongoDB\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}\n")
        return

    # Initialize embedder
    print("Test 2: Initializing OpenAIEmbedder")
    try:
        embedder = OpenAIEmbedder(model="text-embedding-3-large")
        print(f"✓ Initialized embedder: {embedder}\n")
    except Exception as e:
        print(f"✗ Failed to initialize embedder: {e}\n")
        return

    # TODO: Update these parameters with your actual MongoDB Atlas configuration
    # These are placeholder values - user must update them
    DATABASE_NAME = "your_database_name"
    COLLECTION_NAME = "your_collection_name"
    VECTOR_FIELD_PATH = "embedding"  # Field containing embeddings
    VECTOR_INDEX_NAME = "vector_index"  # Your Atlas Vector Search index name

    print(f"Test 3: Executing vector search")
    print(f"  Database: {DATABASE_NAME}")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Vector field: {VECTOR_FIELD_PATH}")
    print(f"  Index: {VECTOR_INDEX_NAME}\n")

    try:
        results = vector_search(
            client=client,
            database_name=DATABASE_NAME,
            collection_name=COLLECTION_NAME,
            search_query="How do I implement authentication?",
            embedder=embedder,
            vector_field_path=VECTOR_FIELD_PATH,
            vector_index_name=VECTOR_INDEX_NAME,
            top_k=5,
            num_candidates=50,
        )

        print(f"✓ Vector search completed successfully")
        print(f"  Results: {len(results)} documents\n")

        for i, doc in enumerate(results):
            score = doc.get("vectorSearchScore", "N/A")
            print(f"  Result {i+1}:")
            print(f"    Score: {score}")
            print(f"    Document ID: {doc.get('_id')}")
            # Print first 2 fields (excluding _id and score)
            field_count = 0
            for key, value in doc.items():
                if key not in ["_id", "vectorSearchScore", VECTOR_FIELD_PATH] and field_count < 2:
                    print(f"    {key}: {str(value)[:100]}")
                    field_count += 1
            print()

    except Exception as e:
        print(f"✗ Vector search failed: {e}\n")
        return

    # Test 4: Vector search with pre-filter
    print("Test 4: Vector search with pre-filter")
    try:
        results = vector_search(
            client=client,
            database_name=DATABASE_NAME,
            collection_name=COLLECTION_NAME,
            search_query="machine learning tutorial",
            embedder=embedder,
            vector_field_path=VECTOR_FIELD_PATH,
            vector_index_name=VECTOR_INDEX_NAME,
            top_k=3,
            filter={"category": "tutorial"},  # Example filter - update as needed
        )

        print(f"✓ Vector search with filter completed")
        print(f"  Results: {len(results)} documents\n")

    except Exception as e:
        print(f"✗ Vector search with filter failed: {e}\n")

    # Test 5: Error handling - empty query
    print("Test 5: Error handling for empty query")
    try:
        results = vector_search(
            client=client,
            database_name=DATABASE_NAME,
            collection_name=COLLECTION_NAME,
            search_query="",
            embedder=embedder,
            vector_field_path=VECTOR_FIELD_PATH,
            vector_index_name=VECTOR_INDEX_NAME,
            top_k=5,
        )
        print("✗ Should have raised ValueError for empty query\n")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}\n")
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")

    print("=== Tests completed ===")


if __name__ == "__main__":
    main()
