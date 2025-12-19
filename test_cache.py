#!/usr/bin/env python3
"""
Test script to demonstrate GitHub data caching functionality
"""

import sys
import importlib.util
from pathlib import Path

# Load GitHubCollector directly from file to avoid package __init__ issues
github_module_path = Path(__file__).parent / "evaluator" / "collectors" / "github.py"
spec = importlib.util.spec_from_file_location("github_collector", github_module_path)
github_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(github_module)

GitHubCollector = github_module.GitHubCollector


def test_repo_caching():
    """Test repository data caching"""
    print("=" * 60)
    print("Testing Repository Data Caching")
    print("=" * 60)

    # Initialize collector with data directory
    collector = GitHubCollector(cache_dir="data")

    # Test with a sample repo URL
    test_repo = "https://github.com/anthropics/anthropic-sdk-python"

    print("\n1. First request (should fetch and cache):")
    print("-" * 60)
    data1 = collector.collect_repo_data(test_repo)
    print(f"Repository: {data1.get('repo_name')}")
    print(f"Cache location: {collector._get_cache_path(test_repo)}")

    print("\n2. Second request (should load from cache):")
    print("-" * 60)
    data2 = collector.collect_repo_data(test_repo)
    print(f"Repository: {data2.get('repo_name')}")

    print("\n3. Force fresh fetch (bypassing cache):")
    print("-" * 60)
    data3 = collector.collect_repo_data(test_repo, use_cache=False)
    print(f"Repository: {data3.get('repo_name')}")

    # Test with another repo to show directory structure
    print("\n4. Different repository:")
    print("-" * 60)
    test_repo2 = "https://github.com/openai/openai-python"
    data4 = collector.collect_repo_data(test_repo2)
    print(f"Repository: {data4.get('repo_name')}")
    print(f"Cache location: {collector._get_cache_path(test_repo2)}")


def test_user_caching():
    """Test user data caching"""
    print("\n" + "=" * 60)
    print("Testing User Data Caching")
    print("=" * 60)

    collector = GitHubCollector(cache_dir="data")

    test_user = "torvalds"

    print("\n1. First request for user (should fetch and cache):")
    print("-" * 60)
    data1 = collector.collect_user_data(test_user)
    user_url = f"https://github.com/{test_user}"
    print(f"User: {test_user}")
    print(f"Cache location: {collector._get_cache_path(user_url)}")

    print("\n2. Second request for user (should load from cache):")
    print("-" * 60)
    data2 = collector.collect_user_data(test_user)
    print(f"User: {test_user}")
    print(f"Total contributions: {data2.get('total_contributions')}")


def show_cache_structure():
    """Display the cache directory structure"""
    print("\n" + "=" * 60)
    print("Cache Directory Structure")
    print("=" * 60)

    import os
    from pathlib import Path

    cache_dir = Path("data")
    if cache_dir.exists():
        print(f"\nContents of '{cache_dir}':")
        for root, dirs, files in os.walk(cache_dir):
            level = root.replace(str(cache_dir), '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = Path(root) / file
                size = file_path.stat().st_size
                print(f'{subindent}{file} ({size} bytes)')
    else:
        print(f"\nCache directory '{cache_dir}' does not exist yet.")


if __name__ == "__main__":
    print("GitHub Data Caching Test\n")

    # Run tests
    test_repo_caching()
    test_user_caching()
    show_cache_structure()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    print("\nNotes:")
    print("- First requests fetch data and save to cache")
    print("- Subsequent requests load from cache (faster)")
    print("- Cache files are organized by owner/repo structure")
    print("- User data is cached in data/users/ directory")
    print("- Use use_cache=False to force fresh data fetch")
