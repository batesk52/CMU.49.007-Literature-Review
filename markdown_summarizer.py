"""
Markdown Summarizer Module

This module provides functionality to summarize markdown content using OpenAI's GPT API.
It reads markdown files and generates concise, abstract-like summaries suitable for 
a knowledge base system.
"""

import os
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging
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


class MarkdownSummarizer:
    """
    Summarizes markdown content using OpenAI's GPT API.
    """
    
    def __init__(self):
        """
        Initialize the summarizer with OpenAI API configuration.
        """
        config = get_config()
        self.openai_api_key = config.api.openai_api_key
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.max_content_length = config.processing.max_content_length
        self.max_retries = config.processing.max_retries
        self.retry_delay = config.processing.retry_delay
        self.model = config.api.openai_model
    
    def read_markdown_file(self, file_path: Path) -> str:
        """
        Read the content of a markdown file.
        
        Args:
            file_path (Path): Path to the markdown file
            
        Returns:
            str: The content of the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Read {len(content)} characters from {file_path}")
                return content
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    logger.warning(f"File {file_path} read with latin-1 encoding")
                    return content
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                raise IOError(f"Could not read file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def truncate_content(self, content: str) -> str:
        """
        Truncate content if it's too long for the API.
        
        Args:
            content (str): The original content
            
        Returns:
            str: Truncated content if necessary
        """
        if len(content) <= self.max_content_length:
            return content
        
        # Try to truncate at a reasonable boundary (paragraph, sentence)
        truncated = content[:self.max_content_length]
        
        # Find last paragraph break
        last_paragraph = truncated.rfind('\n\n')
        if last_paragraph > self.max_content_length * 0.7:
            truncated = truncated[:last_paragraph]
        else:
            # Find last sentence
            last_sentence = max(
                truncated.rfind('. '),
                truncated.rfind('! '),
                truncated.rfind('? ')
            )
            if last_sentence > self.max_content_length * 0.7:
                truncated = truncated[:last_sentence + 1]
        
        logger.info(f"Content truncated from {len(content)} to {len(truncated)} characters")
        return truncated + "\n\n[Content truncated...]"
    
    def summarize_content(self, content: str, file_path: Optional[Path] = None) -> str:
        """
        Generate a summary of markdown content using OpenAI GPT.
        
        Args:
            content (str): The markdown content to summarize
            file_path (Path, optional): Path to the source file for context
            
        Returns:
            str: The generated summary
            
        Raises:
            Exception: If the API call fails after retries
        """
        # Truncate content if necessary
        content_to_summarize = self.truncate_content(content)
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Create context-aware prompt
        file_context = f" (from {file_path.name})" if file_path else ""
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert at creating concise, informative summaries of markdown documents. 
                    Your summaries should be abstract-like, capturing the main topics, key points, and purpose of the document.
                    Focus on what someone would need to know to determine if this document is relevant to their query.
                    Keep summaries between 2-4 sentences and include the document's primary focus and any important technical details."""
                },
                {
                    "role": "user",
                    "content": f"Please create a concise summary of this markdown document{file_context}:\n\n{content_to_summarize}"
                }
            ],
            "max_tokens": 200,
            "temperature": 0.3
        }
        
        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making API call (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    logger.info(f"Successfully generated summary for {file_path or 'content'}")
                    return summary
                    
                elif response.status_code == 429:  # Rate limited
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    if attempt == self.max_retries - 1:
                        raise Exception(f"API call failed: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise Exception("API request timed out after multiple attempts")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"API request failed: {e}")
            
            # Wait before retrying
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        raise Exception("Failed to generate summary after all retries")
    
    def summarize_file(self, file_path: Path) -> Dict[str, str]:
        """
        Read a markdown file and generate its summary.
        
        Args:
            file_path (Path): Path to the markdown file
            
        Returns:
            Dict[str, str]: Dictionary with 'file_path', 'content', and 'summary' keys
        """
        logger.info(f"Processing file: {file_path}")
        
        try:
            content = self.read_markdown_file(file_path)
            summary = self.summarize_content(content, file_path)
            
            return {
                'file_path': str(file_path),
                'content_length': len(content),
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            raise
    
    def summarize_files(self, file_paths: List[Path]) -> List[Dict[str, str]]:
        """
        Summarize multiple markdown files.
        
        Args:
            file_paths (List[Path]): List of paths to markdown files
            
        Returns:
            List[Dict[str, str]]: List of file summaries
        """
        summaries = []
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                logger.info(f"Processing file {i}/{len(file_paths)}: {file_path.name}")
                summary_data = self.summarize_file(file_path)
                summaries.append(summary_data)
                
                # Add small delay between API calls to be respectful
                if i < len(file_paths):
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Skipping file {file_path} due to error: {e}")
                # Continue with other files rather than failing completely
                continue
        
        logger.info(f"Successfully processed {len(summaries)} out of {len(file_paths)} files")
        return summaries


def main():
    """
    Command-line interface for the markdown summarizer.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Summarize markdown files using OpenAI")
    parser.add_argument("files", nargs="+", help="Markdown files to summarize")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("-o", "--output", help="Output file for summaries (JSON format)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create summarizer
    try:
        summarizer = MarkdownSummarizer()
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    # Process files
    file_paths = [Path(f) for f in args.files]
    summaries = summarizer.summarize_files(file_paths)
    
    # Output results
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(summaries, f, indent=2)
        print(f"Summaries saved to {args.output}")
    else:
        for summary in summaries:
            print(f"\n=== {summary['file_path']} ===")
            print(f"Length: {summary['content_length']} characters")
            print(f"Summary: {summary['summary']}")
    
    return 0


if __name__ == "__main__":
    exit(main())