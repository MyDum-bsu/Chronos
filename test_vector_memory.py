#!/usr/bin/env python3
"""Test script for VectorMemory functionality."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory.vector import VectorMemory


async def main() -> None:
    """Run vector memory tests."""
    print("Initializing VectorMemory...")
    vm = VectorMemory(collection_name="test_collection", persist_directory="./chroma_data_test")
    
    # Clear any existing test data
    print("\nClearing existing test memories...")
    deleted = await vm.clear_user_memories(999)
    print(f"Deleted {deleted} existing memories")
    
    # Test data
    user_id = 999
    memories = [
        "I love programming in Python",
        "Python is a great language for data science",
        "The weather today is sunny and warm",
        "I need to buy groceries tomorrow",
        "My favorite movie is Inception",
    ]
    
    print("\nStoring memories...")
    memory_ids = []
    for i, text in enumerate(memories):
        memory_id = await vm.remember(user_id, text, metadata={"index": i})
        memory_ids.append(memory_id)
        print(f"  Stored: '{text[:50]}...' with ID: {memory_id}")
    
    print("\nRecalling memories with semantic search...")
    
    # Test queries
    queries = [
        "What programming language do I like?",
        "Tell me about my movie preferences",
        "What do I need to do tomorrow?",
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = await vm.recall(user_id, query, n_results=3)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result}")
    
    print("\nDeleting a specific memory...")
    if memory_ids:
        vm.delete_memory(memory_ids[0])
        print(f"  Deleted memory ID: {memory_ids[0]}")
    
    print("\nRecalling after deletion (should not see first memory):")
    results = await vm.recall(user_id, "programming Python", n_results=3)
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")
    
    print("\nClearing all user memories...")
    deleted = await vm.clear_user_memories(user_id)
    print(f"Deleted {deleted} memories")
    
    print("\nTest complete! ✅")


if __name__ == "__main__":
    asyncio.run(main())
