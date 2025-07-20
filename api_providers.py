"""
API Providers Module

This module provides a unified interface for different LLM APIs (OpenAI, Gemini, Claude)
to support both text generation and embeddings functionality.
"""

import os
import json
import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import logging
import numpy as np

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class BaseAPIProvider(ABC):
    """Abstract base class for API providers."""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 1.0
    
    @abstractmethod
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        pass
    
    @abstractmethod
    def generate_summary(self, content: str, file_context: str = "") -> Optional[str]:
        """Generate a summary of the content."""
        pass
    
    @abstractmethod
    def answer_question(self, question: str, context: str) -> Optional[str]:
        """Answer a question based on provided context."""
        pass
    
    def _handle_retry(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff."""
        return self.retry_delay * (2 ** attempt)


class OpenAIProvider(BaseAPIProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key.startswith("your_"):
            raise ValueError("Valid OPENAI_API_KEY environment variable is required")
        
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4"
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding using OpenAI API."""
        data = {
            "model": self.embedding_model,
            "input": text.strip()
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["data"][0]["embedding"]
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def generate_summary(self, content: str, file_context: str = "") -> Optional[str]:
        """Generate summary using OpenAI API."""
        messages = [
            {
                "role": "system",
                "content": """You are an expert at creating concise, informative summaries of markdown documents. 
                Your summaries should be abstract-like, capturing the main topics, key points, and purpose of the document.
                Focus on what someone would need to know to determine if this document is relevant to their query.
                Keep summaries between 2-4 sentences and include the document's primary focus and any important technical details."""
            },
            {
                "role": "user",
                "content": f"Please create a concise summary of this markdown document{file_context}:\n\n{content}"
            }
        ]
        
        data = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.3
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"OpenAI summary error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def answer_question(self, question: str, context: str) -> Optional[str]:
        """Answer question using OpenAI API."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions based on the provided context. Be accurate and cite relevant information from the context."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
        
        data = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"OpenAI answer error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None


class GeminiProvider(BaseAPIProvider):
    """Google Gemini API provider implementation."""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.embedding_model = "models/embedding-001"
        self.chat_model = "gemini-1.5-flash"  # Updated model name
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.max_retries = 5  # Increased retries for rate limiting
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding using Gemini API."""
        url = f"{self.base_url}/{self.embedding_model}:embedContent?key={self.api_key}"
        data = {
            "model": self.embedding_model,
            "content": {
                "parts": [{"text": text.strip()}]
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    return result["embedding"]["values"]
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Gemini embedding error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def generate_summary(self, content: str, file_context: str = "") -> Optional[str]:
        """Generate summary using Gemini API."""
        url = f"{self.base_url}/models/{self.chat_model}:generateContent?key={self.api_key}"
        
        # Drastically reduce content to minimize API load
        truncated_content = content[:400] if len(content) > 400 else content
        
        prompt = f"""One sentence summary{file_context}: {truncated_content}"""
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.0,  # Zero temperature for deterministic output
                "maxOutputTokens": 30  # Even lower token limit
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=data, timeout=60)  # Increased timeout
                
                if response.status_code == 200:
                    result = response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"].strip()
                elif response.status_code in [429, 503]:  # Rate limiting or service unavailable
                    wait_time = self._handle_retry(attempt)
                    logger.warning(f"Rate limited (status {response.status_code}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Check if error message indicates rate limiting
                    error_text = response.text
                    if "quota" in error_text.lower() or "limit" in error_text.lower():
                        wait_time = self._handle_retry(attempt) * 2  # Double wait for quota issues
                        logger.warning(f"Quota/limit error, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Gemini API error {response.status_code}: {error_text}")
                        break  # Don't retry on non-recoverable errors
                    
            except Exception as e:
                logger.error(f"Gemini summary error: {e}")
                
            if attempt < self.max_retries - 1:
                wait_time = min(self.retry_delay * (2 ** attempt), 10)  # Exponential backoff, max 10s
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        return None
    
    def answer_question(self, question: str, context: str) -> Optional[str]:
        """Answer question using Gemini API."""
        url = f"{self.base_url}/models/{self.chat_model}:generateContent?key={self.api_key}"
        
        prompt = f"""You are a helpful assistant that answers questions based on the provided context. 
        Be accurate and cite relevant information from the context.
        
        Context:
        {context}
        
        Question: {question}"""
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 500
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"].strip()
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Gemini answer error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None


class ClaudeProvider(BaseAPIProvider):
    """Anthropic Claude API provider implementation."""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable is required")
        
        self.chat_model = "claude-3-sonnet-20240229"
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Claude doesn't provide embeddings API directly.
        This implementation uses a workaround by generating semantic descriptions
        and using a simple hashing approach. For production, consider using
        a dedicated embedding model or service.
        """
        # Generate a semantic fingerprint using Claude
        messages = [
            {
                "role": "user",
                "content": f"""Generate 10 key semantic concepts from this text as single words or short phrases, 
                ordered by importance. Format: concept1, concept2, ..., concept10
                
                Text: {text[:1000]}"""
            }
        ]
        
        data = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.1
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    concepts = result["content"][0]["text"].strip()
                    
                    # Create a simple embedding from concepts (not ideal for production)
                    # This is a placeholder - for real semantic search, use dedicated embedding models
                    embedding = self._concepts_to_embedding(concepts)
                    return embedding
                    
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"Claude API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Claude embedding error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def _concepts_to_embedding(self, concepts: str) -> List[float]:
        """Convert concepts to a simple embedding vector (placeholder implementation)."""
        # This is a simplified approach - in production, use proper embedding models
        import hashlib
        
        # Create a deterministic embedding from concepts
        concepts_lower = concepts.lower()
        hash_obj = hashlib.sha256(concepts_lower.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to normalized float vector
        embedding = []
        for i in range(0, len(hash_bytes), 2):
            if i + 1 < len(hash_bytes):
                value = (hash_bytes[i] + hash_bytes[i+1]) / 510.0  # Normalize to [0, 1]
                embedding.append(value * 2 - 1)  # Scale to [-1, 1]
        
        # Pad or truncate to standard size (384 dimensions)
        target_size = 384
        if len(embedding) < target_size:
            embedding.extend([0.0] * (target_size - len(embedding)))
        else:
            embedding = embedding[:target_size]
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def generate_summary(self, content: str, file_context: str = "") -> Optional[str]:
        """Generate summary using Claude API."""
        messages = [
            {
                "role": "user",
                "content": f"""You are an expert at creating concise, informative summaries of markdown documents. 
                Your summaries should be abstract-like, capturing the main topics, key points, and purpose of the document.
                Focus on what someone would need to know to determine if this document is relevant to their query.
                Keep summaries between 2-4 sentences and include the document's primary focus and any important technical details.
                
                Please create a concise summary of this markdown document{file_context}:
                
                {content[:15000]}"""  # Claude has larger context window
            }
        ]
        
        data = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.3
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["content"][0]["text"].strip()
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"Claude API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Claude summary error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def answer_question(self, question: str, context: str) -> Optional[str]:
        """Answer question using Claude API."""
        messages = [
            {
                "role": "user",
                "content": f"""You are a helpful assistant that answers questions based on the provided context. 
                Be accurate and cite relevant information from the context.
                
                Context:
                {context}
                
                Question: {question}"""
            }
        ]
        
        data = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["content"][0]["text"].strip()
                elif response.status_code == 429:
                    time.sleep(self._handle_retry(attempt))
                else:
                    logger.error(f"Claude API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Claude answer error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None


class APIProviderFactory:
    """Factory for creating API provider instances."""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> BaseAPIProvider:
        """
        Create an API provider instance.
        
        Args:
            provider_name: Name of the provider ('openai', 'gemini', 'claude')
                          If None, will auto-detect based on available API keys
        
        Returns:
            BaseAPIProvider instance
        """
        if provider_name:
            provider_name = provider_name.lower()
            
        # Auto-detect based on available API keys
        if not provider_name:
            # Check for valid API keys (not placeholders)
            openai_key = os.getenv("OPENAI_API_KEY", "")
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            claude_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
            
            # Skip placeholder keys
            if openai_key and not openai_key.startswith("your_"):
                provider_name = "openai"
            elif gemini_key and not gemini_key.startswith("your_"):
                provider_name = "gemini"
            elif claude_key and not claude_key.startswith("your_"):
                provider_name = "claude"
            else:
                raise ValueError("No valid API keys found. Set OPENAI_API_KEY, GEMINI_API_KEY, or CLAUDE_API_KEY")
        
        # Create provider
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        elif provider_name == "claude":
            return ClaudeProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of providers with configured API keys."""
        providers = []
        if os.getenv("OPENAI_API_KEY"):
            providers.append("openai")
        if os.getenv("GEMINI_API_KEY"):
            providers.append("gemini")
        if os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
            providers.append("claude")
        return providers