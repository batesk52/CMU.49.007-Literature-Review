#!/usr/bin/env python3
"""
Test suite for the api_providers module.

This module tests the API provider implementations for OpenAI, Gemini, and Claude,
including embeddings generation, text summarization, and question answering.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import time

# Import the module we're testing
from api_providers import (
    BaseAPIProvider, OpenAIProvider, GeminiProvider, ClaudeProvider,
    APIProviderFactory
)


class TestBaseAPIProvider:
    """Test suite for BaseAPIProvider abstract class."""
    
    def test_base_initialization(self):
        """Test base provider initialization."""
        # Create a concrete implementation for testing
        class TestProvider(BaseAPIProvider):
            def get_embedding(self, text): pass
            def generate_summary(self, content, file_context=""): pass
            def answer_question(self, question, context): pass
        
        provider = TestProvider()
        assert provider.max_retries == 3
        assert provider.retry_delay == 1.0
    
    def test_handle_retry(self):
        """Test retry delay calculation."""
        class TestProvider(BaseAPIProvider):
            def get_embedding(self, text): pass
            def generate_summary(self, content, file_context=""): pass
            def answer_question(self, question, context): pass
        
        provider = TestProvider()
        
        # Test exponential backoff
        assert provider._handle_retry(0) == 1.0  # 1.0 * 2^0
        assert provider._handle_retry(1) == 2.0  # 1.0 * 2^1
        assert provider._handle_retry(2) == 4.0  # 1.0 * 2^2
        assert provider._handle_retry(3) == 8.0  # 1.0 * 2^3


class TestOpenAIProvider:
    """Test suite for OpenAIProvider class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Save original env var
        self.original_api_key = os.environ.get("OPENAI_API_KEY")
        
    def teardown_method(self):
        """Clean up after each test."""
        # Restore original env var
        if self.original_api_key:
            os.environ["OPENAI_API_KEY"] = self.original_api_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
    
    def test_initialization_success(self):
        """Test successful initialization with valid API key."""
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        
        provider = OpenAIProvider()
        
        assert provider.api_key == "test-api-key"
        assert provider.embedding_model == "text-embedding-3-small"
        assert provider.chat_model == "gpt-4"
        assert provider.base_url == "https://api.openai.com/v1"
        assert "Authorization" in provider.headers
        assert provider.headers["Authorization"] == "Bearer test-api-key"
    
    def test_initialization_no_api_key(self):
        """Test initialization fails without API key."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider()
        
        assert "Valid OPENAI_API_KEY environment variable is required" in str(exc_info.value)
    
    def test_initialization_invalid_api_key(self):
        """Test initialization fails with placeholder API key."""
        os.environ["OPENAI_API_KEY"] = "your_openai_key_here"
        
        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider()
        
        assert "Valid OPENAI_API_KEY environment variable is required" in str(exc_info.value)
    
    @patch('requests.post')
    def test_get_embedding_success(self, mock_post):
        """Test successful embedding generation."""
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        provider = OpenAIProvider()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}]
        }
        mock_post.return_value = mock_response
        
        # Get embedding
        embedding = provider.get_embedding("Test text")
        
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_post.assert_called_once()
        
        # Check request details
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/embeddings"
        assert call_args[1]["json"]["model"] == "text-embedding-3-small"
        assert call_args[1]["json"]["input"] == "Test text"
    
    @patch('requests.post')
    def test_get_embedding_rate_limit(self, mock_post):
        """Test handling of rate limit errors."""
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        provider = OpenAIProvider()
        
        # Mock rate limit response then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        
        mock_post.side_effect = [mock_response_429, mock_response_200]
        
        # Get embedding (should retry and succeed)
        with patch('time.sleep'):  # Speed up test
            embedding = provider.get_embedding("Test text")
        
        assert embedding == [0.1, 0.2, 0.3]
        assert mock_post.call_count == 2
    
    @patch('requests.post')
    def test_get_embedding_failure(self, mock_post):
        """Test embedding generation failure."""
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        provider = OpenAIProvider()
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        # Get embedding should return None after retries
        with patch('time.sleep'):  # Speed up test
            embedding = provider.get_embedding("Test text")
        
        assert embedding is None
        assert mock_post.call_count == 3  # Should retry max times
    
    @patch('requests.post')
    def test_generate_summary_success(self, mock_post):
        """Test successful summary generation."""
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        provider = OpenAIProvider()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is a test summary of the content."
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Generate summary
        summary = provider.generate_summary("Long test content", "test.md")
        
        assert summary == "This is a test summary of the content."
        mock_post.assert_called_once()
        
        # Check request structure
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
        assert call_args[1]["json"]["model"] == "gpt-4"
        assert len(call_args[1]["json"]["messages"]) > 0
    
    @patch('requests.post')
    def test_answer_question_success(self, mock_post):
        """Test successful question answering."""
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        provider = OpenAIProvider()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "The answer is 42."
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Answer question
        answer = provider.answer_question("What is the answer?", "Context about 42")
        
        assert answer == "The answer is 42."
        mock_post.assert_called_once()


class TestGeminiProvider:
    """Test suite for GeminiProvider class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.original_api_key = os.environ.get("GEMINI_API_KEY")
        
    def teardown_method(self):
        """Clean up after each test."""
        if self.original_api_key:
            os.environ["GEMINI_API_KEY"] = self.original_api_key
        elif "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
    
    def test_initialization_success(self):
        """Test successful initialization with valid API key."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        
        provider = GeminiProvider()
        
        assert provider.api_key == "test-gemini-key"
        assert provider.embedding_model == "models/text-embedding-004"
        assert provider.chat_model == "gemini-1.5-pro"
        assert "key=" in provider.base_url
    
    def test_initialization_no_api_key(self):
        """Test initialization fails without API key."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        
        with pytest.raises(ValueError) as exc_info:
            GeminiProvider()
        
        assert "Valid GEMINI_API_KEY environment variable is required" in str(exc_info.value)
    
    @patch('requests.post')
    def test_get_embedding_success(self, mock_post):
        """Test successful embedding generation."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        provider = GeminiProvider()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": [{
                "values": [0.1, 0.2, 0.3, 0.4, 0.5]
            }]
        }
        mock_post.return_value = mock_response
        
        # Get embedding
        embedding = provider.get_embedding("Test text")
        
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_generate_summary_success(self, mock_post):
        """Test successful summary generation."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        provider = GeminiProvider()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "This is a Gemini-generated summary."
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Generate summary
        summary = provider.generate_summary("Test content")
        
        assert summary == "This is a Gemini-generated summary."


