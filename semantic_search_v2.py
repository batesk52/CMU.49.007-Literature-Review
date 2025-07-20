"""
Semantic Search V2 Module

This version supports multiple API providers (OpenAI, Gemini, Claude)
for embeddings and semantic search functionality.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import time

# Import API providers
from api_providers import APIProviderFactory

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticSearchV2:
    """
    Implements semantic search using configurable API providers for embeddings.
    """
    
    def __init__(self, embeddings_cache_path: str = "data/embeddings_cache.json",
                 provider_name: str = None):
        """
        Initialize the semantic search system.
        
        Args:
            embeddings_cache_path (str): Path to cache embeddings to avoid re-computation
            provider_name (str, optional): API provider to use ('openai', 'gemini', 'claude')
                                         If None, auto-detects based on available API keys
        """
        try:
            self.provider = APIProviderFactory.create_provider(provider_name)
            self.provider_name = provider_name or self.provider.__class__.__name__.replace('Provider', '')
            logger.info(f"Initialized semantic search with {self.provider_name} provider")
        except ValueError as e:
            logger.error(f"Failed to initialize API provider: {e}")
            raise
        
        self.embeddings_cache_path = Path(embeddings_cache_path)
        self.embeddings_cache = self._load_embeddings_cache()
        
        logger.info(f"Initialized semantic search with {self.provider_name}")
    
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
                "providers": {},
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
            
            # Track which providers have been used
            if "providers" not in self.embeddings_cache["metadata"]:
                self.embeddings_cache["metadata"]["providers"] = {}
            if self.provider_name not in self.embeddings_cache["metadata"]["providers"]:
                self.embeddings_cache["metadata"]["providers"][self.provider_name] = {
                    "first_used": datetime.now().isoformat(),
                    "embedding_count": 0
                }
            
            # Save to file
            with open(self.embeddings_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_cache, f, indent=2)
                
            logger.debug(f"Saved embeddings cache to {self.embeddings_cache_path}")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")
    
    def _create_cache_key(self, text: str, file_path: str = "") -> str:
        """
        Create a cache key for text embeddings, including provider info.
        
        Args:
            text (str): The text to embed
            file_path (str): Optional file path for context
            
        Returns:
            str: Cache key
        """
        import hashlib
        content = f"{text}|{file_path}|{self.provider_name}"
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
        
        # Get embedding from provider
        embedding = self.provider.get_embedding(text)
        
        if embedding:
            # Cache the embedding
            self.embeddings_cache["embeddings"][cache_key] = embedding
            
            # Update provider stats
            if "providers" not in self.embeddings_cache["metadata"]:
                self.embeddings_cache["metadata"]["providers"] = {}
            if self.provider_name not in self.embeddings_cache["metadata"]["providers"]:
                self.embeddings_cache["metadata"]["providers"][self.provider_name] = {
                    "first_used": self.embeddings_cache["metadata"].get("last_updated", ""),
                    "embedding_count": 0
                }
            self.embeddings_cache["metadata"]["providers"][self.provider_name]["embedding_count"] += 1
            
            self._save_embeddings_cache()
        
        return embedding
    
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
            
            # Handle different vector sizes (pad shorter one with zeros)
            if len(a) != len(b):
                max_len = max(len(a), len(b))
                if len(a) < max_len:
                    a = np.pad(a, (0, max_len - len(a)), 'constant')
                else:
                    b = np.pad(b, (0, max_len - len(b)), 'constant')
            
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
        logger.info(f"Building embeddings for knowledge database using {self.provider_name}...")
        
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
        logger.info(f"Performing semantic search for: '{query}' using {self.provider_name}")
        
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
                    "added_time": file_entry.get("added_to_db", ""),
                    "provider": self.provider_name
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
        providers = self.embeddings_cache.get("metadata", {}).get("providers", {})
        
        # Count embeddings by provider
        provider_counts = {}
        for provider_name in providers:
            provider_counts[provider_name] = providers[provider_name].get("embedding_count", 0)
        
        return {
            "total_embeddings": len(embeddings),
            "cache_file_exists": self.embeddings_cache_path.exists(),
            "cache_file_size": self.embeddings_cache_path.stat().st_size if self.embeddings_cache_path.exists() else 0,
            "current_provider": self.provider_name,
            "providers_used": list(providers.keys()),
            "embeddings_by_provider": provider_counts,
            "created": self.embeddings_cache.get("metadata", {}).get("created"),
            "last_updated": self.embeddings_cache.get("metadata", {}).get("last_updated")
        }
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of available API providers."""
        return APIProviderFactory.get_available_providers()


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
    parser.add_argument("--provider", choices=['openai', 'gemini', 'claude'],
                       help="API provider to use (auto-detect if not specified)")
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
    
    # Show available providers
    available = SemanticSearchV2.get_available_providers()
    print(f"Available API providers: {', '.join(available)}")
    
    try:
        # Initialize components
        semantic_search = SemanticSearchV2(args.embeddings_cache, args.provider)
        knowledge_db = KnowledgeDatabase(args.db_path)
        
        if args.command == "build":
            created = semantic_search.build_embeddings_for_database(knowledge_db, args.force)
            print(f"Created {created} new embeddings using {semantic_search.provider_name}")
            
        elif args.command == "search":
            results = semantic_search.semantic_search(
                args.query, knowledge_db, args.top_k, args.threshold
            )
            
            print(f"\n🔍 Semantic search results for: '{args.query}'")
            print(f"Provider: {semantic_search.provider_name}")
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
            
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet one of these environment variables:")
        print("  - OPENAI_API_KEY for OpenAI")
        print("  - GEMINI_API_KEY for Google Gemini")
        print("  - CLAUDE_API_KEY or ANTHROPIC_API_KEY for Claude")


if __name__ == "__main__":
    main()