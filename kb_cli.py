#!/usr/bin/env python3
"""
Knowledge Base CLI Interface

A comprehensive command-line interface for the AI-powered markdown knowledge base system.
Provides easy access to all knowledge base functionality through intuitive commands.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, List, Dict
import json
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_base_builder import KnowledgeBaseBuilder
from document_ingester import DocumentIngester
from error_handler import setup_logging, safe_execute, error_handler

# ASCII art banner
BANNER = """
╔══════════════════════════════════════════════════════════╗
║         AI-Powered Markdown Knowledge Base System         ║
║                  Intelligent Q&A from Markdown            ║
╚══════════════════════════════════════════════════════════╝
"""

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def colorize(text: str, color: str) -> str:
    """Apply color to text for terminal output."""
    return f"{color}{text}{Colors.ENDC}"

def print_banner():
    """Print the application banner."""
    print(colorize(BANNER, Colors.CYAN))

def print_section(title: str):
    """Print a section header."""
    print(f"\n{colorize('═' * 60, Colors.BLUE)}")
    print(colorize(f"  {title}", Colors.BOLD + Colors.BLUE))
    print(colorize('═' * 60, Colors.BLUE))

def format_file_info(file_info: dict, index: Optional[int] = None) -> str:
    """Format file information for display."""
    lines = []
    
    if index is not None:
        lines.append(colorize(f"\n{index}. {file_info['filename']}", Colors.BOLD + Colors.GREEN))
    else:
        lines.append(colorize(f"\n📄 {file_info['filename']}", Colors.BOLD + Colors.GREEN))
    
    lines.append(f"   {colorize('Path:', Colors.CYAN)} {file_info['file_path']}")
    lines.append(f"   {colorize('Size:', Colors.CYAN)} {file_info.get('content_length', 0):,} characters")
    
    if 'similarity_score' in file_info:
        score = file_info['similarity_score']
        score_color = Colors.GREEN if score > 0.8 else Colors.WARNING if score > 0.6 else Colors.FAIL
        lines.append(f"   {colorize('Similarity:', Colors.CYAN)} {colorize(f'{score:.1%}', score_color)}")
    
    lines.append(f"   {colorize('Summary:', Colors.CYAN)} {file_info['summary'][:200]}...")
    
    return '\n'.join(lines)

class KnowledgeBaseCLI:
    """Command-line interface for the knowledge base system."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.builder = None
        self.ingester = None
        self.logger = logging.getLogger(__name__)
        
    def initialize_builder(self, args):
        """Initialize the knowledge base builder with provided arguments."""
        try:
            self.builder = KnowledgeBaseBuilder(
                base_directory=args.directory,
                db_path=args.db_path,
                embeddings_cache_path=args.embeddings_cache,
                force_update=getattr(args, 'force_update', False)
            )
            return True
        except Exception as e:
            print(colorize(f"❌ Failed to initialize: {e}", Colors.FAIL))
            return False
    
    def cmd_build(self, args):
        """Build or update the knowledge base."""
        print_section("Building Knowledge Base")
        
        print(f"📁 Scanning directory: {colorize(args.directory, Colors.CYAN)}")
        print(f"💾 Database path: {colorize(args.db_path, Colors.CYAN)}")
        
        if args.force_update:
            print(colorize("⚠️  Force update enabled - all files will be reprocessed", Colors.WARNING))
        
        print("\nStarting build process...")
        
        result = safe_execute(self.builder.build_knowledge_base, default_return={})
        
        if result:
            print(f"\n{colorize('✅ Build completed successfully!', Colors.GREEN)}")
            print(f"\n📊 Build Statistics:")
            print(f"   ⏱️  Duration: {result['duration_seconds']:.1f} seconds")
            print(f"   📄 Files found: {result['files_found']}")
            print(f"   ✅ Files processed: {result['files_processed']}")
            print(f"   ❌ Files failed: {result['files_failed']}")
            print(f"   🗑️  Files removed: {result.get('files_removed', 0)}")
            
            if result['files_failed'] > 0:
                print(colorize(f"\n⚠️  {result['files_failed']} files failed to process. Check logs for details.", Colors.WARNING))
        else:
            print(colorize("\n❌ Build failed. Check logs for details.", Colors.FAIL))
    
    def cmd_search(self, args):
        """Perform keyword search."""
        print_section(f"Keyword Search: '{args.query}'")
        
        results = safe_execute(
            lambda: self.builder.search_knowledge_base(args.query, args.case_sensitive),
            default_return=[]
        )
        
        if not results:
            print(colorize(f"\nNo files found matching '{args.query}'", Colors.WARNING))
            return
        
        print(f"\n{colorize(f'Found {len(results)} matching files:', Colors.GREEN)}")
        
        for i, result in enumerate(results, 1):
            print(format_file_info(result, i))
    
    def cmd_semantic_search(self, args):
        """Perform semantic search."""
        print_section(f"Semantic Search: '{args.query}'")
        
        print(f"🔍 Searching for top {args.top_k} semantically similar files...")
        print(f"📊 Similarity threshold: {args.threshold:.0%}")
        
        results = safe_execute(
            lambda: self.builder.semantic_search_knowledge_base(
                args.query, args.top_k, args.threshold
            ),
            default_return=[]
        )
        
        if not results:
            print(colorize(f"\nNo semantically similar files found (threshold: {args.threshold:.0%})", Colors.WARNING))
            return
        
        print(f"\n{colorize(f'Found {len(results)} semantically similar files:', Colors.GREEN)}")
        
        for i, result in enumerate(results, 1):
            print(format_file_info(result, i))
    
    def cmd_ask(self, args):
        """Answer a question using the knowledge base."""
        print_section("Question Answering")
        
        print(f"❓ Question: {colorize(args.question, Colors.CYAN)}")
        print(f"\n🔍 Searching knowledge base...")
        
        result = safe_execute(
            lambda: self.builder.answer_question(
                args.question, args.top_k, args.threshold
            ),
            default_return={}
        )
        
        if not result or 'answer' not in result:
            print(colorize("\n❌ Failed to generate answer. Check logs for details.", Colors.FAIL))
            return
        
        print(f"\n{colorize('💡 Answer:', Colors.GREEN)}")
        print(f"\n{result['answer']}")
        
        if result.get('source_files'):
            print(f"\n{colorize('📚 Sources used:', Colors.CYAN)}")
            for i, source in enumerate(result['source_files'], 1):
                print(f"   {i}. {source['filename']} (similarity: {source['similarity_score']:.1%})")
        
        if result.get('confidence'):
            confidence = result['confidence']
            conf_color = Colors.GREEN if confidence == 'high' else Colors.WARNING if confidence == 'medium' else Colors.FAIL
            print(f"\n{colorize('📊 Confidence:', Colors.CYAN)} {colorize(confidence, conf_color)}")
    
    def cmd_stats(self, args):
        """Display knowledge base statistics."""
        print_section("Knowledge Base Statistics")
        
        stats = safe_execute(self.builder.get_database_stats, default_return={})
        
        if not stats:
            print(colorize("❌ Failed to retrieve statistics.", Colors.FAIL))
            return
        
        print(f"\n📊 Database Overview:")
        print(f"   📄 Total files: {stats.get('total_files', 0)}")
        print(f"   📝 Total content: {stats.get('total_content_length', 0):,} characters")
        print(f"   📏 Average file size: {stats.get('average_content_length', 0):,.0f} characters")
        print(f"   📋 Average summary size: {stats.get('average_summary_length', 0):,.0f} characters")
        
        if stats.get('newest_file'):
            print(f"\n   🆕 Newest file: {stats['newest_file']}")
        if stats.get('oldest_file'):
            print(f"   🕰️  Oldest file: {stats['oldest_file']}")
    
    def cmd_embeddings(self, args):
        """Build or rebuild embeddings."""
        print_section("Building Embeddings")
        
        if args.force:
            print(colorize("⚠️  Force rebuild enabled - all embeddings will be regenerated", Colors.WARNING))
        
        print("🔧 Building embeddings for knowledge base...")
        
        created = safe_execute(
            lambda: self.builder.build_embeddings(args.force),
            default_return=0
        )
        
        print(f"\n{colorize(f'✅ Created {created} new embeddings', Colors.GREEN)}")
    
    def cmd_generate(self, args):
        """Generate summaries for files based on mode."""
        print_section(f"Summary Generation Mode: {args.mode}")
        
        print(f"🔍 Identifying files needing summaries (mode: {colorize(args.mode, Colors.CYAN)})")
        
        if args.files:
            print(f"📎 Target files: {colorize(', '.join(args.files), Colors.CYAN)}")
        
        # Progress callback for user feedback
        def progress_callback(current, total, filename):
            progress_pct = (current / total) * 100
            print(f"📝 [{current:3d}/{total:3d}] ({progress_pct:5.1f}%) Processing: {colorize(filename, Colors.CYAN)}")
        
        # Start generation process
        print("\nStarting summary generation...")
        
        result = safe_execute(
            lambda: self.builder.generate_summaries(
                mode=args.mode,
                target_files=args.files,
                progress_callback=progress_callback
            ),
            default_return={}
        )
        
        if result:
            print(f"\n{colorize('✅ Generation completed successfully!', Colors.GREEN)}")
            print(f"\n📊 Generation Statistics:")
            print(f"   ⏱️  Duration: {result['duration_seconds']:.1f} seconds")
            print(f"   🔍 Mode: {result['mode']}")
            print(f"   📄 Files found: {result['files_found']}")
            print(f"   ✅ Files processed: {result['files_processed']}")
            print(f"   ❌ Files failed: {result['files_failed']}")
            
            if result['files_failed'] > 0:
                print(colorize(f"\n⚠️  {result['files_failed']} files failed to process. Check logs for details.", Colors.WARNING))
            
            if result['files_found'] == 0:
                print(colorize(f"\n✨ No files need summary generation in '{args.mode}' mode.", Colors.GREEN))
        else:
            print(colorize("\n❌ Generation failed. Check logs for details.", Colors.FAIL))
    
    def cmd_validate(self, args):
        """Validate summary quality and database consistency."""
        print_section("Summary Validation")
        
        print("🔍 Validating summary quality and database consistency...")
        
        result = safe_execute(self.builder.validate_summaries, default_return={})
        
        if not result:
            print(colorize("❌ Failed to validate summaries.", Colors.FAIL))
            return
        
        print(f"\n{colorize('📊 Validation Results:', Colors.GREEN)}")
        print(f"   📄 Total files: {result.get('total_files', 0)}")
        print(f"   ✅ Files with summaries: {result.get('files_with_summaries', 0)}")
        print(f"   ❌ Files missing summaries: {result.get('files_missing_summaries', 0)}")
        print(f"   📏 Files with short summaries: {result.get('files_with_short_summaries', 0)}")
        print(f"   📏 Files with long summaries: {result.get('files_with_long_summaries', 0)}")
        print(f"   🗑️  Orphaned database entries: {result.get('orphaned_database_entries', 0)}")
        
        issues = result.get('consistency_issues', [])
        if issues:
            print(f"\n{colorize('⚠️ Consistency Issues:', Colors.WARNING)}")
            for i, issue in enumerate(issues[:10], 1):  # Show first 10 issues
                print(f"   {i}. {issue}")
            
            if len(issues) > 10:
                print(f"   ... and {len(issues) - 10} more issues")
        else:
            print(f"\n{colorize('✅ No consistency issues found!', Colors.GREEN)}")
    
    def cmd_interactive(self, args):
        """Start interactive Q&A mode."""
        print_section("Interactive Q&A Mode")
        
        print(f"\n{colorize('Welcome to interactive Q&A mode!', Colors.GREEN)}")
        print(f"Type your questions and get answers from the knowledge base.")
        print(f"Commands: {colorize('/help', Colors.CYAN)} for help, {colorize('/exit', Colors.CYAN)} to quit")
        
        while True:
            try:
                print(f"\n{colorize('❓ Your question:', Colors.CYAN)} ", end='')
                question = input().strip()
                
                if not question:
                    continue
                
                if question.lower() in ['/exit', '/quit', '/q']:
                    print(colorize("\n👋 Goodbye!", Colors.GREEN))
                    break
                
                if question.lower() == '/help':
                    print(f"\n{colorize('Available commands:', Colors.CYAN)}")
                    print("  /help  - Show this help message")
                    print("  /exit  - Exit interactive mode")
                    print("  /stats - Show knowledge base statistics")
                    continue
                
                if question.lower() == '/stats':
                    self.cmd_stats(args)
                    continue
                
                # Answer the question
                print(f"\n🔍 Searching knowledge base...")
                
                result = safe_execute(
                    lambda: self.builder.answer_question(question),
                    default_return={}
                )
                
                if result and 'answer' in result:
                    print(f"\n{colorize('💡 Answer:', Colors.GREEN)}")
                    print(f"\n{result['answer']}")
                    
                    if result.get('source_files'):
                        print(f"\n{colorize('📚 Sources:', Colors.CYAN)} ", end='')
                        sources = [f['filename'] for f in result['source_files'][:3]]
                        print(', '.join(sources))
                else:
                    print(colorize("\n❌ Failed to generate answer.", Colors.FAIL))
                    
            except KeyboardInterrupt:
                print(colorize("\n\n👋 Goodbye!", Colors.GREEN))
                break
            except Exception as e:
                self.logger.error(f"Interactive mode error: {e}", exc_info=True)
                print(colorize(f"\n❌ Error: {e}", Colors.FAIL))
    
    def cmd_ingest(self, args):
        """Ingest documents and create markdown summaries."""
        print_section("Document Ingestion")
        
        # Initialize document ingester
        try:
            self.ingester = DocumentIngester(
                output_dir=args.output_dir,
                provider_name=args.provider
            )
        except Exception as e:
            print(colorize(f"❌ Failed to initialize ingester: {e}", Colors.FAIL))
            return
        
        path = Path(args.path)
        
        if path.is_file():
            # Process single file
            print(f"📄 Processing document: {colorize(path.name, Colors.CYAN)}")
            
            result = safe_execute(
                lambda: self.ingester.process_document(path, args.force),
                default_return={}
            )
            
            if result.get('status') == 'success':
                print(colorize(f"\n✅ Successfully processed!", Colors.GREEN))
                print(f"📝 Markdown saved to: {colorize(result['markdown_path'], Colors.CYAN)}")
            elif result.get('status') == 'skipped':
                print(colorize(f"\n⏭️  Skipped: {result.get('reason', 'unknown')}", Colors.WARNING))
            else:
                print(colorize(f"\n❌ Failed: {result.get('reason', 'unknown')}", Colors.FAIL))
        
        else:
            # Process directory
            print(f"📁 Processing directory: {colorize(str(path), Colors.CYAN)}")
            print(f"📝 Output directory: {colorize(args.output_dir, Colors.CYAN)}")
            
            if args.force:
                print(colorize("⚠️  Force mode enabled - all documents will be reprocessed", Colors.WARNING))
            
            print("\n🔍 Scanning for supported documents...")
            
            results = safe_execute(
                lambda: self.ingester.process_directory(path, not args.no_recursive, args.force),
                default_return={}
            )
            
            if results:
                print(f"\n{colorize('✅ Processing completed!', Colors.GREEN)}")
                print(f"\n📊 Processing Statistics:")
                print(f"   📄 Total found: {results.get('total_found', 0)}")
                print(f"   ✅ Processed: {results.get('processed', 0)}")
                print(f"   ⏭️  Skipped: {results.get('skipped', 0)}")
                print(f"   ❌ Failed: {results.get('failed', 0)}")
                
                if results.get('failed', 0) > 0:
                    print(colorize(f"\n⚠️  {results['failed']} documents failed. Check logs for details.", Colors.WARNING))
                
                # Show master index location
                index_path = Path(args.output_dir) / "index.md"
                print(f"\n📚 Master index: {colorize(str(index_path), Colors.CYAN)}")
            else:
                print(colorize("\n❌ Processing failed. Check logs for details.", Colors.FAIL))

