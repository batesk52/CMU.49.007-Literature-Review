"""
Knowledge Base Builder

This module integrates the markdown scanner, summarizer, and database components
to create a complete knowledge base system that automatically processes
markdown files and builds a searchable database.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import logging
import time
from config import get_config

# Import our custom modules
from markdown_scanner import MarkdownScanner
from markdown_summarizer_v2 import MarkdownSummarizerV2
from knowledge_database import KnowledgeDatabase
from semantic_search_v2 import SemanticSearchV2
from question_answerer import QuestionAnswerer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeBaseBuilder:
    """
    Orchestrates the process of building a knowledge base from markdown files.
    """
    
    def __init__(self, 
                 base_directory: Optional[str] = None, 
                 db_path: Optional[str] = None,
                 embeddings_cache_path: Optional[str] = None,
                 force_update: bool = False):
        """
        Initialize the knowledge base builder.
        
        Args:
            base_directory (str): Directory to scan for markdown files
            db_path (str): Path to the JSON database file
            embeddings_cache_path (str): Path to the embeddings cache file
            force_update (bool): Whether to force re-processing of all files
        """
        config = get_config()
        
        # Use provided values or get from config
        self.base_directory = Path(base_directory or config.paths.base_directory).resolve()
        db_path = db_path or str(config.paths.knowledge_base_path)
        embeddings_cache_path = embeddings_cache_path or str(config.paths.embeddings_cache_path)
        
        self.force_update = force_update
        
        # Initialize components
        try:
            self.scanner = MarkdownScanner(str(self.base_directory))
            # Auto-detect provider based on available API keys
            self.summarizer = MarkdownSummarizerV2()  # Will auto-detect Gemini/OpenAI/Claude
            self.database = KnowledgeDatabase(db_path)
            # Use v2 for semantic search which supports multiple providers
            self.semantic_search = SemanticSearchV2(embeddings_cache_path)
            
            # Try to initialize Q&A system, but make it optional
            try:
                self.qa_system = QuestionAnswerer(db_path, embeddings_cache_path)
            except ValueError as e:
                logger.warning(f"Question answering system unavailable: {e}")
                self.qa_system = None
            
            logger.info(f"Initialized knowledge base builder for {self.base_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def scan_files(self) -> List[Path]:
        """
        Scan for markdown files in the base directory.
        
        Returns:
            List[Path]: List of markdown files found
        """
        logger.info("Scanning for markdown files...")
        self.scanner.scan_and_update()
        files = self.scanner.get_markdown_files()
        
        logger.info(f"Found {len(files)} markdown files")
        return files
    
    def process_file(self, file_path: Path) -> bool:
        """
        Process a single markdown file: read, summarize, and add to database.
        
        Args:
            file_path (Path): Path to the markdown file
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            logger.info(f"Processing: {file_path.name}")
            
            # Check if file needs processing
            if not self.force_update and not self.database.has_file_changed(file_path):
                logger.info(f"File unchanged, skipping: {file_path.name}")
                return True
            
            # Read and summarize the file
            summary_data = self.summarizer.summarize_file(file_path)
            
            # Add to database
            self.database.add_file(
                file_path=file_path,
                summary=summary_data['summary'],
                content_length=summary_data['content_length']
            )
            
            logger.info(f"Successfully processed: {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return False
    
    def build_knowledge_base(self) -> dict:
        """
        Build the complete knowledge base by processing all markdown files.
        
        Returns:
            dict: Summary of the build process
        """
        start_time = time.time()
        logger.info("Starting knowledge base build...")
        
        # Scan for files
        markdown_files = self.scan_files()
        
        if not markdown_files:
            logger.warning("No markdown files found to process")
            return {
                "status": "completed",
                "files_found": 0,
                "files_processed": 0,
                "files_failed": 0,
                "duration_seconds": time.time() - start_time
            }
        
        # Process each file
        processed_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(markdown_files, 1):
            logger.info(f"Processing file {i}/{len(markdown_files)}: {file_path.name}")
            
            if self.process_file(file_path):
                processed_count += 1
            else:
                failed_count += 1
            
            # Add small delay between API calls to be respectful
            if i < len(markdown_files):
                time.sleep(0.5)
        
        # Clean up missing files from database
        logger.info("Cleaning up database...")
        removed_count = self.database.cleanup_missing_files()
        
        # Save the database
        logger.info("Saving database...")
        self.database.save_database()
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Return summary
        result = {
            "status": "completed",
            "files_found": len(markdown_files),
            "files_processed": processed_count,
            "files_failed": failed_count,
            "files_removed": removed_count,
            "duration_seconds": duration
        }
        
        logger.info(f"Knowledge base build completed in {duration:.1f}s")
        logger.info(f"Processed: {processed_count}, Failed: {failed_count}, Removed: {removed_count}")
        
        return result
    
    def search_knowledge_base(self, query: str, case_sensitive: bool = False) -> List[dict]:
        """
        Search the knowledge base for files matching a query (keyword search).
        
        Args:
            query (str): Search query
            case_sensitive (bool): Whether to perform case-sensitive search
            
        Returns:
            List[dict]: List of matching files
        """
        logger.info(f"Searching knowledge base for: '{query}'")
        results = self.database.search_summaries(query, case_sensitive)
        
        # Format results for display
        formatted_results = []
        for result in results:
            formatted_results.append({
                "filename": result.get("filename", "Unknown"),
                "file_path": result.get("file_path", ""),
                "summary": result.get("summary", ""),
                "content_length": result.get("content_length", 0),
                "search_type": "keyword"
            })
        
        return formatted_results
    
    def semantic_search_knowledge_base(self, query: str, top_k: int = 5, 
                                     similarity_threshold: float = 0.7) -> List[dict]:
        """
        Perform semantic search on the knowledge base using embeddings.
        
        Args:
            query (str): Search query
            top_k (int): Number of top results to return
            similarity_threshold (float): Minimum similarity score (0-1)
            
        Returns:
            List[dict]: List of semantically similar files with scores
        """
        logger.info(f"Performing semantic search for: '{query}'")
        
        try:
            results = self.semantic_search.semantic_search(
                query, self.database, top_k, similarity_threshold
            )
            
            # Format results for display
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "filename": result.get("filename", "Unknown"),
                    "file_path": result.get("file_path", ""),
                    "summary": result.get("summary", ""),
                    "content_length": result.get("content_length", 0),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "search_type": "semantic"
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def build_embeddings(self, force_rebuild: bool = False) -> int:
        """
        Build embeddings for all files in the knowledge base.
        
        Args:
            force_rebuild (bool): Whether to rebuild all embeddings
            
        Returns:
            int: Number of embeddings created
        """
        logger.info("Building embeddings for knowledge base...")
        
        try:
            created = self.semantic_search.build_embeddings_for_database(
                self.database, force_rebuild
            )
            logger.info(f"Created {created} new embeddings")
            return created
            
        except Exception as e:
            logger.error(f"Failed to build embeddings: {e}")
            return 0
    
    def get_database_stats(self) -> dict:
        """
        Get statistics about the knowledge base database.
        
        Returns:
            dict: Database statistics
        """
        return self.database.get_statistics()
    
    def answer_question(self, question: str, top_k: int = 5,
                       similarity_threshold: float = 0.6) -> dict:
        """
        Answer a question using the knowledge base.
        
        Args:
            question (str): The user's question
            top_k (int): Number of files to consider
            similarity_threshold (float): Minimum similarity score
            
        Returns:
            dict: Answer with metadata
        """
        if self.qa_system is None:
            logger.warning("Question answering not available - OpenAI API key required")
            return {
                "answer": "Question answering requires an OpenAI API key. You can still use keyword search and semantic search.",
                "source_files": [],
                "confidence": "none"
            }
        return self.qa_system.answer_question(
            question, top_k, similarity_threshold
        )
    
    def identify_files_needing_summaries(self, mode: str = "missing") -> List[Path]:
        """
        Identify files that need summary generation based on the specified mode.
        
        Args:
            mode (str): Generation mode - "missing", "outdated", or "all"
            
        Returns:
            List[Path]: List of files needing summary generation
        """
        logger.info(f"Identifying files needing summaries (mode: {mode})")
        
        # Get all markdown files from filesystem
        all_files = self.scan_files()
        files_needing_summaries = []
        
        for file_path in all_files:
            file_key = str(file_path.resolve())
            
            if mode == "missing":
                # Files not in database or without summaries
                if not self.database.has_file(file_key):
                    files_needing_summaries.append(file_path)
                    logger.debug(f"Missing from database: {file_path.name}")
                else:
                    file_data = self.database.get_file_data(file_key)
                    if not file_data or not file_data.get("summary"):
                        files_needing_summaries.append(file_path)
                        logger.debug(f"Missing summary: {file_path.name}")
                        
            elif mode == "outdated":
                # Files that have changed since last processing
                if self.database.has_file_changed(file_path):
                    files_needing_summaries.append(file_path)
                    logger.debug(f"Outdated: {file_path.name}")
                    
            elif mode == "all":
                # All files regardless of current state
                files_needing_summaries.append(file_path)
                
        logger.info(f"Found {len(files_needing_summaries)} files needing summaries")
        return files_needing_summaries
    
    def generate_summaries(self, mode: str = "missing", target_files: Optional[List[str]] = None,
                          progress_callback: Optional[callable] = None) -> dict:
        """
        Generate summaries for files based on the specified mode.
        
        Args:
            mode (str): Generation mode - "missing", "outdated", or "all"
            target_files (List[str]): Specific files/patterns to target (optional)
            progress_callback (callable): Callback function for progress updates
            
        Returns:
            dict: Summary of the generation process
        """
        start_time = time.time()
        logger.info(f"Starting summary generation (mode: {mode})")
        
        # Identify files needing processing
        files_to_process = self.identify_files_needing_summaries(mode)
        
        # Filter by target files if specified
        if target_files:
            filtered_files = []
            for file_path in files_to_process:
                for target in target_files:
                    if target in str(file_path) or file_path.name == target:
                        filtered_files.append(file_path)
                        break
            files_to_process = filtered_files
            logger.info(f"Filtered to {len(files_to_process)} target files")
        
        if not files_to_process:
            logger.info("No files need summary generation")
            return {
                "status": "completed",
                "mode": mode,
                "files_found": 0,
                "files_processed": 0,
                "files_failed": 0,
                "duration_seconds": time.time() - start_time
            }
        
        # Process each file
        processed_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(files_to_process, 1):
            logger.info(f"Generating summary {i}/{len(files_to_process)}: {file_path.name}")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i, len(files_to_process), file_path.name)
            
            try:
                # Generate summary for the file
                summary_data = self.summarizer.summarize_file(file_path)
                
                # Add/update in database
                self.database.add_file(
                    file_path=file_path,
                    summary=summary_data['summary'],
                    content_length=summary_data['content_length']
                )
                
                processed_count += 1
                logger.info(f"Successfully generated summary for: {file_path.name}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to generate summary for {file_path.name}: {e}")
            
            # Add small delay between API calls to be respectful
            if i < len(files_to_process):
                time.sleep(0.5)
        
        # Save the database
        logger.info("Saving database with new summaries...")
        self.database.save_database()
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Return summary
        result = {
            "status": "completed",
            "mode": mode,
            "files_found": len(files_to_process),
            "files_processed": processed_count,
            "files_failed": failed_count,
            "duration_seconds": duration
        }
        
        logger.info(f"Summary generation completed in {duration:.1f}s")
        logger.info(f"Processed: {processed_count}, Failed: {failed_count}")
        
        return result
    
    def validate_summaries(self) -> dict:
        """
        Validate the quality and consistency of summaries in the database.
        
        Returns:
            dict: Validation results including stats and issues found
        """
        logger.info("Validating summary quality and database consistency")
        
        validation_results = {
            "total_files": 0,
            "files_with_summaries": 0,
            "files_missing_summaries": 0,
            "files_with_short_summaries": 0,
            "files_with_long_summaries": 0,
            "orphaned_database_entries": 0,
            "consistency_issues": []
        }
        
        # Get all files from database
        db_files = self.database.get_all_files_dict()
        validation_results["total_files"] = len(db_files)
        
        # Get all markdown files from filesystem
        filesystem_files = self.scan_files()
        filesystem_file_keys = {str(f.resolve()) for f in filesystem_files}
        
        for file_key, file_data in db_files.items():
            # Check if file still exists on filesystem
            if file_key not in filesystem_file_keys:
                validation_results["orphaned_database_entries"] += 1
                validation_results["consistency_issues"].append(
                    f"Database entry for missing file: {file_key}"
                )
                continue
            
            # Check summary quality
            summary = file_data.get("summary", "")
            if not summary:
                validation_results["files_missing_summaries"] += 1
                validation_results["consistency_issues"].append(
                    f"Missing summary: {file_data.get('filename', file_key)}"
                )
            else:
                validation_results["files_with_summaries"] += 1
                
                # Check summary length (target: 2-3 sentences, roughly 100-300 chars)
                if len(summary) < 50:
                    validation_results["files_with_short_summaries"] += 1
                    validation_results["consistency_issues"].append(
                        f"Summary too short: {file_data.get('filename', file_key)}"
                    )
                elif len(summary) > 500:
                    validation_results["files_with_long_summaries"] += 1
                    validation_results["consistency_issues"].append(
                        f"Summary too long: {file_data.get('filename', file_key)}"
                    )
        
        # Check for files in filesystem but not in database
        db_file_keys = set(db_files.keys())
        for fs_file in filesystem_files:
            fs_file_key = str(fs_file.resolve())
            if fs_file_key not in db_file_keys:
                validation_results["files_missing_summaries"] += 1
                validation_results["consistency_issues"].append(
                    f"File not in database: {fs_file.name}"
                )
        
        logger.info(f"Validation completed: {validation_results['files_with_summaries']}/{validation_results['total_files']} files have summaries")
        if validation_results["consistency_issues"]:
            logger.warning(f"Found {len(validation_results['consistency_issues'])} consistency issues")
        
        return validation_results


