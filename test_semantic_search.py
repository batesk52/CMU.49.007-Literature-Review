#!/usr/bin/env python3
"""
Unit tests for the semantic search module.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.close()
    yield temp_file.name
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture(autouse=True)
def mock_openai_key(monkeypatch):
    """Mock OpenAI API key for all tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    # Clear any cached config by reloading the modules
    import sys
    if 'config' in sys.modules:
        del sys.modules['config']
    if 'semantic_search' in sys.modules:
        del sys.modules['semantic_search']
    # Now import after setting the env var
    global SemanticSearch
    from semantic_search import SemanticSearch


@pytest.fixture
def sample_embedding():
    """Sample embedding vector."""
    return [0.1] * 1536  # 1536 dimensions for text-embedding-3-small


def test_initialization(mock_openai_key, temp_cache_file):
    """Test SemanticSearch initialization."""
    from semantic_search import SemanticSearch
    search = SemanticSearch(temp_cache_file)
    # Check that API key is set (don't check exact value as it may vary between test runs)
    assert search.openai_api_key is not None
    assert search.embedding_model == "text-embedding-3-small"
    assert search.embedding_dimension == 1536


def test_initialization_without_api_key(temp_cache_file):
    """Test initialization without API key."""
    # Import config module to reset it
    from config import reset_config
    
    # Remove API key if exists
    original = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    # Reset the global config to ensure it re-reads environment
    reset_config()
    
    # Clear cached modules to ensure fresh import
    import sys
    if 'semantic_search' in sys.modules:
        del sys.modules['semantic_search']
    
    try:
        from semantic_search import SemanticSearch
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
            SemanticSearch(temp_cache_file)
    finally:
        # Restore API key
        if original:
            os.environ["OPENAI_API_KEY"] = original
        # Reset config again to pick up restored environment
        reset_config()