def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Markdown Knowledge Base CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s build                             # Build knowledge base from current directory
  %(prog)s build ~/documents                 # Build from specific directory
  %(prog)s search "python"                   # Search for files mentioning 'python'
  %(prog)s ask "How do I use Git?"           # Ask a question
  %(prog)s interactive                       # Start interactive Q&A mode
  %(prog)s generate --mode missing           # Generate summaries for files without them
  %(prog)s generate --mode outdated          # Generate summaries for changed files
  %(prog)s generate --mode all               # Force regenerate all summaries
  %(prog)s validate                          # Validate summary quality and consistency
        """
    )
    
    # Global arguments
    parser.add_argument("-d", "--directory", default=".",
                       help="Base directory for markdown files (default: current directory)")
    parser.add_argument("--db-path", default="data/knowledge_base.json",
                       help="Path to the database file")
    parser.add_argument("--embeddings-cache", default="data/embeddings_cache.json",
                       help="Path to embeddings cache file")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--no-color", action="store_true",
                       help="Disable colored output")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build or update the knowledge base")
    build_parser.add_argument("-f", "--force-update", action="store_true",
                             help="Force re-processing of all files")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search files by keyword")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-c", "--case-sensitive", action="store_true",
                              help="Case sensitive search")
    
    # Semantic search command
    semantic_parser = subparsers.add_parser("semantic", help="Semantic search using AI")
    semantic_parser.add_argument("query", help="Search query")
    semantic_parser.add_argument("-k", "--top-k", type=int, default=5,
                                help="Number of results to return (default: 5)")
    semantic_parser.add_argument("-t", "--threshold", type=float, default=0.7,
                                help="Similarity threshold 0-1 (default: 0.7)")
    
    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question")
    ask_parser.add_argument("question", help="Your question")
    ask_parser.add_argument("-k", "--top-k", type=int, default=5,
                           help="Number of files to consider (default: 5)")
    ask_parser.add_argument("-t", "--threshold", type=float, default=0.6,
                           help="Similarity threshold 0-1 (default: 0.6)")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show knowledge base statistics")
    
    # Embeddings command
    embeddings_parser = subparsers.add_parser("embeddings", help="Build embeddings for semantic search")
    embeddings_parser.add_argument("-f", "--force", action="store_true",
                                  help="Force rebuild all embeddings")
    
    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive Q&A mode")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate summaries for files")
    generate_parser.add_argument("--mode", choices=["missing", "outdated", "all"], default="missing",
                                help="Generation mode: missing (files without summaries), outdated (changed files), all (force all)")
    generate_parser.add_argument("--files", nargs="*",
                                help="Specific files or patterns to target")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate summary quality and database consistency")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest PDFs/EPUBs and create markdown summaries")
    ingest_parser.add_argument("path", help="File or directory to ingest")
    ingest_parser.add_argument("--output-dir", default="document_summaries",
                              help="Output directory for markdown summaries (default: document_summaries)")
    ingest_parser.add_argument("--provider", choices=['openai', 'gemini', 'claude'],
                              help="API provider to use (auto-detect if not specified)")
    ingest_parser.add_argument("-f", "--force", action="store_true",
                              help="Force reprocessing of already processed files")
    ingest_parser.add_argument("--no-recursive", action="store_true",
                              help="Don't process subdirectories")
    
    return parser

def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Disable colors if requested
    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    # Show banner
    if not args.no_color and args.command:
        print_banner()
    
    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 0
    
    # Initialize CLI
    cli = KnowledgeBaseCLI()
    
    # Initialize builder (not needed for ingest command)
    if args.command != 'ingest':
        if not cli.initialize_builder(args):
            return 1
    
    # Execute command
    command_map = {
        'build': cli.cmd_build,
        'search': cli.cmd_search,
        'semantic': cli.cmd_semantic_search,
        'ask': cli.cmd_ask,
        'stats': cli.cmd_stats,
        'embeddings': cli.cmd_embeddings,
        'interactive': cli.cmd_interactive,
        'generate': cli.cmd_generate,
        'validate': cli.cmd_validate,
        'ingest': cli.cmd_ingest,
    }
    
    try:
        command_func = command_map.get(args.command)
        if command_func:
            command_func(args)
        else:
            print(colorize(f"❌ Unknown command: {args.command}", Colors.FAIL))
            return 1
    except KeyboardInterrupt:
        print(colorize("\n\n⏹️  Operation cancelled by user", Colors.WARNING))
        return 1
    except Exception as e:
        logging.error(f"Command '{args.command}' failed: {e}", exc_info=True)
        print(colorize(f"\n❌ Error: {e}", Colors.FAIL))
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())