class TestClaudeProvider:
    """Test suite for ClaudeProvider class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.original_api_key = os.environ.get("ANTHROPIC_API_KEY")
        
    def teardown_method(self):
        """Clean up after each test."""
        if self.original_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.original_api_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
    
    def test_initialization_success(self):
        """Test successful initialization with valid API key."""
        os.environ["ANTHROPIC_API_KEY"] = "test-claude-key"
        
        provider = ClaudeProvider()
        
        assert provider.api_key == "test-claude-key"
        assert provider.chat_model == "claude-3-sonnet-20240229"
        assert provider.base_url == "https://api.anthropic.com/v1"
        assert "x-api-key" in provider.headers
    
    def test_initialization_no_api_key(self):
        """Test initialization fails without API key."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        with pytest.raises(ValueError) as exc_info:
            ClaudeProvider()
        
        assert "Valid ANTHROPIC_API_KEY environment variable is required" in str(exc_info.value)
    
    @patch('requests.post')
    def test_get_embedding_not_supported(self, mock_post):
        """Test that Claude doesn't support embeddings."""
        os.environ["ANTHROPIC_API_KEY"] = "test-claude-key"
        provider = ClaudeProvider()
        
        # Get embedding should return None (not supported)
        embedding = provider.get_embedding("Test text")
        
        assert embedding is None
        mock_post.assert_not_called()
    
    @patch('requests.post')
    def test_generate_summary_success(self, mock_post):
        """Test successful summary generation."""
        os.environ["ANTHROPIC_API_KEY"] = "test-claude-key"
        provider = ClaudeProvider()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{
                "text": "This is a Claude-generated summary."
            }]
        }
        mock_post.return_value = mock_response
        
        # Generate summary
        summary = provider.generate_summary("Test content")
        
        assert summary == "This is a Claude-generated summary."
        
        # Check request headers
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["anthropic-version"] == "2023-06-01"


