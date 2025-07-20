# Knowledge Base System - API Reference

Complete API documentation for the AI-Powered Markdown Knowledge Base System.

## Table of Contents
- [Core Classes](#core-classes)
- [Data Models](#data-models)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Advanced Features](#advanced-features)

## Core Classes

### KnowledgeBaseBuilder

Main orchestrator class that integrates all system components.

```python
class KnowledgeBaseBuilder(
    base_directory: Optional[str] = None,
    db_path: Optional[str] = None,
    embeddings_cache_path: Optional[str] = None,
    force_update: bool = False
)
```

#### Parameters
- `base_directory` (str, optional): Root directory to scan for markdown files
- `db_path` (str, optional): Path to JSON database file
- `embeddings_cache_path` (str, optional): Path to embeddings cache
- `force_update` (bool): Force re-processing of all files

#### Methods

##### build_knowledge_base(directory: Optional[str] = None) ’ Dict[str, Any]
Build or update the knowledge base from markdown files.

```python
kb = KnowledgeBaseBuilder()
result = kb.build_knowledge_base("/path/to/docs")
# Returns: {'processed': 10, 'total': 15, 'errors': []}
```

##### search_files(query: str) ’ List[Dict[str, Any]]
Perform keyword search across file summaries.

```python
results = kb.search_files("configuration")
# Returns: [{'file_path': '...', 'summary': '...', 'score': 0.95}, ...]
```

##### semantic_search(query: str, top_k: int = 5, threshold: float = 0.7) ’ List[Dict[str, Any]]
Perform semantic search using embeddings.

```python
results = kb.semantic_search("error handling", top_k=10)
# Returns: [{'file_path': '...', 'summary': '...', 'similarity': 0.89}, ...]
```

##### get_statistics() ’ Dict[str, Any]
Get database statistics.

```python
stats = kb.get_statistics()
# Returns: {'total_files': 50, 'total_size': 1234567, 'last_updated': '...'}
```

### MarkdownScanner

Discovers markdown files in directory trees.

```python
class MarkdownScanner(base_directory: str = ".")
```

#### Methods

##### scan_directory(directory: Optional[str] = None) ’ List[Tuple[str, str]]
Scan directory for markdown files.

```python
scanner = MarkdownScanner("/docs")
files = scanner.scan_directory()
# Returns: [('/abs/path/file.md', 'relative/path/file.md'), ...]
```

##### is_excluded(path: Path) ’ bool
Check if path matches exclusion patterns.

```python
excluded = scanner.is_excluded(Path("node_modules/readme.md"))
# Returns: True
```

#### Properties
- `exclude_patterns`: List of patterns to exclude (default: ['.git/', 'node_modules/', etc.])
- `markdown_extensions`: Supported extensions (default: ['.md', '.markdown'])

### MarkdownSummarizer

Generates AI-powered summaries of markdown content.

```python
class MarkdownSummarizer()
```

#### Methods

##### summarize(content: str, file_path: Optional[Path] = None) ’ str
Generate summary of markdown content.

```python
summarizer = MarkdownSummarizer()
summary = summarizer.summarize(content, Path("doc.md"))
# Returns: "This document describes the API endpoints for..."
```

##### summarize_file(file_path: Path) ’ str
Read and summarize a markdown file.

```python
summary = summarizer.summarize_file(Path("/docs/api.md"))
```

##### read_markdown_file(file_path: Path) ’ str
Read markdown file with encoding detection.

```python
content = summarizer.read_markdown_file(Path("file.md"))
```

#### Configuration
- `max_content_length`: Maximum characters before truncation (default: 15000)
- `model`: OpenAI model to use (default: "gpt-4")
- `max_retries`: API retry attempts (default: 3)

### KnowledgeDatabase

JSON-based database for storing file metadata and summaries.

```python
class KnowledgeDatabase(db_path: str = "data/knowledge_base.json")
```

#### Methods

##### update_file(file_path: str, summary: str, content_length: int, file_hash: str) ’ None
Add or update file entry.

```python
db = KnowledgeDatabase()
db.update_file(
    "/path/to/file.md",
    "Summary text...",
    1234,
    "md5hash"
)
```

##### search(query: str) ’ List[Dict[str, Any]]
Search files by keyword.

```python
results = db.search("authentication")
# Returns: [{'file_path': '...', 'summary': '...', 'relevance': 0.8}, ...]
```

##### get_file_info(file_path: str) ’ Optional[Dict[str, Any]]
Get information for specific file.

```python
info = db.get_file_info("/path/to/file.md")
# Returns: {'summary': '...', 'last_modified': '...', 'content_length': 1234}
```

##### get_all_files() ’ List[Dict[str, Any]]
Get all file entries.

```python
all_files = db.get_all_files()
```

##### remove_missing_files() ’ int
Clean database of deleted files.

```python
removed_count = db.remove_missing_files()
```

##### get_statistics() ’ Dict[str, Any]
Get database statistics.

```python
stats = db.get_statistics()
# Returns: {'total_files': 50, 'total_size': 1234567, ...}
```

### SemanticSearch

Provides embedding-based semantic search capabilities.

```python
class SemanticSearch(
    database: KnowledgeDatabase,
    embeddings_cache_path: Optional[str] = None
)
```

#### Methods

##### search(query: str, top_k: int = 5, threshold: float = 0.7) ’ List[Dict[str, Any]]
Search using semantic similarity.

```python
search = SemanticSearch(database)
results = search.search("best practices", top_k=10, threshold=0.6)
# Returns: [{'file_path': '...', 'summary': '...', 'similarity': 0.92}, ...]
```

##### get_embedding(text: str) ’ List[float]
Get embedding vector for text.

```python
embedding = search.get_embedding("sample text")
# Returns: [0.123, -0.456, ...] (1536-dimensional)
```

##### build_embeddings_for_database() ’ None
Generate embeddings for all database entries.

```python
search.build_embeddings_for_database()
```

##### compute_similarity(embedding1: List[float], embedding2: List[float]) ’ float
Calculate cosine similarity between embeddings.

```python
similarity = search.compute_similarity(emb1, emb2)
# Returns: 0.89 (similarity score 0-1)
```

#### Configuration
- `embedding_model`: Model name (default: "text-embedding-3-small")
- `embedding_dimension`: Vector size (default: 1536)

### QuestionAnswerer

Synthesizes answers from relevant documents.

```python
class QuestionAnswerer(
    database: KnowledgeDatabase,
    embeddings_cache_path: Optional[str] = None
)
```

#### Methods

##### answer_question(query: str, top_k: int = 5) ’ Dict[str, Any]
Generate answer with sources.

```python
qa = QuestionAnswerer(database)
result = qa.answer_question("How to configure logging?")
# Returns: {
#   'answer': 'To configure logging...',
#   'sources': ['/docs/logging.md', '/docs/config.md'],
#   'confidence': 0.85
# }
```

##### find_relevant_files(query: str, top_k: int = 5, similarity_threshold: float = 0.7) ’ List[Dict[str, Any]]
Find files relevant to query.

```python
files = qa.find_relevant_files("error handling", top_k=10)
```

##### prepare_context(relevant_files: List[Dict[str, Any]], max_context_length: int = 12000) ’ str
Prepare context from relevant files.

```python
context = qa.prepare_context(relevant_files)
```

##### synthesize_answer(query: str, context: str, sources: List[str]) ’ str
Generate answer using GPT.

```python
answer = qa.synthesize_answer(query, context, sources)
```

##### interactive_qa_session() ’ None
Start interactive Q&A mode.

```python
qa.interactive_qa_session()
# Enters interactive prompt
```

### ErrorHandler

Centralized error handling and logging.

```python
class KnowledgeBaseLogger(name: str = "knowledge_base")
```

#### Methods

##### setup_logging(log_level: str = "INFO", log_dir: str = "logs") ’ None
Configure logging system.

```python
logger = KnowledgeBaseLogger()
logger.setup_logging("DEBUG", "custom_logs")
```

##### log_error(error: Exception, context: Optional[str] = None) ’ None
Log error with context.

```python
try:
    # operation
except Exception as e:
    logger.log_error(e, "Failed to process file")
```

#### Decorators

##### @with_error_handling
Decorator for automatic error handling.

```python
@with_error_handling
def risky_operation():
    # code that might fail
```

##### @validate_environment
Ensure required environment variables exist.

```python
@validate_environment(["OPENAI_API_KEY"])
def api_operation():
    # requires API key
```

## Data Models

### Database Entry Schema
```json
{
  "metadata": {
    "version": "1.0",
    "created_at": "2023-12-01T10:00:00Z",
    "last_updated": "2023-12-01T12:00:00Z"
  },
  "files": {
    "/absolute/path/to/file.md": {
      "relative_path": "docs/file.md",
      "summary": "This file contains...",
      "content_length": 1234,
      "last_modified": "2023-12-01T10:00:00",
      "file_hash": "md5hash"
    }
  }
}
```

### Embeddings Cache Schema
```json
{
  "metadata": {
    "model": "text-embedding-3-small",
    "dimension": 1536,
    "created_at": "2023-12-01T10:00:00Z"
  },
  "embeddings": {
    "/path/to/file.md": {
      "embedding": [0.123, -0.456, ...],
      "model": "text-embedding-3-small",
      "created_at": "2023-12-01T10:00:00"
    }
  }
}
```

### Search Result Schema
```python
{
    "file_path": "/absolute/path/to/file.md",
    "relative_path": "docs/file.md",
    "summary": "Brief summary of content...",
    "similarity": 0.89,  # For semantic search
    "relevance": 0.75,   # For keyword search
    "content_length": 1234,
    "last_modified": "2023-12-01T10:00:00"
}
```

### Question Answer Schema
```python
{
    "answer": "Based on the documentation...",
    "sources": [
        "/docs/file1.md",
        "/docs/file2.md"
    ],
    "confidence": 0.85,
    "relevant_files": [
        {
            "file_path": "...",
            "summary": "...",
            "similarity": 0.92
        }
    ]
}
```

## CLI Reference

### kb_cli.py Commands

#### build
Build or update knowledge base.
```bash
kb_cli.py build [PATH]
  --force    Force re-processing of all files
```

#### search
Keyword search in summaries.
```bash
kb_cli.py search QUERY
  --limit N  Maximum results (default: 10)
```

#### semantic
Semantic search using embeddings.
```bash
kb_cli.py semantic QUERY
  --top-k N      Number of results (default: 5)
  --threshold F  Similarity threshold (default: 0.7)
```

#### ask
Ask a question.
```bash
kb_cli.py ask QUESTION
  --top-k N  Number of sources (default: 5)
```

#### interactive
Enter interactive Q&A mode.
```bash
kb_cli.py interactive
```

#### stats
Show database statistics.
```bash
kb_cli.py stats
  --verbose  Show detailed statistics
```

#### embeddings
Build/rebuild embeddings cache.
```bash
kb_cli.py embeddings
  --force  Rebuild all embeddings
```

### knowledge_base_builder.py Commands

#### build
```bash
python knowledge_base_builder.py build [DIRECTORY]
```

#### search
```bash
python knowledge_base_builder.py search "query"
```

#### semantic-search
```bash
python knowledge_base_builder.py semantic-search "query" --top-k 10
```

#### build-embeddings
```bash
python knowledge_base_builder.py build-embeddings
```

#### stats
```bash
python knowledge_base_builder.py stats
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
OPENAI_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-small
MAX_CONTENT_LENGTH=15000
MAX_RETRIES=3
RETRY_DELAY=1
```

### Configuration Class (config.py)

```python
from config import get_config

config = get_config()

# Access configuration
api_key = config.api.openai_api_key
model = config.api.openai_model
log_level = config.logging.level
db_path = config.paths.knowledge_base_path
```

### Custom Configuration

```python
# Override defaults
import os
os.environ['OPENAI_MODEL'] = 'gpt-3.5-turbo'
os.environ['MAX_CONTENT_LENGTH'] = '20000'
```

## Error Handling

### Exception Types

```python
class KnowledgeBaseError(Exception):
    """Base exception for knowledge base errors"""

class DatabaseError(KnowledgeBaseError):
    """Database operation errors"""

class APIError(KnowledgeBaseError):
    """External API errors"""

class ValidationError(KnowledgeBaseError):
    """Input validation errors"""
```

### Error Handling Patterns

```python
# Using error handler
from error_handler import KnowledgeBaseLogger, with_error_handling

logger = KnowledgeBaseLogger(__name__)

@with_error_handling
def process_file(path):
    # Automatic error logging
    pass

# Manual error handling
try:
    result = api_call()
except APIError as e:
    logger.log_error(e, "API call failed")
    # Handle gracefully
```

### Retry Logic

```python
# Built-in retry for API calls
from error_handler import safe_api_call

@safe_api_call(max_retries=3, delay=1)
def call_openai():
    # Will retry on failure
    pass
```

## Advanced Features

### Multi-Provider Support (V2 Modules)

```python
# Using alternative AI providers
from markdown_summarizer_v2 import MarkdownSummarizer
from api_providers import APIProvider

# OpenAI (default)
summarizer = MarkdownSummarizer(provider=APIProvider.OPENAI)

# Google Gemini
summarizer = MarkdownSummarizer(provider=APIProvider.GEMINI)

# Anthropic Claude
summarizer = MarkdownSummarizer(provider=APIProvider.CLAUDE)
```

### Custom Preprocessing

```python
# Add custom preprocessing
class CustomSummarizer(MarkdownSummarizer):
    def preprocess_content(self, content: str) -> str:
        # Custom logic
        content = super().preprocess_content(content)
        # Additional processing
        return content
```

### Batch Operations

```python
# Process multiple directories
kb = KnowledgeBaseBuilder()
for directory in directories:
    kb.build_knowledge_base(directory)
```

### Custom Search Filters

```python
# Filter search results
results = kb.search_files("query")
filtered = [r for r in results if r['content_length'] > 1000]
```

### Integration Hooks

```python
# Add callbacks
class CustomBuilder(KnowledgeBaseBuilder):
    def on_file_processed(self, file_path: str, summary: str):
        # Custom logic after each file
        super().on_file_processed(file_path, summary)
        # Send notification, update UI, etc.
```

### Performance Optimization

```python
# Parallel processing
from concurrent.futures import ThreadPoolExecutor

def process_files_parallel(files):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_file, f) for f in files]
        results = [f.result() for f in futures]
```

## Best Practices

1. **API Key Security**: Never commit API keys to version control
2. **Error Handling**: Always wrap API calls in try-except blocks
3. **Rate Limiting**: Respect API rate limits with built-in retry logic
4. **Resource Management**: Close database connections properly
5. **Logging**: Use appropriate log levels for debugging
6. **Testing**: Run test suite before deploying changes
7. **Documentation**: Keep summaries focused and concise
8. **Performance**: Cache embeddings to reduce API calls