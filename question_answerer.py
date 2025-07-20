"""
Question Answering System

This module implements a question-answering system that uses semantic search
to find relevant markdown files and synthesizes comprehensive answers from
their content using OpenAI's GPT models.
"""

import os
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from config import get_config

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import our custom modules
from knowledge_database import KnowledgeDatabase
from semantic_search_v2 import SemanticSearchV2 as SemanticSearch
from markdown_summarizer import MarkdownSummarizer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionAnswerer:
    """
    Implements question-answering functionality using semantic search and GPT synthesis.
    """
    
    def __init__(self, 
                 db_path: Optional[str] = None,
                 embeddings_cache_path: Optional[str] = None):
        """
        Initialize the question answering system.
        
        Args:
            db_path (str): Path to the knowledge database
            embeddings_cache_path (str): Path to the embeddings cache
        """
        config = get_config()
        self.openai_api_key = config.api.openai_api_key
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Use provided paths or get from config
        db_path = db_path or str(config.paths.knowledge_base_path)
        embeddings_cache_path = embeddings_cache_path or str(config.paths.embeddings_cache_path)
        
        # Initialize components
        self.knowledge_db = KnowledgeDatabase(db_path)
        self.semantic_search = SemanticSearch(embeddings_cache_path)
        self.summarizer = MarkdownSummarizer()
        
        # API configuration
        self.max_context_length = 12000  # Conservative limit for context
        self.max_retries = config.processing.max_retries
        self.retry_delay = config.processing.retry_delay
        self.model = config.api.openai_model
    
    def find_relevant_files(self, query: str, top_k: int = 5, 
                           similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find files relevant to the query using semantic search.
        
        Args:
            query (str): The user's question
            top_k (int): Maximum number of files to return
            similarity_threshold (float): Minimum similarity score
            
        Returns:
            List[Dict[str, Any]]: List of relevant files with similarity scores
        """
        logger.info(f"Finding files relevant to: '{query}'")
        
        # Use semantic search to find relevant files
        relevant_files = self.semantic_search.semantic_search(
            query, 
            self.knowledge_db, 
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
        
        logger.info(f"Found {len(relevant_files)} relevant files")
        return relevant_files
    
    def read_file_content(self, file_path: str) -> str:
        """
        Read the full content of a markdown file.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: File content or empty string if reading fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return ""
    
    def prepare_context(self, relevant_files: List[Dict[str, Any]], query: str) -> str:
        """
        Prepare context from relevant files for the GPT model.
        
        Args:
            relevant_files (List[Dict[str, Any]]): Files found by semantic search
            query (str): The original query for context
            
        Returns:
            str: Formatted context string
        """
        context_parts = []
        total_length = 0
        
        for i, file_info in enumerate(relevant_files):
            if total_length >= self.max_context_length:
                break
                
            file_path = file_info['file_path']
            similarity_score = file_info.get('similarity_score', 0.0)
            
            # Read the full file content
            content = self.read_file_content(file_path)
            if not content:
                continue
            
            # Format the file information
            file_name = Path(file_path).name
            file_section = f"""
=== File: {file_name} (Relevance: {similarity_score:.2f}) ===
{content}
"""
            
            # Check if adding this file would exceed our limit
            if total_length + len(file_section) > self.max_context_length:
                # Try to include a truncated version
                remaining_space = self.max_context_length - total_length - 200  # Leave space for header
                if remaining_space > 500:  # Only include if we have reasonable space
                    truncated_content = content[:remaining_space] + "\n\n[Content truncated...]"
                    file_section = f"""
=== File: {file_name} (Relevance: {similarity_score:.2f}) ===
{truncated_content}
"""
                    context_parts.append(file_section)
                break
            
            context_parts.append(file_section)
            total_length += len(file_section)
        
        context = "\n".join(context_parts)
        logger.info(f"Prepared context from {len(context_parts)} files ({len(context)} characters)")
        return context
    
    def synthesize_answer(self, query: str, context: str) -> str:
        """
        Use GPT to synthesize an answer from the context.
        
        Args:
            query (str): The user's question
            context (str): Context from relevant files
            
        Returns:
            str: Synthesized answer
        """
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are an intelligent knowledge base assistant. Your task is to answer questions using information from markdown files provided as context.

Instructions:
1. Answer the question using ONLY information found in the provided context
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Cite specific files when referencing information (use the format [filename])
4. Provide comprehensive answers when possible, but be concise
5. If multiple files contain relevant information, synthesize it coherently
6. If there are contradictions between files, mention them
7. Use a natural, helpful tone

Context contains files with their relevance scores. Higher scores indicate more relevant content."""

        user_prompt = f"""Question: {query}

Context from relevant files:
{context}

Please provide a comprehensive answer to the question based on the information in the context."""

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.3
        }
        
        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making GPT API call (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=get_config().processing.request_timeout * 2  # Longer timeout for Q&A
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result["choices"][0]["message"]["content"].strip()
                    logger.info("Successfully synthesized answer")
                    return answer
                    
                elif response.status_code == 429:  # Rate limited
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    if attempt == self.max_retries - 1:
                        return f"Error: Failed to generate answer due to API error ({response.status_code})"
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return "Error: Request timed out while generating answer"
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return f"Error: Failed to generate answer due to connection error"
            
            # Wait before retrying
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return "Error: Failed to generate answer after multiple attempts"
    
    def answer_question(self, query: str, top_k: int = 5, 
                       similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Answer a question using the knowledge base.
        
        Args:
            query (str): The user's question
            top_k (int): Maximum number of files to consider
            similarity_threshold (float): Minimum similarity score for relevance
            
        Returns:
            Dict[str, Any]: Dictionary containing answer and metadata
        """
        logger.info(f"Answering question: '{query}'")
        
        try:
            # Find relevant files
            relevant_files = self.find_relevant_files(query, top_k, similarity_threshold)
            
            if not relevant_files:
                return {
                    "question": query,
                    "answer": "I couldn't find any relevant information in the knowledge base to answer your question. You may want to try rephrasing your question or checking if the relevant documents are in the knowledge base.",
                    "relevant_files": [],
                    "files_used": 0,
                    "confidence": "low"
                }
            
            # Prepare context from relevant files
            context = self.prepare_context(relevant_files, query)
            
            # Synthesize answer
            answer = self.synthesize_answer(query, context)
            
            # Determine confidence based on relevance scores
            avg_relevance = sum(f.get('similarity_score', 0) for f in relevant_files) / len(relevant_files)
            confidence = "high" if avg_relevance > 0.8 else "medium" if avg_relevance > 0.6 else "low"
            
            return {
                "question": query,
                "answer": answer,
                "relevant_files": [
                    {
                        "file_path": f['file_path'],
                        "filename": Path(f['file_path']).name,
                        "similarity_score": f.get('similarity_score', 0.0)
                    }
                    for f in relevant_files
                ],
                "files_used": len(relevant_files),
                "confidence": confidence,
                "average_relevance": avg_relevance
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "question": query,
                "answer": f"Error: An unexpected error occurred while processing your question: {str(e)}",
                "relevant_files": [],
                "files_used": 0,
                "confidence": "error"
            }
    
    def interactive_qa(self):
        """
        Start an interactive question-answering session.
        """
        print("🧠 Knowledge Base Q&A System")
        print("="*50)
        print("Ask questions about your markdown files. Type 'quit' to exit.")
        print()
        
        while True:
            try:
                question = input("❓ Your question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not question:
                    continue
                
                print("\n🔍 Searching knowledge base...")
                result = self.answer_question(question)
                
                print(f"\n💡 Answer:")
                print(result['answer'])
                
                if result['relevant_files']:
                    print(f"\n📁 Sources used ({result['files_used']} files):")
                    for file_info in result['relevant_files']:
                        print(f"  • {file_info['filename']} (relevance: {file_info['similarity_score']:.2f})")
                
                print(f"\n🎯 Confidence: {result['confidence']}")
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("-" * 50)


def main():
    """
    Command-line interface for the question answering system.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Question-Answering system for markdown knowledge base")
    parser.add_argument("--db-path", default="data/knowledge_base.json",
                       help="Path to the knowledge database")
    parser.add_argument("--embeddings-cache", default="data/embeddings_cache.json",
                       help="Path to the embeddings cache")
    parser.add_argument("-q", "--question", help="Ask a single question and exit")
    parser.add_argument("-k", "--top-k", type=int, default=5,
                       help="Number of top files to consider")
    parser.add_argument("-t", "--threshold", type=float, default=0.7,
                       help="Similarity threshold for relevance")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize question answerer
        qa = QuestionAnswerer(args.db_path, args.embeddings_cache)
        
        if args.question:
            # Single question mode
            print(f"Question: {args.question}")
            print()
            result = qa.answer_question(args.question, args.top_k, args.threshold)
            
            print("Answer:")
            print(result['answer'])
            
            if result['relevant_files']:
                print(f"\nSources ({result['files_used']} files):")
                for file_info in result['relevant_files']:
                    print(f"  • {file_info['filename']} (relevance: {file_info['similarity_score']:.2f})")
            
            print(f"\nConfidence: {result['confidence']}")
        else:
            # Interactive mode
            qa.interactive_qa()
    
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())