class TestAPIProviderFactory:
    """Test suite for APIProviderFactory class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Save original env vars
        self.original_keys = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY")
        }
        
    def teardown_method(self):
        """Clean up after each test."""
        # Restore original env vars
        for key, value in self.original_keys.items():
            if value:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    def test_create_provider_openai(self):
        """Test creating OpenAI provider."""
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        
        provider = APIProviderFactory.create_provider("openai")
        
        assert isinstance(provider, OpenAIProvider)
    
    def test_create_provider_gemini(self):
        """Test creating Gemini provider."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        
        provider = APIProviderFactory.create_provider("gemini")
        
        assert isinstance(provider, GeminiProvider)
    
    def test_create_provider_claude(self):
        """Test creating Claude provider."""
        os.environ["ANTHROPIC_API_KEY"] = "test-claude-key"
        
        provider = APIProviderFactory.create_provider("claude")
        
        assert isinstance(provider, ClaudeProvider)
    
    def test_create_provider_auto_detect_openai(self):
        """Test auto-detecting OpenAI provider."""
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        provider = APIProviderFactory.create_provider()
        
        assert isinstance(provider, OpenAIProvider)
    
    def test_create_provider_auto_detect_gemini(self):
        """Test auto-detecting Gemini provider."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        provider = APIProviderFactory.create_provider()
        
        assert isinstance(provider, GeminiProvider)
    
    def test_create_provider_unknown(self):
        """Test error for unknown provider."""
        with pytest.raises(ValueError) as exc_info:
            APIProviderFactory.create_provider("unknown_provider")
        
        assert "Unknown provider: unknown_provider" in str(exc_info.value)
    
    def test_create_provider_no_api_keys(self):
        """Test error when no API keys are available."""
        # Remove all API keys
        for key in ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
            if key in os.environ:
                del os.environ[key]
        
        with pytest.raises(ValueError) as exc_info:
            APIProviderFactory.create_provider()
        
        assert "No API keys found" in str(exc_info.value)
    
    def test_get_available_providers_all(self):
        """Test getting available providers when all keys exist."""
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-claude-key"
        
        providers = APIProviderFactory.get_available_providers()
        
        assert "openai" in providers
        assert "gemini" in providers
        assert "claude" in providers
        assert len(providers) == 3
    
    def test_get_available_providers_partial(self):
        """Test getting available providers with partial keys."""
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        providers = APIProviderFactory.get_available_providers()
        
        assert providers == ["openai"]
    
    def test_get_available_providers_none(self):
        """Test getting available providers with no keys."""
        for key in ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
            if key in os.environ:
                del os.environ[key]
        
        providers = APIProviderFactory.get_available_providers()
        
        assert providers == []


def test_api_providers_integration():
    """Integration test for API providers."""
    # This test requires actual API keys to run
    # It's marked to be skipped in CI but can be run locally
    
    import pytest
    
    # Skip if no API keys are available
    if not any(os.environ.get(key) for key in ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]):
        pytest.skip("No API keys available for integration test")
    
    # Get available providers
    available = APIProviderFactory.get_available_providers()
    assert len(available) > 0
    
    # Test with first available provider
    provider_name = available[0]
    provider = APIProviderFactory.create_provider(provider_name)
    
    # Test that provider implements required methods
    assert hasattr(provider, 'get_embedding')
    assert hasattr(provider, 'generate_summary')
    assert hasattr(provider, 'answer_question')


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()