def test_load_existing_cache(mock_openai_key):
    """Test loading existing embeddings cache."""
    # Create a cache file with data
    cache_data = {
        "metadata": {
            "model": "text-embedding-3-small",
            "created": "2025-01-01T00:00:00",
            "last_updated": "2025-01-01T00:00:00"
        },
        "embeddings": {
            "test_key": [0.1] * 1536
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cache_data, f)
        temp_file = f.name
    
    try:
        from semantic_search import SemanticSearch
        search = SemanticSearch(temp_file)
        assert len(search.embeddings_cache["embeddings"]) == 1
        assert "test_key" in search.embeddings_cache["embeddings"]
    finally:
        os.unlink(temp_file)


def test_save_embeddings_cache(mock_openai_key, temp_cache_file):
    """Test saving embeddings cache."""
    search = SemanticSearch(temp_cache_file)
    
    # Add some data
    search.embeddings_cache["embeddings"]["test_key"] = [0.1] * 10
    search._save_embeddings_cache()
    
    # Verify file was saved
    assert Path(temp_cache_file).exists()
    
    # Load and verify content
    with open(temp_cache_file, 'r') as f:
        data = json.load(f)
    
    assert "test_key" in data["embeddings"]
    assert data["metadata"]["last_updated"] is not None


def test_create_cache_key(mock_openai_key, temp_cache_file):
    """Test cache key creation."""
    search = SemanticSearch(temp_cache_file)
    
    key1 = search._create_cache_key("test text", "file.md")
    key2 = search._create_cache_key("test text", "file.md")
    key3 = search._create_cache_key("different text", "file.md")
    
    # Same input should produce same key
    assert key1 == key2
    # Different input should produce different key
    assert key1 != key3


def test_cosine_similarity(mock_openai_key, temp_cache_file):
    """Test cosine similarity calculation."""
    search = SemanticSearch(temp_cache_file)
    
    # Test identical vectors
    vec1 = [1.0, 0.0, 0.0]
    similarity = search.cosine_similarity(vec1, vec1)
    assert pytest.approx(similarity, 0.001) == 1.0
    
    # Test orthogonal vectors
    vec2 = [0.0, 1.0, 0.0]
    similarity = search.cosine_similarity(vec1, vec2)
    assert pytest.approx(similarity, 0.001) == 0.0
    
    # Test zero vectors
    vec_zero = [0.0, 0.0, 0.0]
    similarity = search.cosine_similarity(vec_zero, vec1)
    assert similarity == 0.0


@patch('requests.post')
def test_request_embedding_success(mock_post, mock_openai_key, temp_cache_file, sample_embedding):
    """Test successful embedding request."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"embedding": sample_embedding}]
    }
    mock_post.return_value = mock_response
    
    search = SemanticSearch(temp_cache_file)
    embedding = search._request_embedding("test text")
    
    assert embedding == sample_embedding
    mock_post.assert_called_once()


@patch('requests.post')
def test_request_embedding_rate_limit(mock_post, mock_openai_key, temp_cache_file, sample_embedding):
    """Test handling rate limit errors."""
    # Mock rate limit then success
    mock_response_429 = Mock()
    mock_response_429.status_code = 429
    
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "data": [{"embedding": sample_embedding}]
    }
    
    mock_post.side_effect = [mock_response_429, mock_response_200]
    
    search = SemanticSearch(temp_cache_file)
    search.retry_delay = 0.01  # Speed up test
    
    embedding = search._request_embedding("test text")
    
    assert embedding == sample_embedding
    assert mock_post.call_count == 2


@patch('requests.post')
def test_request_embedding_failure(mock_post, mock_openai_key, temp_cache_file):
    """Test embedding request failure."""
    # Mock error response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response
    
    search = SemanticSearch(temp_cache_file)
    search.max_retries = 1  # Reduce retries for test
    
    embedding = search._request_embedding("test text")
    
    assert embedding is None


@patch('semantic_search.SemanticSearch._request_embedding')
def test_get_embedding_with_cache(mock_request, mock_openai_key, temp_cache_file, sample_embedding):
    """Test getting embedding with caching."""
    mock_request.return_value = sample_embedding
    
    search = SemanticSearch(temp_cache_file)
    
    # First call should request from API
    embedding1 = search.get_embedding("test text", "file.md")
    assert embedding1 == sample_embedding
    assert mock_request.call_count == 1
    
    # Second call should use cache
    embedding2 = search.get_embedding("test text", "file.md")
    assert embedding2 == sample_embedding
    assert mock_request.call_count == 1  # No additional API call


@patch('semantic_search.SemanticSearch.get_embedding')
def test_build_embeddings_for_database(mock_get_embedding, mock_openai_key, temp_cache_file, sample_embedding):
    """Test building embeddings for database."""
    mock_get_embedding.return_value = sample_embedding
    
    # Mock knowledge database
    mock_db = Mock()
    mock_db.get_all_files.return_value = [
        {"file_path": "/path/file1.md", "summary": "Summary 1"},
        {"file_path": "/path/file2.md", "summary": "Summary 2"},
        {"file_path": "/path/file3.md", "summary": ""}  # No summary
    ]
    
    search = SemanticSearch(temp_cache_file)
    created = search.build_embeddings_for_database(mock_db)
    
    assert created == 2  # Only files with summaries
    assert mock_get_embedding.call_count == 2


@patch('semantic_search.SemanticSearch.get_embedding')
def test_semantic_search_functionality(mock_get_embedding, mock_openai_key, temp_cache_file):
    """Test semantic search functionality."""
    # Create different embeddings with varying similarity
    query_embedding = [1.0, 0.0, 0.0]
    file1_embedding = [0.9, 0.1, 0.0]  # High similarity
    file2_embedding = [0.1, 0.9, 0.1]  # Low similarity
    file3_embedding = [0.8, 0.2, 0.0]  # Medium similarity
    
    # Mock get_embedding to return query embedding
    mock_get_embedding.return_value = query_embedding
    
    # Create search instance with pre-populated cache
    search = SemanticSearch(temp_cache_file)
    
    # Add file embeddings to cache
    search.embeddings_cache["embeddings"] = {
        search._create_cache_key("Summary 1", "/path/file1.md"): file1_embedding,
        search._create_cache_key("Summary 2", "/path/file2.md"): file2_embedding,
        search._create_cache_key("Summary 3", "/path/file3.md"): file3_embedding
    }
    
    # Mock knowledge database
    mock_db = Mock()
    mock_db.get_all_files.return_value = [
        {
            "file_path": "/path/file1.md",
            "filename": "file1.md",
            "summary": "Summary 1",
            "content_length": 1000,
            "added_to_db": "2025-01-01"
        },
        {
            "file_path": "/path/file2.md",
            "filename": "file2.md",
            "summary": "Summary 2",
            "content_length": 2000,
            "added_to_db": "2025-01-02"
        },
        {
            "file_path": "/path/file3.md",
            "filename": "file3.md",
            "summary": "Summary 3",
            "content_length": 3000,
            "added_to_db": "2025-01-03"
        }
    ]
    
    # Perform search with low threshold to get all results
    results = search.semantic_search("test query", mock_db, top_k=3, similarity_threshold=0.0)
    
    assert len(results) == 3
    # Results should be sorted by similarity
    assert results[0]["filename"] == "file1.md"  # Highest similarity
    assert results[1]["filename"] == "file3.md"  # Medium similarity
    assert results[2]["filename"] == "file2.md"  # Lowest similarity
    
    # Test with higher threshold
    results = search.semantic_search("test query", mock_db, top_k=3, similarity_threshold=0.8)
    assert len(results) < 3  # Should filter out low similarity results


def test_get_cache_stats(mock_openai_key, temp_cache_file):
    """Test cache statistics."""
    search = SemanticSearch(temp_cache_file)
    
    # Add some embeddings
    search.embeddings_cache["embeddings"] = {
        "key1": [0.1] * 10,
        "key2": [0.2] * 10
    }
    search._save_embeddings_cache()
    
    stats = search.get_cache_stats()
    
    assert stats["total_embeddings"] == 2
    assert stats["cache_file_exists"] is True
    assert stats["cache_file_size"] > 0
    assert stats["model_used"] == "text-embedding-3-small"


def test_semantic_search_no_query_embedding(mock_openai_key, temp_cache_file):
    """Test semantic search when query embedding fails."""
    search = SemanticSearch(temp_cache_file)
    
    # Mock get_embedding to return None (failure)
    with patch.object(search, 'get_embedding', return_value=None):
        mock_db = Mock()
        results = search.semantic_search("test query", mock_db)
        
        assert results == []


def test_semantic_search_missing_file_embedding(mock_openai_key, temp_cache_file):
    """Test semantic search with missing file embeddings."""
    search = SemanticSearch(temp_cache_file)
    
    # Mock successful query embedding
    with patch.object(search, 'get_embedding', return_value=[1.0, 0.0, 0.0]):
        # Mock database with files but no embeddings in cache
        mock_db = Mock()
        mock_db.get_all_files.return_value = [
            {"file_path": "/path/file1.md", "summary": "Summary 1"}
        ]
        
        results = search.semantic_search("test query", mock_db)
        
        # Should return empty results since no file embeddings exist
        assert results == []


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()