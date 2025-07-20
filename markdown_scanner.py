"""
Markdown Scanner Module

This module provides functionality to scan directories and find all markdown files.
It builds a comprehensive list of .md files with their full paths for processing
by the knowledge base system.
"""

import os
from pathlib import Path
from typing import List, Set
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkdownScanner:
    """
    Scans directories for markdown files and maintains a registry of discovered files.
    """
    
    def __init__(self, base_directory: str = "."):
        """
        Initialize the scanner with a base directory.
        
        Args:
            base_directory (str): The root directory to start scanning from
        """
        self.base_directory = Path(base_directory).resolve()
        self.markdown_files: List[Path] = []
        self.excluded_patterns: Set[str] = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            ".pytest_cache", ".mypy_cache", "*.tmp", "*.temp"
        }
    
    def add_exclusion_pattern(self, pattern: str) -> None:
        """
        Add a pattern to exclude from scanning.
        
        Args:
            pattern (str): Pattern to exclude (directory name or glob pattern)
        """
        self.excluded_patterns.add(pattern)
    
    def should_exclude_path(self, path: Path) -> bool:
        """
        Check if a path should be excluded from scanning.
        
        Args:
            path (Path): Path to check
            
        Returns:
            bool: True if path should be excluded
        """
        # Check if any part of the path matches exclusion patterns
        for part in path.parts:
            if part in self.excluded_patterns:
                return True
        
        # Check if filename matches any glob patterns
        for pattern in self.excluded_patterns:
            if pattern.startswith("*") and path.name.endswith(pattern[1:]):
                return True
                
        return False
    
    def scan_directory(self, directory: Path = None) -> List[Path]:
        """
        Recursively scan a directory for markdown files.
        
        Args:
            directory (Path, optional): Directory to scan. Defaults to base_directory.
            
        Returns:
            List[Path]: List of paths to markdown files found
        """
        if directory is None:
            directory = self.base_directory
            
        found_files = []
        
        try:
            # Ensure directory exists and is actually a directory
            if not directory.exists():
                logger.warning(f"Directory does not exist: {directory}")
                return found_files
                
            if not directory.is_dir():
                logger.warning(f"Path is not a directory: {directory}")
                return found_files
            
            # Walk through directory tree
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)
                
                # Skip excluded directories
                if self.should_exclude_path(root_path):
                    continue
                
                # Filter out excluded subdirectories
                dirs[:] = [d for d in dirs if not self.should_exclude_path(root_path / d)]
                
                # Find markdown files in current directory
                for file in files:
                    file_path = root_path / file
                    
                    # Check if it's a markdown file
                    if file.lower().endswith(('.md', '.markdown')):
                        if not self.should_exclude_path(file_path):
                            found_files.append(file_path)
                            logger.debug(f"Found markdown file: {file_path}")
            
            logger.info(f"Found {len(found_files)} markdown files in {directory}")
            return found_files
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing {directory}: {e}")
            return found_files
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            return found_files
    
    def scan_and_update(self, directory: Path = None) -> None:
        """
        Scan for markdown files and update the internal registry.
        
        Args:
            directory (Path, optional): Directory to scan. Defaults to base_directory.
        """
        self.markdown_files = self.scan_directory(directory)
    
    def get_markdown_files(self) -> List[Path]:
        """
        Get the list of discovered markdown files.
        
        Returns:
            List[Path]: List of paths to markdown files
        """
        return self.markdown_files.copy()
    
    def get_file_count(self) -> int:
        """
        Get the count of discovered markdown files.
        
        Returns:
            int: Number of markdown files found
        """
        return len(self.markdown_files)
    
    def get_relative_paths(self) -> List[str]:
        """
        Get markdown file paths relative to the base directory.
        
        Returns:
            List[str]: List of relative path strings
        """
        relative_paths = []
        for file_path in self.markdown_files:
            try:
                relative_path = file_path.relative_to(self.base_directory)
                relative_paths.append(str(relative_path))
            except ValueError:
                # File is outside base directory, use absolute path
                relative_paths.append(str(file_path))
        
        return relative_paths


def main():
    """
    Command-line interface for the markdown scanner.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan directories for markdown files")
    parser.add_argument("directory", nargs="?", default=".", 
                       help="Directory to scan (default: current directory)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--exclude", action="append", default=[],
                       help="Add exclusion pattern (can be used multiple times)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create scanner and add exclusions
    scanner = MarkdownScanner(args.directory)
    for pattern in args.exclude:
        scanner.add_exclusion_pattern(pattern)
    
    # Scan for files
    scanner.scan_and_update()
    
    # Display results
    files = scanner.get_markdown_files()
    print(f"Found {len(files)} markdown files:")
    for file_path in files:
        print(f"  {file_path}")


if __name__ == "__main__":
    main()