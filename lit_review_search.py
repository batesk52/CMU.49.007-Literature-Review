#!/usr/bin/env python3
"""
Simple helper script for searching your literature review knowledge base.
This makes it easier to search without typing long commands.
"""

import sys
import subprocess
import os

# Configuration - paths to your knowledge base
DOCS_DIR = "document_summaries"
DB_PATH = "document_summaries/data/knowledge_base.json"
CACHE_PATH = "data/embeddings_cache.json"

def print_help():
    print("""
📚 Literature Review Search Tool
================================

Usage:
    python lit_review_search.py search "keyword"          # Keyword search
    python lit_review_search.py find "learning"           # Semantic search (smart)
    python lit_review_search.py ask "your question?"      # Ask a question
    python lit_review_search.py chat                      # Interactive mode
    python lit_review_search.py stats                     # View statistics
    python lit_review_search.py build                     # Build/rebuild knowledge base
    python lit_review_search.py help                      # Show this help

Examples:
    python lit_review_search.py search "dopamine"
    python lit_review_search.py find "neural plasticity mechanisms"
    python lit_review_search.py ask "What are the mechanisms of learning?"
    """)

def run_command(cmd_parts):
    """Run a kb_cli.py command with proper paths."""
    base_cmd = [
        "python", "kb_cli.py",
        "-d", DOCS_DIR,
        "--db-path", DB_PATH,
        "--embeddings-cache", CACHE_PATH
    ]
    
    full_cmd = base_cmd + cmd_parts
    
    # Run the command
    try:
        subprocess.run(full_cmd)
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command in ["help", "-h", "--help"]:
        print_help()
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ Please provide a search term")
            print("Example: python lit_review_search.py search 'learning'")
            sys.exit(1)
        query = " ".join(sys.argv[2:])
        run_command(["search", query])
    
    elif command == "find":
        if len(sys.argv) < 3:
            print("❌ Please provide a search term")
            print("Example: python lit_review_search.py find 'neural mechanisms'")
            sys.exit(1)
        query = " ".join(sys.argv[2:])
        # Use lower threshold for semantic search
        run_command(["semantic", "-t", "0.4", query])
    
    elif command == "ask":
        if len(sys.argv) < 3:
            print("❌ Please provide a question")
            print("Example: python lit_review_search.py ask 'What is the role of dopamine?'")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        # Use lower threshold for Q&A to find more relevant documents
        run_command(["ask", "-t", "0.4", question])
    
    elif command == "chat":
        run_command(["interactive"])
    
    elif command == "stats":
        run_command(["stats"])
    
    elif command == "build":
        print("🔨 Building knowledge base...")
        run_command(["build"])
        print("\n🔨 Building embeddings...")
        run_command(["embeddings"])
    
    else:
        print(f"❌ Unknown command: {command}")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()