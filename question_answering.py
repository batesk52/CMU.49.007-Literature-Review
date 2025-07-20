"""
Question Answering Module

This module provides natural language question-answering functionality by finding
relevant markdown files and synthesizing comprehensive answers from their content.
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import our modules
from semantic_search_v2 import SemanticSearchV2 as SemanticSearch
from knowledge_database import KnowledgeDatabase
from markdown_scanner import MarkdownScanner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionAnswering:
    """
    Implements question-answering system that synthesizes responses from relevant files.
    """
    
    def __init__(self, 
                 knowledge_db_path: str = "data/knowledge_base.json",
                 embeddings_cache_path: str = "data/embeddings_cache.json",
                 max_context_length: int = 8000):
        """
        Initialize the question-answering system.
        
        Args:
            knowledge_db_path (str): Path to the knowledge database
            embeddings_cache_path (str): Path to embeddings cache
            max_context_length (int): Maximum total context length for synthesis
        """
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize components
        self.knowledge_db = KnowledgeDatabase(knowledge_db_path)
        self.semantic_search = SemanticSearch(embeddings_cache_path)
        
        # Configuration
        self.max_context_length = max_context_length
        self.max_retries = 3
        self.retry_delay = 1.0
        
        logger.info("Initialized question-answering system")
    
    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        Read the content of a markdown file.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            Optional[str]: File content or None if error
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def find_relevant_files(self, question: str, top_k: int = 5, 
                          similarity_threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        Find files relevant to the question using semantic search.
        
        Args:
            question (str): The user's question
            top_k (int): Number of top results to consider
            similarity_threshold (float): Minimum similarity score
            
        Returns:
            List[Dict[str, Any]]: List of relevant files with metadata
        """
        logger.info(f"Finding relevant files for question: '{question}'")
        
        # Perform semantic search
        relevant_files = self.semantic_search.semantic_search(
            question, self.knowledge_db, top_k, similarity_threshold
        )
        
        logger.info(f"Found {len(relevant_files)} relevant files")
        return relevant_files
    
    def prepare_context(self, relevant_files: List[Dict[str, Any]], 
                       max_length: Optional[int] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Prepare context from relevant files for the QA synthesis.
        
        Args:
            relevant_files (List[Dict[str, Any]]): List of relevant files
            max_length (Optional[int]): Maximum context length
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: Combined context and file info
        """
        if max_length is None:
            max_length = self.max_context_length
        
        context_parts = []
        included_files = []
        current_length = 0
        
        for file_info in relevant_files:
            file_path = file_info.get("file_path", "")
            similarity_score = file_info.get("similarity_score", 0)
            
            # Read file content
            content = self.read_file_content(file_path)
            if not content:
                continue
            
            # Calculate how much content we can include
            remaining_space = max_length - current_length
            if remaining_space <= 0:
                break
            
            # Truncate content if necessary
            if len(content) > remaining_space:
                # Try to truncate at a reasonable boundary
                truncated_content = content[:remaining_space]
                last_paragraph = truncated_content.rfind('\n\n')
                if last_paragraph > remaining_space * 0.7:
                    truncated_content = truncated_content[:last_paragraph]
                content = truncated_content + "\n\n[Content truncated...]"
            
            # Add to context
            file_name = Path(file_path).name
            context_part = f"### File: {file_name} (Relevance: {similarity_score:.2f})\n\n{content}"
            context_parts.append(context_part)
            current_length += len(context_part)
            
            included_files.append({
                "file_path": file_path,
                "file_name": file_name,
                "similarity_score": similarity_score,
                "content_included": len(content)
            })
            
            logger.debug(f"Included {file_name} in context ({len(content)} chars)")
        
        combined_context = "\n\n---\n\n".join(context_parts)
        logger.info(f"Prepared context from {len(included_files)} files ({current_length} chars)")
        
        return combined_context, included_files
    
    def synthesize_answer(self, question: str, context: str, 
                         included_files: List[Dict[str, Any]]) -> Optional[str]:
        """
        Synthesize an answer using OpenAI GPT based on the context.
        
        Args:
            question (str): The user's question
            context (str): Combined context from relevant files
            included_files (List[Dict[str, Any]]): Information about included files
            
        Returns:
            Optional[str]: Synthesized answer or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Create file list for the prompt
        file_list = ", ".join([f["file_name"] for f in included_files])
        
        data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert assistant that answers questions based on provided markdown documentation.
                    Your answers should be comprehensive, accurate, and well-structured. Always base your answers on the provided context.
                    If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information is available.
                    Cite specific files when referencing information. Use markdown formatting for clarity."""
                },
                {
                    "role": "user",
                    "content": f"""Based on the following markdown documentation, please answer this question: {question}

The following files were identified as most relevant: {file_list}

Context from these files:

{context}

Please provide a comprehensive answer based on this documentation. Include specific references to the source files when citing information."""
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making synthesis API call (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
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
                        return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return None
            
            # Wait before retrying
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def answer_question(self, question: str, top_k: int = 5, 
                       similarity_threshold: float = 0.6,
                       include_sources: bool = True) -> Dict[str, Any]:
        """
        Answer a question by finding relevant files and synthesizing a response.
        
        Args:
            question (str): The user's question
            top_k (int): Number of top results to consider
            similarity_threshold (float): Minimum similarity score
            include_sources (bool): Whether to include source file information
            
        Returns:
            Dict[str, Any]: Answer with metadata
        """
        start_time = time.time()
        logger.info(f"Answering question: '{question}'")
        
        # Find relevant files
        relevant_files = self.find_relevant_files(question, top_k, similarity_threshold)
        
        if not relevant_files:
            return {
                "question": question,
                "answer": "I couldn't find any relevant documentation to answer your question. Please try rephrasing or asking about topics covered in the knowledge base.",
                "sources": [],
                "processing_time": time.time() - start_time,
                "status": "no_relevant_files"
            }
        
        # Prepare context
        context, included_files = self.prepare_context(relevant_files)
        
        # Synthesize answer
        answer = self.synthesize_answer(question, context, included_files)
        
        if not answer:
            return {
                "question": question,
                "answer": "I found relevant documentation but encountered an error while generating the answer. Please try again.",
                "sources": included_files if include_sources else [],
                "processing_time": time.time() - start_time,
                "status": "synthesis_failed"
            }
        
        # Prepare response
        response = {
            "question": question,
            "answer": answer,
            "processing_time": time.time() - start_time,
            "status": "success"
        }
        
        if include_sources:
            response["sources"] = [
                {
                    "file": f["file_name"],
                    "path": f["file_path"],
                    "relevance_score": f["similarity_score"],
                    "content_used": f["content_included"]
                }
                for f in included_files
            ]
        
        logger.info(f"Successfully answered question in {response['processing_time']:.2f}s")
        return response
    
    def batch_answer_questions(self, questions: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Answer multiple questions in batch.
        
        Args:
            questions (List[str]): List of questions
            **kwargs: Additional arguments for answer_question
            
        Returns:
            List[Dict[str, Any]]: List of answers
        """
        logger.info(f"Batch processing {len(questions)} questions")
        answers = []
        
        for i, question in enumerate(questions, 1):
            logger.info(f"Processing question {i}/{len(questions)}")
            answer = self.answer_question(question, **kwargs)
            answers.append(answer)
            
            # Add delay between API calls
            if i < len(questions):
                time.sleep(1.0)
        
        return answers


def main():
    """
    Command-line interface for the question-answering system.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Question-answering system for knowledge base")
    parser.add_argument("--db-path", default="data/knowledge_base.json",
                       help="Path to the knowledge database")
    parser.add_argument("--embeddings-cache", default="data/embeddings_cache.json",
                       help="Path to embeddings cache file")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question")
    ask_parser.add_argument("question", help="Your question")
    ask_parser.add_argument("--top-k", type=int, default=5,
                           help="Number of files to consider")
    ask_parser.add_argument("--threshold", type=float, default=0.6,
                           help="Similarity threshold (0-1)")
    ask_parser.add_argument("--no-sources", action="store_true",
                           help="Don't include source information")
    
    # Interactive mode
    interactive_parser = subparsers.add_parser("interactive", 
                                              help="Interactive question-answering mode")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize QA system
        qa_system = QuestionAnswering(args.db_path, args.embeddings_cache)
        
        if args.command == "ask":
            # Answer single question
            result = qa_system.answer_question(
                args.question,
                top_k=args.top_k,
                similarity_threshold=args.threshold,
                include_sources=not args.no_sources
            )
            
            print(f"\n❓ Question: {result['question']}")
            print(f"\n💡 Answer:\n{result['answer']}")
            
            if result.get('sources'):
                print(f"\n📚 Sources used:")
                for source in result['sources']:
                    print(f"   - {source['file']} (relevance: {source['relevance_score']:.2f})")
            
            print(f"\n⏱️  Processing time: {result['processing_time']:.2f}s")
            
        elif args.command == "interactive":
            # Interactive mode
            print("🤖 Interactive Question-Answering Mode")
            print("Type 'quit' or 'exit' to stop")
            print("-" * 50)
            
            while True:
                try:
                    question = input("\n❓ Your question: ").strip()
                    
                    if question.lower() in ['quit', 'exit']:
                        print("👋 Goodbye!")
                        break
                    
                    if not question:
                        continue
                    
                    result = qa_system.answer_question(question)
                    
                    print(f"\n💡 Answer:\n{result['answer']}")
                    
                    if result.get('sources'):
                        print(f"\n📚 Sources: {', '.join(s['file'] for s in result['sources'])}")
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                    
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()