def main():
    """
    Command-line interface for the knowledge base builder.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Build and manage a markdown knowledge base")
    parser.add_argument("directory", nargs="?", default=".", 
                       help="Directory to scan for markdown files")
    parser.add_argument("--db-path", default="data/knowledge_base.json",
                       help="Path to the database file")
    parser.add_argument("--embeddings-cache", default="data/embeddings_cache.json",
                       help="Path to embeddings cache file")
    parser.add_argument("--force-update", action="store_true",
                       help="Force re-processing of all files")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Build command (default)
    build_parser = subparsers.add_parser("build", help="Build the knowledge base")
    
    # Search command (keyword)
    search_parser = subparsers.add_parser("search", help="Search the knowledge base (keyword)")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--case-sensitive", action="store_true",
                              help="Case sensitive search")
    
    # Semantic search command
    semantic_parser = subparsers.add_parser("semantic-search", help="Semantic search using embeddings")
    semantic_parser.add_argument("query", help="Search query")
    semantic_parser.add_argument("--top-k", type=int, default=5,
                                help="Number of results to return")
    semantic_parser.add_argument("--threshold", type=float, default=0.7,
                                help="Similarity threshold (0-1)")
    
    # Build embeddings command
    embeddings_parser = subparsers.add_parser("build-embeddings", help="Build embeddings for semantic search")
    embeddings_parser.add_argument("--force", action="store_true",
                                  help="Force rebuild all embeddings")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create knowledge base builder
        builder = KnowledgeBaseBuilder(
            base_directory=args.directory,
            db_path=args.db_path,
            embeddings_cache_path=args.embeddings_cache,
            force_update=args.force_update
        )
        
        if args.command == "search":
            results = builder.search_knowledge_base(args.query, args.case_sensitive)
            print(f"\n🔍 Found {len(results)} files matching '{args.query}':")
            
            for result in results:
                print(f"\n📄 {result['filename']}")
                print(f"   Path: {result['file_path']}")
                print(f"   Length: {result['content_length']} characters")
                print(f"   Summary: {result['summary']}")
                
        elif args.command == "semantic-search":
            results = builder.semantic_search_knowledge_base(
                args.query, args.top_k, args.threshold
            )
            print(f"\n🧠 Semantic search results for '{args.query}':")
            print(f"Found {len(results)} semantically similar files:")
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. 📄 {result['filename']} (similarity: {result['similarity_score']:.3f})")
                print(f"   Path: {result['file_path']}")
                print(f"   Length: {result['content_length']} characters")
                print(f"   Summary: {result['summary']}")
                
        elif args.command == "build-embeddings":
            print(f"\n🔧 Building embeddings for knowledge base...")
            created = builder.build_embeddings(args.force)
            print(f"✅ Created {created} new embeddings")
            
        elif args.command == "stats":
            stats = builder.get_database_stats()
            print("\n📊 Knowledge Base Statistics:")
            print(f"   Total files: {stats['total_files']}")
            print(f"   Total content: {stats['total_content_length']:,} characters")
            print(f"   Average content length: {stats['average_content_length']:.0f} characters")
            print(f"   Average summary length: {stats['average_summary_length']:.0f} characters")
            
            if stats['newest_file']:
                print(f"   Newest file added: {stats['newest_file']}")
            if stats['oldest_file']:
                print(f"   Oldest file added: {stats['oldest_file']}")
                
        else:
            # Default: build the knowledge base
            print(f"\n🔍 Building knowledge base from: {args.directory}")
            result = builder.build_knowledge_base()
            
            print(f"\n✅ Build completed in {result['duration_seconds']:.1f} seconds")
            print(f"   Files found: {result['files_found']}")
            print(f"   Files processed: {result['files_processed']}")
            print(f"   Files failed: {result['files_failed']}")
            print(f"   Files removed: {result['files_removed']}")
            
            if result['files_failed'] > 0:
                print(f"\n⚠️  {result['files_failed']} files failed to process. Check logs for details.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()