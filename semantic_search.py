"""
Semantic Search Module

This module provides semantic search functionality using OpenAI embeddings
to find relevant markdown files based on meaning rather than just keyword matching.
"""

import os
import json
import requests
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import time
from config import get_config

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Implements semantic search using OpenAI embeddings for finding relevant files.
    """
    
    def __init__(self, embeddings_cache_path: Optional[str] = None):
        """
        Initialize the semantic search system.
        
        Args:
            embeddings_cache_path (str): Path to cache embeddings to avoid re-computation
        """
        config = get_config()
        self.openai_api_key = config.api.openai_api_key
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # OpenAI API configuration
        self.embedding_model = config.api.openai_embedding_model
        self.embedding_dimension = 1536  # Dimension for text-embedding-3-small
        self.max_retries = config.processing.max_retries
        self.retry_delay = config.processing.retry_delay
        
        # Use provided path or get from config
        if embeddings_cache_path:
            self.embeddings_cache_path = Path(embeddings_cache_path)
        else:
            self.embeddings_cache_path = config.paths.embeddings_cache_path
        
        self.embeddings_cache = self._load_embeddings_cache()
        
        logger.info(f"Initialized semantic search with model: {self.embedding_model}")
    
    def _load_embeddings_cache(self) -> Dict[str, Any]:
        """
        Load cached embeddings from disk.
        
        Returns:
            Dict[str, Any]: Cached embeddings data
        """
        if self.embeddings_cache_path.exists():
            try:
                with open(self.embeddings_cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    logger.info(f"Loaded {len(cache.get('embeddings', {}))} cached embeddings")
                    return cache
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load embeddings cache: {e}")
        
        return {
            "metadata": {
                "model": self.embedding_model,
                "created": None,
                "last_updated": None
            },
            "embeddings": {}
        }
    
    def _save_embeddings_cache(self) -> None:
        """
        Save embeddings cache to disk.
        """
        try:
            # Ensure directory exists
            self.embeddings_cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update metadata
            from datetime import datetime
            if not self.embeddings_cache["metadata"]["created"]:
                self.embeddings_cache["metadata"]["created"] = datetime.now().isoformat()
            self.embeddings_cache["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Save to file
            with open(self.embeddings_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_cache, f, indent=2)
                
            logger.debug(f"Saved embeddings cache to {self.embeddings_cache_path}")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")
    
    def _create_cache_key(self, text: str, file_path: str = "") -> str:
        """
        Create a cache key for text embeddings.
        
        Args:
            text (str): The text to embed
            file_path (str): Optional file path for context
            
        Returns:
            str: Cache key
        """
        import hashlib
        content = f"{text}|{file_path}|{self.embedding_model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_embedding(self, text: str, file_path: str = "") -> Optional[List[float]]:
        """
        Get embedding for text, using cache if available.
        
        Args:
            text (str): Text to embed
            file_path (str): Optional file path for context
            
        Returns:
            Optional[List[float]]: Embedding vector or None if failed
        """
        # Check cache first
        cache_key = self._create_cache_key(text, file_path)
        if cache_key in self.embeddings_cache["embeddings"]:
            logger.debug(f"Using cached embedding for {file_path or 'text'}")
            return self.embeddings_cache["embeddings"][cache_key]
        
        # Get embedding from OpenAI API
        embedding = self._request_embedding(text)
        
        if embedding:
            # Cache the embedding
            self.embeddings_cache["embeddings"][cache_key] = embedding
            self._save_embeddings_cache()
        
        return embedding
    
    def _request_embedding(self, text: str) -> Optional[List[float]]:
        """
        Request embedding from OpenAI API.
        
        Args:
            text (str): Text to embed
            
        Returns:
            Optional[List[float]]: Embedding vector or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.embedding_model,
            "input": text.strip()
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Requesting embedding (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    "https://api.openai.com/v1/embeddings",
                    headers=headers,
                    json=data,
                    timeout=get_config().processing.request_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result["data"][0]["embedding"]
                    logger.debug("Successfully obtained embedding")
                    return embedding
                    
                elif response.status_code == 429:  # Rate limited
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    if attempt == self.max_retries - 1:
                        break
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
            
            # Wait before retrying
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        logger.error("Failed to get embedding after all retries")
        return None
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1 (List[float]): First vector
            vec2 (List[float]): Second vector
            
        Returns:
            float: Cosine similarity score (0 to 1)
        """
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def build_embeddings_for_database(self, knowledge_db, force_rebuild: bool = False) -> int:
        """
        Build embeddings for all files in the knowledge database.
        
        Args:
            knowledge_db: KnowledgeDatabase instance
            force_rebuild (bool): Whether to rebuild all embeddings
            
        Returns:
            int: Number of embeddings created
        """
        logger.info("Building embeddings for knowledge database...")
        
        all_files = knowledge_db.get_all_files()
        embeddings_created = 0
        
        for i, file_entry in enumerate(all_files, 1):
            file_path = file_entry.get("file_path", "")
            summary = file_entry.get("summary", "")
            
            if not summary:
                logger.warning(f"No summary found for {file_path}, skipping")
                continue
            
            logger.info(f"Processing embeddings {i}/{len(all_files)}: {Path(file_path).name}")
            
            # Check if we need to create embedding
            cache_key = self._create_cache_key(summary, file_path)
            
            if not force_rebuild and cache_key in self.embeddings_cache["embeddings"]:
                logger.debug(f"Embedding already exists for {Path(file_path).name}")
                continue
            
            # Create embedding
            embedding = self.get_embedding(summary, file_path)
            
            if embedding:
                embeddings_created += 1
                logger.info(f"Created embedding for {Path(file_path).name}")
            else:
                logger.error(f"Failed to create embedding for {Path(file_path).name}")
            
            # Add delay between API calls
            if i < len(all_files):
                time.sleep(0.5)
        
        logger.info(f"Created {embeddings_created} new embeddings")
        return embeddings_created
    
    def semantic_search(self, query: str, knowledge_db, top_k: int = 5, 
                       similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform semantic search to find relevant files.
        
        Args:
            query (str): Search query
            knowledge_db: KnowledgeDatabase instance
            top_k (int): Number of top results to return
            similarity_threshold (float): Minimum similarity score (0-1)
            
        Returns:
            List[Dict[str, Any]]: List of relevant files with similarity scores
        """
        logger.info(f"Performing semantic search for: '{query}'")
        
        # Get embedding for the query
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            logger.error("Failed to get embedding for query")
            return []
        
        # Get all files from database
        all_files = knowledge_db.get_all_files()
        results = []
        
        for file_entry in all_files:
            file_path = file_entry.get("file_path", "")
            summary = file_entry.get("summary", "")
            
            if not summary:
                continue
            
            # Get embedding for file summary
            cache_key = self._create_cache_key(summary, file_path)
            file_embedding = self.embeddings_cache["embeddings"].get(cache_key)
            
            if not file_embedding:
                logger.warning(f"No embedding found for {Path(file_path).name}, skipping")
                continue
            
            # Calculate similarity
            similarity = self.cosine_similarity(query_embedding, file_embedding)
            
            if similarity >= similarity_threshold:
                result = {
                    "file_path": file_path,
                    "filename": file_entry.get("filename", Path(file_path).name),
                    "summary": summary,
                    "content_length": file_entry.get("content_length", 0),
                    "similarity_score": similarity,
                    "added_time": file_entry.get("added_to_db", "")
                }
                results.append(result)
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Return top k results
        top_results = results[:top_k]
        
        logger.info(f"Found {len(top_results)} relevant files (threshold: {similarity_threshold})")
        for result in top_results:
            logger.debug(f"  {result['filename']}: {result['similarity_score']:.3f}")
        
        return top_results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the embeddings cache.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        embeddings = self.embeddings_cache.get("embeddings", {})
        
        return {
            "total_embeddings": len(embeddings),
            "cache_file_exists": self.embeddings_cache_path.exists(),
            "cache_file_size": self.embeddings_cache_path.stat().st_size if self.embeddings_cache_path.exists() else 0,
            "model_used": self.embeddings_cache.get("metadata", {}).get("model", "unknown"),
            "created": self.embeddings_cache.get("metadata", {}).get("created"),
            "last_updated": self.embeddings_cache.get("metadata", {}).get("last_updated")
        }


def main():
    """
    Command-line interface for semantic search functionality.
    """
    import argparse
    from knowledge_database import KnowledgeDatabase
    
    parser = argparse.ArgumentParser(description="Semantic search for knowledge base")
    parser.add_argument("--db-path", default="data/knowledge_base.json",
                       help="Path to the knowledge database")
    parser.add_argument("--embeddings-cache", default="data/embeddings_cache.json",
                       help="Path to embeddings cache file")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Build embeddings command
    build_parser = subparsers.add_parser("build", help="Build embeddings for all files")
    build_parser.add_argument("--force", action="store_true",
                             help="Force rebuild all embeddings")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Perform semantic search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--top-k", type=int, default=5,
                              help="Number of results to return")
    search_parser.add_argument("--threshold", type=float, default=0.7,
                              help="Similarity threshold (0-1)")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize components
        semantic_search = SemanticSearch(args.embeddings_cache)
        knowledge_db = KnowledgeDatabase(args.db_path)
        
        if args.command == "build":
            created = semantic_search.build_embeddings_for_database(knowledge_db, args.force)
            print(f"Created {created} new embeddings")
            
        elif args.command == "search":
            results = semantic_search.semantic_search(
                args.query, knowledge_db, args.top_k, args.threshold
            )
            
            print(f"\n🔍 Semantic search results for: '{args.query}'")
            print(f"Found {len(results)} relevant files:\n")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. 📄 {result['filename']} (similarity: {result['similarity_score']:.3f})")
                print(f"   Path: {result['file_path']}")
                print(f"   Summary: {result['summary'][:150]}...")
                print()
                
        elif args.command == "stats":
            stats = semantic_search.get_cache_stats()
            print("📊 Embeddings Cache Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
                
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()