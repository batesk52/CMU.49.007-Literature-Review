# Knowledge Base System - Usage Guide

A comprehensive guide for using the AI-Powered Markdown Knowledge Base System.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
- [API Documentation](#api-documentation)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

The Knowledge Base System is an intelligent tool that:
- Scans directories for markdown files
- Generates AI-powered summaries
- Provides semantic and keyword search
- Answers questions using your documentation
- Maintains an efficient JSON database

## Installation

### Prerequisites
- Python 3.8 or higher
- OpenAI API key
- pip package manager

### Setup Steps

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=sk-...  # Your OpenAI API key (required)
LOG_LEVEL=INFO         # Optional: DEBUG, INFO, WARNING, ERROR
```

3. **Verify Installation**
```bash
python kb_cli.py --help
```

## Configuration

### Environment Variables

The system uses a centralized configuration management system. Copy `.env.example` to `.env` and configure:

#### Required (at least one):
- `OPENAI_API_KEY`: OpenAI API key (recommended)
- `GEMINI_API_KEY`: Google Gemini API key (alternative)
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY`: Claude API key (alternative)

#### Optional Settings:
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `OPENAI_MODEL`: GPT model to use (default: gpt-4)
- `EMBEDDING_MODEL`: Embedding model (default: text-embedding-3-small)

### Configuration Management

The system includes a configuration module with validation:

```bash
# Validate your configuration
python config.py validate

# Show current configuration
python config.py show

# Save configuration to file
python config.py save my_config.json
```

### Data Storage
The system stores data in:
- `data/knowledge_base.json` - Main database
- `data/embeddings_cache.json` - Cached embeddings
- `logs/` - Application and error logs
- All paths are automatically created if they don't exist

## Quick Start

### 1. Build Your Knowledge Base
```bash
# Scan and process markdown files
python kb_cli.py build ./docs

# Output:
# ╔══════════════════════════════════════════╗
# ║     Knowledge Base System v1.0           ║
# ╚══════════════════════════════════════════╝
# 
# 🔍 Scanning directory: ./docs
# ✓ Found 15 markdown files
# 
# 📝 Processing files...
# ✓ Processed 10 new/modified files
# ⏭️  Skipped 5 unchanged files
# 
# 🧮 Building embeddings...
# ✓ Generated embeddings for semantic search
# 
# ✅ Knowledge base ready!
```

### 2. Search Your Documents
```bash
# Keyword search
python kb_cli.py search "API configuration"

# Semantic search
python kb_cli.py semantic "how to handle errors"
```

### 3. Ask Questions
```bash
# Single question
python kb_cli.py ask "What are the main components?"

# Interactive mode
python kb_cli.py interactive
```

## Detailed Usage

### Building the Knowledge Base

The build process involves:
1. Scanning for markdown files
2. Generating summaries
3. Creating embeddings
4. Updating the database

```bash
# Basic build
python knowledge_base_builder.py build /path/to/docs

# With CLI (recommended)
python kb_cli.py build ./documentation

# Build only embeddings
python knowledge_base_builder.py build-embeddings
```

**Options:**
- Path: Directory to scan (default: current directory)
- Recursive: Automatically scans subdirectories
- Incremental: Only processes new/changed files

### Search Features

#### Keyword Search
Find files containing specific terms:
```bash
# Simple search
python kb_cli.py search "docker"

# Multi-word search
python kb_cli.py search "environment variables configuration"
```

#### Semantic Search
Find conceptually related content:
```bash
# Basic semantic search
python kb_cli.py semantic "best practices"

# With custom parameters
python knowledge_base_builder.py semantic-search "testing strategies" --top-k 10
```

**Parameters:**
- `--top-k`: Number of results (default: 5)
- `--threshold`: Similarity threshold 0-1 (default: 0.7)

### Question Answering

#### Single Questions
```bash
python kb_cli.py ask "How do I configure logging?"

# Response includes:
# - Synthesized answer
# - Source citations
# - Confidence score
```

#### Interactive Mode
```bash
python kb_cli.py interactive

# Features:
# - Continuous Q&A session
# - Context retention
# - Source tracking
# - Special commands:
#   /help - Show available commands
#   /stats - Display knowledge base statistics
#   /clear - Clear screen
#   /exit or /quit - Exit interactive mode
# - Type 'exit' or 'quit' to end session
```

### Database Management

#### View Statistics
```bash
python kb_cli.py stats

# Shows:
# - Total files indexed
# - Database size
# - Last update time
# - Embeddings status
```

#### Clean Database
```bash
# Remove entries for deleted files
python knowledge_base_builder.py clean

# Rebuild from scratch
rm data/knowledge_base.json
python kb_cli.py build ./docs
```

## API Documentation

### Python API

#### KnowledgeBaseBuilder
```python
from knowledge_base_builder import KnowledgeBaseBuilder

# Initialize
kb = KnowledgeBaseBuilder()

# Build knowledge base
kb.build_knowledge_base("/path/to/docs")

# Search operations
keyword_results = kb.search_files("query")
semantic_results = kb.semantic_search("query", top_k=5)

# Get statistics
stats = kb.get_statistics()
```

#### MarkdownScanner
```python
from markdown_scanner import MarkdownScanner

scanner = MarkdownScanner()

# Scan directory
files = scanner.scan_directory("/docs")
# Returns: [(absolute_path, relative_path), ...]

# With exclusions
scanner.exclude_patterns.append("drafts/")
files = scanner.scan_directory("/docs")
```

#### MarkdownSummarizer
```python
from markdown_summarizer import MarkdownSummarizer

summarizer = MarkdownSummarizer()

# Summarize content
summary = summarizer.summarize(content, file_path)

# Summarize file
summary = summarizer.summarize_file(Path("doc.md"))
```

#### SemanticSearch
```python
from semantic_search import SemanticSearch
from knowledge_database import KnowledgeDatabase

db = KnowledgeDatabase("data/knowledge_base.json")
search = SemanticSearch(db)

# Search with custom parameters
results = search.search(
    query="error handling",
    top_k=10,
    threshold=0.6
)

# Build embeddings for all files
search.build_embeddings_for_database()
```

#### QuestionAnswerer
```python
from question_answerer import QuestionAnswerer

qa = QuestionAnswerer(database)

# Get answer with sources
answer = qa.answer_question("How to setup?")
print(answer["answer"])
print(answer["sources"])
print(answer["confidence"])
```

### CLI Commands Reference

#### kb_cli.py
```bash
# Build knowledge base
kb_cli.py build [PATH]
  --force              Force re-processing of all files

# Search commands
kb_cli.py search QUERY
  --case-sensitive     Enable case-sensitive search

kb_cli.py semantic QUERY
  --top-k N           Number of results (default: 5)
  --threshold F       Similarity threshold 0-1 (default: 0.7)

# Q&A commands
kb_cli.py ask QUESTION
  --top-k N           Number of sources to use (default: 5)

kb_cli.py interactive
  # Special commands: /help, /stats, /clear, /exit

# Management
kb_cli.py stats
  # Shows files, size, last update, provider info

kb_cli.py embeddings
  --force             Rebuild all embeddings

# Global options
  --directory PATH    Base directory for markdown files
  --db-path PATH     Path to knowledge base JSON
  --verbose          Enable verbose output

# Help
kb_cli.py --help
kb_cli.py COMMAND --help
```

#### knowledge_base_builder.py
```bash
# Primary commands
knowledge_base_builder.py build [PATH]
knowledge_base_builder.py search QUERY
knowledge_base_builder.py semantic-search QUERY [--top-k N]
knowledge_base_builder.py build-embeddings
knowledge_base_builder.py stats
```

## Examples

### Example 1: Building Documentation KB
```bash
# Initial setup
export OPENAI_API_KEY=sk-...
pip install -r requirements.txt

# Build knowledge base
python kb_cli.py build ./project-docs

# Ask about setup
python kb_cli.py ask "What are the installation requirements?"
```

### Example 2: Research Paper Analysis
```bash
# Build KB from papers
python kb_cli.py build ./research-papers

# Find related work
python kb_cli.py semantic "machine learning optimization techniques"

# Interactive exploration
python kb_cli.py interactive
> What approaches are used for hyperparameter tuning?
> Which papers discuss neural architecture search?
```

### Example 3: Code Documentation Search
```bash
# Build from code docs
python kb_cli.py build ./src/docs

# Find implementation details
python kb_cli.py search "authentication middleware"

# Ask specific questions
python kb_cli.py ask "How is user session management implemented?"
```

## Troubleshooting

### Common Issues

#### 1. OpenAI API Key Error
```
Error: OPENAI_API_KEY environment variable is required
```
**Solution:** Create `.env` file with valid API key

#### 2. Rate Limiting
```
Error: Rate limit exceeded
```
**Solution:** System includes automatic retry with backoff. For large repositories, initial build may take time.

#### 3. Memory Issues
```
Error: Out of memory
```
**Solution:** 
- Process smaller directories
- Increase system memory
- Files >15KB are automatically truncated

#### 4. No Results Found
**Solutions:**
- Rebuild embeddings: `python kb_cli.py embeddings`
- Use semantic search instead of keyword
- Check file indexing: `python kb_cli.py stats`

#### 5. Import Errors
```
ModuleNotFoundError: No module named 'openai'
```
**Solution:** Install dependencies: `pip install -r requirements.txt`

### Debug Mode
Enable detailed logging:
```bash
# Set in .env
LOG_LEVEL=DEBUG

# Or via environment
LOG_LEVEL=DEBUG python kb_cli.py build ./docs
```

### Log Files
Check logs for detailed error information:
```bash
# Application logs
tail -f logs/kb_app.log

# Error logs
tail -f logs/kb_errors.log
```

### Performance Tips

1. **Initial Build**: First build processes all files, subsequent builds only changed files
2. **Large Repositories**: Build in batches by subdirectory
3. **Search Performance**: Semantic search is cached after first embedding generation
4. **API Costs**: Monitor OpenAI usage, especially for large repositories

## Advanced Usage

### Custom Exclusions
Edit `markdown_scanner.py` to modify default exclusions:
```python
self.exclude_patterns = [
    '.git/', 'node_modules/', '.venv/',
    'your_custom_pattern/'
]
```

### Multi-Provider Support (V2)
Use V2 modules for multiple AI providers:
```python
from markdown_summarizer_v2 import MarkdownSummarizer
from semantic_search_v2 import SemanticSearch

# Supports OpenAI, Gemini, Claude
summarizer = MarkdownSummarizer(provider="gemini")
```

### Batch Processing
Process multiple directories:
```bash
for dir in docs1 docs2 docs3; do
    python kb_cli.py build $dir
done
```

### Integration Examples
```python
# Web API integration
from flask import Flask, jsonify
from knowledge_base_builder import KnowledgeBaseBuilder

app = Flask(__name__)
kb = KnowledgeBaseBuilder()

@app.route('/search/<query>')
def search(query):
    results = kb.semantic_search(query)
    return jsonify(results)
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review log files
3. Ensure all dependencies are installed
4. Verify API key permissions