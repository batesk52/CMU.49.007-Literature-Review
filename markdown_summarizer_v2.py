"""
Markdown Summarizer V2 Module

This version supports multiple API providers (OpenAI, Gemini, Claude)
through the unified API provider interface.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

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


class MarkdownSummarizerV2:
    """
    Summarizes markdown content using configurable API providers.
    """
    
    def __init__(self, provider_name: str = None):
        """
        Initialize the summarizer with specified API provider.
        
        Args:
            provider_name (str, optional): API provider to use ('openai', 'gemini', 'claude')
                                         If None, auto-detects based on available API keys
        """
        try:
            self.provider = APIProviderFactory.create_provider(provider_name)
            self.provider_name = provider_name or self.provider.__class__.__name__.replace('Provider', '')
            logger.info(f"Initialized summarizer with {self.provider_name} provider")
        except ValueError as e:
            logger.error(f"Failed to initialize API provider: {e}")
            raise
        
        self.max_content_length = 15000  # Conservative limit for API calls
    
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
        Generate a summary of markdown content using the configured API provider.
        
        Args:
            content (str): The markdown content to summarize
            file_path (Path, optional): Path to the source file for context
            
        Returns:
            str: The generated summary
            
        Raises:
            Exception: If the API call fails
        """
        # Truncate content if necessary
        content_to_summarize = self.truncate_content(content)
        
        # Create context-aware file reference
        file_context = f" (from {file_path.name})" if file_path else ""
        
        # Generate summary using the provider
        logger.debug(f"Generating summary using {self.provider_name}")
        summary = self.provider.generate_summary(content_to_summarize, file_context)
        
        if summary:
            logger.info(f"Successfully generated summary for {file_path or 'content'}")
            return summary
        else:
            raise Exception(f"Failed to generate summary using {self.provider_name}")
    
    def summarize_file(self, file_path: Path) -> Dict[str, str]:
        """
        Read a markdown file and generate its summary.
        
        Args:
            file_path (Path): Path to the markdown file
            
        Returns:
            Dict[str, str]: Dictionary with 'file_path', 'content_length', and 'summary' keys
        """
        logger.info(f"Processing file: {file_path}")
        
        try:
            content = self.read_markdown_file(file_path)
            summary = self.summarize_content(content, file_path)
            
            return {
                'file_path': str(file_path),
                'content_length': len(content),
                'summary': summary,
                'provider': self.provider_name
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
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of available API providers."""
        return APIProviderFactory.get_available_providers()


def main():
    """
    Command-line interface for the markdown summarizer.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Summarize markdown files using AI")
    parser.add_argument("files", nargs="+", help="Markdown files to summarize")
    parser.add_argument("--provider", choices=['openai', 'gemini', 'claude'],
                       help="API provider to use (auto-detect if not specified)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("-o", "--output", help="Output file for summaries (JSON format)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Show available providers
    available = MarkdownSummarizerV2.get_available_providers()
    print(f"Available API providers: {', '.join(available)}")
    
    # Create summarizer
    try:
        summarizer = MarkdownSummarizerV2(args.provider)
    except ValueError as e:
        print(f"Error: {e}")
        print("Set one of these environment variables:")
        print("  - OPENAI_API_KEY for OpenAI")
        print("  - GEMINI_API_KEY for Google Gemini")
        print("  - CLAUDE_API_KEY or ANTHROPIC_API_KEY for Claude")
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
            print(f"Provider: {summary['provider']}")
            print(f"Length: {summary['content_length']} characters")
            print(f"Summary: {summary['summary']}")
    
    return 0


if __name__ == "__main__":
    exit(main())