#!/usr/bin/env python3
"""
Test suite for the semantic_search_v2 module.

This module tests the enhanced semantic search functionality with multiple API providers,
embeddings caching, and vector similarity calculations.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module we're testing
from semantic_search_v2 import SemanticSearchV2


class TestSemanticSearchV2:
    """Test suite for SemanticSearchV2 class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = Path(self.temp_dir) / "test_embeddings_cache.json"
        
        # Mock API provider
        self.mock_provider = Mock()
        self.mock_provider.__class__.__name__ = "TestProvider"
        self.mock_provider.get_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Mock knowledge database
        self.mock_db = Mock()
        self.mock_db.get_all_files_dict.return_value = {
            "file1.md": {
                "file_path": "/path/to/file1.md",
                "summary": "Test summary 1",
                "content_length": 100
            },
            "file2.md": {
                "file_path": "/path/to/file2.md", 
                "summary": "Test summary 2",
                "content_length": 200
            }
        }
        
    def teardown_method(self):
        """Clean up after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_initialization_success(self, mock_factory):
        """Test successful initialization with provider."""
        mock_factory.return_value = self.mock_provider
        
        search = SemanticSearchV2(
            embeddings_cache_path=str(self.cache_path),
            provider_name="test"
        )
        
        assert search.provider == self.mock_provider
        assert search.provider_name == "Test"
        assert search.embeddings_cache_path == self.cache_path
        assert isinstance(search.embeddings_cache, dict)
        assert "metadata" in search.embeddings_cache
        assert "embeddings" in search.embeddings_cache
        
        mock_factory.assert_called_once_with("test")
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_initialization_with_existing_cache(self, mock_factory):
        """Test initialization with existing cache file."""
        mock_factory.return_value = self.mock_provider
        
        # Create existing cache
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        existing_cache = {
            "metadata": {
                "providers": {"test": 5},
                "created": "2024-01-01T10:00:00",
                "last_updated": "2024-01-01T11:00:00"
            },
            "embeddings": {
                "file1.md": {
                    "embedding": [0.1, 0.2, 0.3],
                    "provider": "test",
                    "timestamp": "2024-01-01T10:30:00"
                }
            }
        }
        
        with open(self.cache_path, 'w') as f:
            json.dump(existing_cache, f)
        
        search = SemanticSearchV2(
            embeddings_cache_path=str(self.cache_path),
            provider_name="test"
        )
        
        assert len(search.embeddings_cache["embeddings"]) == 1
        assert "file1.md" in search.embeddings_cache["embeddings"]
        assert search.embeddings_cache["metadata"]["created"] == "2024-01-01T10:00:00"
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_initialization_provider_failure(self, mock_factory):
        """Test initialization when provider creation fails."""
        mock_factory.side_effect = ValueError("No API key found")
        
        with pytest.raises(ValueError) as exc_info:
            SemanticSearchV2(
                embeddings_cache_path=str(self.cache_path),
                provider_name="invalid"
            )
        
        assert "No API key found" in str(exc_info.value)
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_get_embedding_new(self, mock_factory):
        """Test getting embedding for new text."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Get embedding
        embedding = search.get_embedding("Test text", "test.md")
        
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        self.mock_provider.get_embedding.assert_called_once_with("Test text")
        
        # Check it was cached
        assert "test.md" in search.embeddings_cache["embeddings"]
        assert search.embeddings_cache["embeddings"]["test.md"]["embedding"] == embedding
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_get_embedding_cached(self, mock_factory):
        """Test getting embedding from cache."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Pre-populate cache
        search.embeddings_cache["embeddings"]["test.md"] = {
            "embedding": [0.9, 0.8, 0.7],
            "provider": "Test",
            "timestamp": datetime.now().isoformat()
        }
        
        # Get embedding (should come from cache)
        embedding = search.get_embedding("Test text", "test.md")
        
        assert embedding == [0.9, 0.8, 0.7]
        self.mock_provider.get_embedding.assert_not_called()
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_get_embedding_different_provider(self, mock_factory):
        """Test getting embedding when provider changes."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Pre-populate cache with different provider
        search.embeddings_cache["embeddings"]["test.md"] = {
            "embedding": [0.9, 0.8, 0.7],
            "provider": "DifferentProvider",
            "timestamp": datetime.now().isoformat()
        }
        
        # Get embedding (should regenerate due to different provider)
        embedding = search.get_embedding("Test text", "test.md")
        
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        self.mock_provider.get_embedding.assert_called_once()
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_get_embedding_api_failure(self, mock_factory):
        """Test handling of API failures when getting embeddings."""
        mock_factory.return_value = self.mock_provider
        self.mock_provider.get_embedding.side_effect = Exception("API error")
        
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Get embedding should return None on error
        embedding = search.get_embedding("Test text", "test.md")
        
        assert embedding is None
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_cosine_similarity(self, mock_factory):
        """Test cosine similarity calculation."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        similarity = search.cosine_similarity(vec1, vec1)
        assert abs(similarity - 1.0) < 0.0001
        
        # Test orthogonal vectors
        vec2 = [0.0, 1.0, 0.0]
        similarity = search.cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.0001
        
        # Test opposite vectors
        vec3 = [-1.0, 0.0, 0.0]
        similarity = search.cosine_similarity(vec1, vec3)
        assert abs(similarity - (-1.0)) < 0.0001
        
        # Test arbitrary vectors
        vec4 = [0.6, 0.8, 0.0]
        vec5 = [0.8, 0.6, 0.0]
        similarity = search.cosine_similarity(vec4, vec5)
        assert 0.9 < similarity < 1.0
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_cosine_similarity_zero_vector(self, mock_factory):
        """Test cosine similarity with zero vectors."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        vec1 = [1.0, 2.0, 3.0]
        vec_zero = [0.0, 0.0, 0.0]
        
        similarity = search.cosine_similarity(vec1, vec_zero)
        assert similarity == 0.0
        
        similarity = search.cosine_similarity(vec_zero, vec_zero)
        assert similarity == 0.0
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_build_embeddings_for_database(self, mock_factory):
        """Test building embeddings for entire database."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Build embeddings
        count = search.build_embeddings_for_database(self.mock_db)
        
        assert count == 2
        assert self.mock_provider.get_embedding.call_count == 2
        assert "file1.md" in search.embeddings_cache["embeddings"]
        assert "file2.md" in search.embeddings_cache["embeddings"]
        
        # Check cache was saved
        assert self.cache_path.exists()
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_build_embeddings_force_rebuild(self, mock_factory):
        """Test force rebuilding embeddings."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Pre-populate cache
        search.embeddings_cache["embeddings"]["file1.md"] = {
            "embedding": [0.9, 0.8, 0.7],
            "provider": "Test",
            "timestamp": datetime.now().isoformat()
        }
        
        # Build with force_rebuild
        count = search.build_embeddings_for_database(self.mock_db, force_rebuild=True)
        
        assert count == 2
        assert self.mock_provider.get_embedding.call_count == 2
        # Check embedding was updated
        assert search.embeddings_cache["embeddings"]["file1.md"]["embedding"] == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_semantic_search(self, mock_factory):
        """Test semantic search functionality."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Pre-populate embeddings
        search.embeddings_cache["embeddings"] = {
            "file1.md": {
                "embedding": [1.0, 0.0, 0.0, 0.0, 0.0],
                "provider": "Test",
                "timestamp": datetime.now().isoformat()
            },
            "file2.md": {
                "embedding": [0.0, 1.0, 0.0, 0.0, 0.0],
                "provider": "Test", 
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Mock query embedding to be similar to file1
        self.mock_provider.get_embedding.return_value = [0.9, 0.1, 0.0, 0.0, 0.0]
        
        # Search
        results = search.semantic_search("test query", self.mock_db, top_k=2)
        
        assert len(results) == 2
        # file1 should be ranked first due to higher similarity
        assert results[0]["filename"] == "file1.md"
        assert results[1]["filename"] == "file2.md"
        assert results[0]["similarity_score"] > results[1]["similarity_score"]
        assert "file_path" in results[0]
        assert "summary" in results[0]
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_semantic_search_with_threshold(self, mock_factory):
        """Test semantic search with similarity threshold."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Pre-populate embeddings
        search.embeddings_cache["embeddings"] = {
            "file1.md": {
                "embedding": [1.0, 0.0, 0.0, 0.0, 0.0],
                "provider": "Test",
                "timestamp": datetime.now().isoformat()
            },
            "file2.md": {
                "embedding": [0.0, 1.0, 0.0, 0.0, 0.0],
                "provider": "Test",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Mock query embedding
        self.mock_provider.get_embedding.return_value = [1.0, 0.1, 0.0, 0.0, 0.0]
        
        # Search with high threshold
        results = search.semantic_search("test query", self.mock_db, top_k=5, similarity_threshold=0.8)
        
        # Only file1 should meet the threshold
        assert len(results) == 1
        assert results[0]["filename"] == "file1.md"
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_semantic_search_no_embeddings(self, mock_factory):
        """Test semantic search when no embeddings exist."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Search without any embeddings
        results = search.semantic_search("test query", self.mock_db)
        
        assert results == []
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_semantic_search_query_embedding_failure(self, mock_factory):
        """Test semantic search when query embedding fails."""
        mock_factory.return_value = self.mock_provider
        self.mock_provider.get_embedding.side_effect = Exception("API error")
        
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Pre-populate some embeddings
        search.embeddings_cache["embeddings"]["file1.md"] = {
            "embedding": [1.0, 0.0, 0.0],
            "provider": "Test",
            "timestamp": datetime.now().isoformat()
        }
        
        # Search should return empty results
        results = search.semantic_search("test query", self.mock_db)
        
        assert results == []
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_get_cache_stats(self, mock_factory):
        """Test getting cache statistics."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Add some embeddings
        search.embeddings_cache["embeddings"] = {
            "file1.md": {
                "embedding": [0.1, 0.2, 0.3],
                "provider": "Test",
                "timestamp": "2024-01-01T10:00:00"
            },
            "file2.md": {
                "embedding": [0.4, 0.5, 0.6],
                "provider": "OtherProvider",
                "timestamp": "2024-01-01T11:00:00"
            }
        }
        
        stats = search.get_cache_stats()
        
        assert stats["total_embeddings"] == 2
        assert stats["cache_file"] == str(self.cache_path)
        assert stats["providers"]["Test"] == 1
        assert stats["providers"]["OtherProvider"] == 1
        assert stats["cache_exists"] is True
        assert "cache_size_kb" in stats
        assert "metadata" in stats
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_save_embeddings_cache_error_handling(self, mock_factory):
        """Test error handling when saving cache fails."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Make cache path unwritable
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            # This should not raise an exception
            search._save_embeddings_cache()
        
        # Verify no exception was raised (method handles errors gracefully)
        assert True
    
    def test_get_available_providers(self):
        """Test getting list of available providers."""
        with patch('semantic_search_v2.APIProviderFactory.get_available_providers') as mock_get:
            mock_get.return_value = ['openai', 'gemini', 'claude']
            
            providers = SemanticSearchV2.get_available_providers()
            
            assert providers == ['openai', 'gemini', 'claude']
            mock_get.assert_called_once()
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_semantic_search_with_metadata(self, mock_factory):
        """Test semantic search returns complete metadata."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Enhanced mock database with more metadata
        self.mock_db.get_all_files_dict.return_value = {
            "file1.md": {
                "file_path": "/path/to/file1.md",
                "summary": "Test summary 1",
                "content_length": 100,
                "metadata": {
                    "last_modified": "2024-01-01T10:00:00",
                    "file_hash": "abc123"
                }
            }
        }
        
        # Pre-populate embedding
        search.embeddings_cache["embeddings"]["file1.md"] = {
            "embedding": [1.0, 0.0, 0.0, 0.0, 0.0],
            "provider": "Test",
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock query embedding
        self.mock_provider.get_embedding.return_value = [0.9, 0.1, 0.0, 0.0, 0.0]
        
        # Search
        results = search.semantic_search("test query", self.mock_db, top_k=1)
        
        assert len(results) == 1
        result = results[0]
        assert result["filename"] == "file1.md"
        assert result["content_length"] == 100
        assert "metadata" in result
    
    @patch('semantic_search_v2.APIProviderFactory.create_provider')
    def test_build_embeddings_partial_failure(self, mock_factory):
        """Test building embeddings when some files fail."""
        mock_factory.return_value = self.mock_provider
        search = SemanticSearchV2(embeddings_cache_path=str(self.cache_path))
        
        # Mock provider to fail on second call
        self.mock_provider.get_embedding.side_effect = [
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Success for file1
            Exception("API error"),       # Fail for file2
        ]
        
        # Build embeddings
        count = search.build_embeddings_for_database(self.mock_db)
        
        # Should only count successful embeddings
        assert count == 1
        assert "file1.md" in search.embeddings_cache["embeddings"]
        assert "file2.md" not in search.embeddings_cache["embeddings"]


def test_semantic_search_v2_integration():
    """Integration test for semantic search workflow."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "test_cache.json"
        
        # Mock provider
        mock_provider = Mock()
        mock_provider.__class__.__name__ = "TestProvider"
        mock_provider.get_embedding.side_effect = lambda text: [
            0.1 * len(text),  # Simple mock: embedding based on text length
            0.2,
            0.3,
            0.4,
            0.5
        ]
        
        with patch('semantic_search_v2.APIProviderFactory.create_provider') as mock_factory:
            mock_factory.return_value = mock_provider
            
            # Initialize search
            search = SemanticSearchV2(embeddings_cache_path=str(cache_path))
            
            # Mock database
            mock_db = Mock()
            mock_db.get_all_files_dict.return_value = {
                "short.md": {
                    "file_path": "/path/short.md",
                    "summary": "Short",
                    "content_length": 10
                },
                "long.md": {
                    "file_path": "/path/long.md",
                    "summary": "This is a much longer summary",
                    "content_length": 100
                }
            }
            
            # Build embeddings
            count = search.build_embeddings_for_database(mock_db)
            assert count == 2
            
            # Perform search
            results = search.semantic_search("medium length query", mock_db)
            
            assert len(results) == 2
            assert all(r["similarity_score"] > 0 for r in results)
            
            # Verify cache was persisted
            assert cache_path.exists()
            
            # Load cache in new instance
            search2 = SemanticSearchV2(embeddings_cache_path=str(cache_path))
            assert len(search2.embeddings_cache["embeddings"]) == 2


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()