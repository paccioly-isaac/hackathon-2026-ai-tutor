#!/usr/bin/env python3
"""
Quick test script for OpenAIEmbedder.

This script tests basic functionality of the OpenAIEmbedder class.
Requires OPENAI_API_KEY environment variable to be set.
"""

import os
from src.retrieval.embedding_generation import OpenAIEmbedder


def main():
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        return

    print("=== Testing OpenAIEmbedder ===\n")

    # Test 1: Initialization with defaults
    print("Test 1: Initializing OpenAIEmbedder with default model (text-embedding-3-large)")
    try:
        embedder = OpenAIEmbedder()
        print(f"✓ Initialized: {embedder}")
        print(f"  Model: {embedder.model}")
        print(f"  Embedding dimension: {embedder.embedding_dimension}")
        config = embedder.get_config()
        print(f"  Config: {config}\n")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}\n")
        return

    # Test 2: Single embedding
    print("Test 2: Generating single embedding")
    try:
        test_text = "Hello world"
        embedding = embedder.embed(test_text)
        if embedding:
            print(f"✓ Generated embedding for '{test_text}'")
            print(f"  Embedding length: {len(embedding)}")
            print(f"  First 5 values: {embedding[:5]}\n")
        else:
            print(f"✗ Got None result for '{test_text}'\n")
    except Exception as e:
        print(f"✗ Failed to generate embedding: {e}\n")
        return

    # Test 3: Batch embedding
    print("Test 3: Generating batch embeddings")
    try:
        test_texts = [
            "Artificial intelligence",
            "Machine learning",
            "Natural language processing"
        ]
        embeddings = embedder.batch_embed(test_texts)
        if embeddings:
            print(f"✓ Generated {len(embeddings)} embeddings")
            for i, text in enumerate(test_texts):
                print(f"  Text {i+1}: '{text}' -> {len(embeddings[i])} dimensions")
            print()
        else:
            print(f"✗ Got None result for batch\n")
    except Exception as e:
        print(f"✗ Failed to generate batch embeddings: {e}\n")
        return

    # Test 4: Different model (text-embedding-3-small)
    print("Test 4: Using text-embedding-3-small model")
    try:
        small_embedder = OpenAIEmbedder(model="text-embedding-3-small")
        print(f"✓ Initialized: {small_embedder}")
        print(f"  Embedding dimension: {small_embedder.embedding_dimension}")

        embedding = small_embedder.embed("Test with small model")
        if embedding:
            print(f"✓ Generated embedding with {len(embedding)} dimensions\n")
        else:
            print("✗ Got None result\n")
    except Exception as e:
        print(f"✗ Failed with small model: {e}\n")

    # Test 5: Dimension reduction
    print("Test 5: Using dimension reduction")
    try:
        reduced_embedder = OpenAIEmbedder(
            model="text-embedding-3-large",
            dimensions=1024
        )
        print(f"✓ Initialized with dimension reduction: {reduced_embedder}")
        print(f"  Configured dimensions: {reduced_embedder.dimensions}")
        print(f"  Embedding dimension: {reduced_embedder.embedding_dimension}")

        embedding = reduced_embedder.embed("Test with reduced dimensions")
        if embedding:
            print(f"✓ Generated embedding with {len(embedding)} dimensions")
            assert len(embedding) == 1024, f"Expected 1024 dimensions, got {len(embedding)}"
            print("✓ Dimension reduction working correctly\n")
        else:
            print("✗ Got None result\n")
    except Exception as e:
        print(f"✗ Failed with dimension reduction: {e}\n")

    # Test 6: Error handling - empty text
    print("Test 6: Error handling for empty text")
    try:
        embedding = embedder.embed("")
        print(f"✗ Should have raised ValueError for empty text\n")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}\n")
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")

    # Test 7: Invalid model
    print("Test 7: Error handling for invalid model")
    try:
        invalid_embedder = OpenAIEmbedder(model="invalid-model")
        print(f"✗ Should have raised ValueError for invalid model\n")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}\n")
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")

    # Test 8: Dimension reduction with ada-002 (should fail)
    print("Test 8: Error handling for dimension reduction with ada-002")
    try:
        invalid_embedder = OpenAIEmbedder(
            model="text-embedding-ada-002",
            dimensions=768
        )
        print(f"✗ Should have raised ValueError for ada-002 with dimensions\n")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}\n")
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")

    print("=== All tests completed ===")


if __name__ == "__main__":
    main()
