# CMU Literature Review & Knowledge Base System

This repository contains a comprehensive suite of tools for academic research, including an AI-powered document ingestion and knowledge base system for processing literature and audio files.

## 🎯 Main Features

### 1. **AI-Powered Document-to-Knowledge Base System** (UPDATED!)
Transform your collection of PDFs, e-books, and other documents into searchable markdown summaries, then build an intelligent knowledge base with natural language Q&A capabilities.

**Key Features:**
- 📚 **Document Ingestion**: Automatically processes PDFs, EPUBs, and other document formats
- 🤖 **AI-Powered Summaries**: Generates comprehensive markdown summaries with navigation aids
- 📁 **Organized Storage**: Creates structured directory layout for easy browsing
- 🔍 **Smart Discovery**: Scans directories for supported document types
- 🔎 **Semantic Search**: Find relevant documents using meaning-based search
- 💬 **Natural Language Q&A**: Ask questions and get synthesized answers from your documentation
- 🗄️ **Efficient Storage**: JSON-based database with embeddings cache
- 🖥️ **CLI Interface**: Easy-to-use command-line tools
- ⚙️ **Multi-Provider Support**: Works with OpenAI, Google Gemini, or Anthropic Claude APIs

### 2. Audio to Notion Processor
Transcribes MP3 files using OpenAI Whisper and creates structured Notion pages with summaries.

### 3. Zotero to Anki Converter  
Converts Zotero annotations to Anki flashcards using AI-generated question-answer pairs.

### 4. Paper Summarizer
Extracts and summarizes academic papers into a structured database.

## 🚀 Quick Start: Complete Workflow

### Prerequisites
- Python 3.8+
- API key for one of: OpenAI, Google Gemini, or Anthropic Claude

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Create configuration file
cp .env.example .env
# Edit .env and add your API key (see step 1 below)
```

### 🎯 Quick Start (If You Already Have a Knowledge Base)
If you've already built your knowledge base and just want to search:
```bas python lit_review_search.py find "learningh
# Use the helper script (automatically handles paths)
python lit_review_search.py search "dopamine"         # Keyword search
python lit_review_search.py find "neural mechanisms"  # Semantic search  
python lit_review_search.py ask "What role does dopamine play?"  # Q&A
python lit_review_search.py chat                      # Interactive mode
```

## 📖 Complete Example Workflow

Here's how to use the system from start to finish with a directory of PDFs and documents:

### **Step 1: Setup Your API Key**
```bash
# Copy the example configuration file
cp .env.example .env

# Edit .env and add ONE of these API keys:
# For OpenAI (recommended):
OPENAI_API_KEY=sk-your_actual_openai_key_here

# OR for Google Gemini (free tier available):
GEMINI_API_KEY=your_gemini_key_here

# OR for Anthropic Claude:
CLAUDE_API_KEY=your_claude_key_here
```

### **Step 2: Ingest Documents (PDFs, EPUBs) → Create Markdown Summaries**
This is the NEW feature! Convert your documents into searchable markdown summaries:

```bash
# Process all PDFs, EPUBs, and documents in a directory
python kb_cli.py ingest /path/to/your/documents

# Example: Process a research library
python kb_cli.py ingest ~/Documents/Research/Papers
python kb_cli.py ingest /mnt/c/Users/Karl/Downloads/zotero-test/KB4

# Force reprocess already-processed files
python kb_cli.py ingest ~/Documents/PDFs --force

# Process a single document
python kb_cli.py ingest ~/Documents/important-paper.pdf
```

**What this does:**
- Finds all PDFs, EPUBs, etc. in the directory
- Extracts text content from each document
- Uses AI to generate comprehensive markdown summaries
- Saves organized summaries in `document_summaries/` directory
- Creates master index and metadata tracking

### **Step 3: Build Knowledge Base from Generated Summaries**
Now build a searchable knowledge base from your markdown summaries:

```bash
# Build knowledge base from the generated markdown summaries
python kb_cli.py -d document_summaries build

# IMPORTANT: After building, note where your database is saved!
# Default location: document_summaries/data/knowledge_base.json
# You'll need this path for all search and query commands

# Or build from any directory with markdown files
python kb_cli.py -d ~/Documents/my-notes build
python kb_cli.py -d ~/Projects/documentation build
```

### **Step 4: Search and Query Your Knowledge Base**
Now you can search through your document summaries and get answers:

**IMPORTANT: Database Path Specification**
When using `kb_cli.py`, you MUST specify the database path or it will create a new empty database:

```bash
# ❌ WRONG - This creates a new empty database
python kb_cli.py -d document_summaries search "machine learning"

# ✅ CORRECT - This uses your existing knowledge base
python kb_cli.py -d document_summaries --db-path document_summaries/data/knowledge_base.json search "machine learning"
```

**Option 1: Using the Helper Script (Recommended - Easier!)**
```bash
# The lit_review_search.py script automatically sets all paths correctly
python lit_review_search.py search "machine learning"      # Keyword search
python lit_review_search.py find "neural networks"         # Semantic search
python lit_review_search.py ask "What does this research say about deep learning?"
python lit_review_search.py chat                          # Interactive mode
```

**Option 2: Using kb_cli.py Directly (Full Commands)**
```bash
# Keyword search for documents
python kb_cli.py -d document_summaries --db-path document_summaries/data/knowledge_base.json search "machine learning"

# Semantic search using AI embeddings (use -t flag for threshold)
python kb_cli.py -d document_summaries --db-path document_summaries/data/knowledge_base.json semantic -t 0.5 "neural networks"

# Ask natural language questions about your documents
python kb_cli.py -d document_summaries --db-path document_summaries/data/knowledge_base.json ask -t 0.4 "What does this research say about deep learning?"

# Interactive mode for multiple questions
python kb_cli.py -d document_summaries --db-path document_summaries/data/knowledge_base.json interactive
```

### **Step 5: Advanced Features**

#### **Generation Mode: Auto-Create Missing Summaries**
For existing markdown files, auto-generate summaries:
```bash
# Generate summaries for markdown files that don't have them yet
python kb_cli.py -d document_summaries generate --mode missing

# Update summaries for files that have changed
python kb_cli.py -d document_summaries generate --mode outdated

# Validate your summary quality and database consistency
python kb_cli.py -d document_summaries validate
```

#### **Monitor and Manage**
```bash
# Get database statistics
python kb_cli.py -d document_summaries stats

# Build embeddings for semantic search
python kb_cli.py -d document_summaries embeddings

# Rebuild embeddings if needed
python kb_cli.py -d document_summaries embeddings --force
```

## 🎯 Real-World Example: Complete Workflow

### Example 1: Processing a Neuroscience Research Library

Here's an actual example of processing 15 neuroscience PDFs from a research directory:

```bash
# 1. Setup (one time) - Using OpenAI for better rate limits
cp .env.example .env
# Add your OPENAI_API_KEY=sk-your_key_here to .env

# 2. Ingest neuroscience papers
python kb_cli.py ingest "/mnt/d/_sandbox/Lit_review/79.015 Neuroscience"

# Output:
# ════════════════════════════════════════════════════════════
#   Document Ingestion
# ════════════════════════════════════════════════════════════
# 📁 Processing directory: /mnt/d/_sandbox/Lit_review/79.015 Neuroscience
# 📝 Output directory: document_summaries
# 
# 🔍 Scanning for supported documents...
# 📄 Found 15 supported documents
# 
# 📄 Processing document 1/15: Balewski et al. - 2022 - Fast and slow contributions...
# ✅ Processed: Fast and slow contributions to decision making in corticostriatal circuits
# 
# [... processes all 15 PDFs ...]
# 
# ✅ Processing completed!
# 📊 Processing Statistics:
#    📄 Total found: 15
#    ✅ Processed: 14
#    ❌ Failed: 1 (corrupted PDF)

# 3. Build searchable knowledge base
python kb_cli.py -d document_summaries build

# Output:
# 📁 Scanning directory: document_summaries
# 📄 Found 29 markdown files
# 🤖 Processing files with OpenAI API...
# ✅ Successfully processed 29 files
# 💾 Knowledge base saved to: data/knowledge_base.json

# 4. Build embeddings for semantic search
python kb_cli.py -d document_summaries embeddings

# Output:
# Building embeddings for knowledge database using openai...
# Processing embeddings 1/29: zuzanna_z_balewski_eric_b_knudsen...
# Created embedding for zuzanna_z_balewski...
# [... creates embeddings for all papers ...]
# Created 29 new embeddings

# 5. Search and query the knowledge base
python kb_cli.py -d document_summaries search "dopamine"
# Found 3 files mentioning dopamine

python kb_cli.py -d document_summaries semantic "memory consolidation"
# Returns papers about engram cells and memory systems

python kb_cli.py -d document_summaries ask "What methods are used for neural recordings?"
# Answer: Based on the documents, neural recording methods include:
# 1. High-density silicon probes combined with optogenetics
# 2. Fully flexible implantable neural probes for electrophysiology
# 3. Large-scale neural recordings with new analytical approaches...
```

**What was created:**
```
document_summaries/
├── index.md                    # Master index of all 14 papers
├── by_type/
│   └── pdfs/                  # All neuroscience paper summaries
│       ├── josh_berke_what_does_dopamine_mean_1.md
│       ├── dheeraj_s_roy_...memory_retrieval_by_activating_engram_cells...md
│       └── [... 12 more paper summaries ...]
└── metadata/
    └── processing_log.json    # Tracking of all processed files

data/
├── knowledge_base.json        # Searchable database with all summaries
└── embeddings_cache.json      # AI embeddings for semantic search (29 entries)
```

### Example 2: General Research Library

Let's walk through processing a general research library:

```bash
# 1. Setup (one time)
cp .env.example .env
# Add your GEMINI_API_KEY=your_key_here to .env

# 2. Ingest all PDFs and EPUBs from your research directory
python kb_cli.py ingest ~/Documents/Research/Papers
# ✅ Creates 50+ markdown summaries in document_summaries/

# 3. Build searchable knowledge base from the summaries
python kb_cli.py -d document_summaries build
# ✅ Creates searchable database with embeddings

# 4. Search and explore your research
python kb_cli.py -d document_summaries search "deep learning"
python kb_cli.py -d document_summaries ask "What are the latest advances in computer vision?"

# 5. Add new papers (incremental)
python kb_cli.py ingest ~/Downloads/new-paper.pdf
python kb_cli.py -d document_summaries build  # Updates knowledge base
```

**Result:** You now have:
- `document_summaries/` directory with organized markdown summaries of all your documents
- A searchable knowledge base that lets you ask questions about your entire research library
- Easy way to add new documents as you acquire them

## 📋 Complete Command Reference
### **Document Ingestion Commands**
```bash
# Process documents (PDFs, EPUBs) into markdown summaries
python kb_cli.py ingest /path/to/documents                    # Process all documents in directory
python kb_cli.py ingest ~/research/paper.pdf                 # Process single document
python kb_cli.py ingest ~/docs --force                       # Force reprocess existing files
python kb_cli.py ingest ~/docs --provider gemini             # Use specific AI provider
python kb_cli.py ingest ~/docs --output-dir my_summaries     # Custom output directory
```

### **Knowledge Base Commands**
```bash
# Build searchable knowledge base from markdown files
python kb_cli.py -d document_summaries build                 # Build from summaries
python kb_cli.py -d ~/notes build --force-update             # Force rebuild all
python kb_cli.py -d ~/docs --db-path my-kb.json build        # Custom database location

# Search and query
python kb_cli.py -d document_summaries search "query"        # Keyword search
python kb_cli.py -d document_summaries semantic "query"      # AI semantic search  
python kb_cli.py -d document_summaries ask "question?"       # Natural language Q&A
python kb_cli.py -d document_summaries interactive           # Interactive chat mode

# Management and maintenance
python kb_cli.py -d document_summaries generate              # Generate missing summaries
python kb_cli.py -d document_summaries validate              # Validate database quality
python kb_cli.py -d document_summaries stats                 # Show statistics
python kb_cli.py -d document_summaries embeddings            # Build search embeddings

# Global options work with any command
python kb_cli.py -d ~/my-docs --db-path ~/my-kb.json --verbose [COMMAND]
python kb_cli.py --help                                      # Show all options
```

### 🏆 Real-World Usage Examples

```bash
# Example 1: Academic Research Library
python kb_cli.py ingest ~/Research/Papers                    # Process all research PDFs
python kb_cli.py -d document_summaries build                 # Build knowledge base
python kb_cli.py -d document_summaries ask "What are the main findings in deep learning papers?"

# Example 2: Personal Book Collection
python kb_cli.py ingest ~/Books/PDFs                         # Process personal library
python kb_cli.py -d document_summaries search "productivity" # Find relevant books
python kb_cli.py -d document_summaries interactive           # Ask questions about your books

# Example 3: Project Documentation  
python kb_cli.py -d ~/Projects/myapp/docs build              # From existing markdown docs
python kb_cli.py -d ~/Projects/myapp/docs ask "How do I deploy this application?"

# Example 4: Mixed Document Types
python kb_cli.py ingest ~/Documents/TechnicalManuals         # Process PDF manuals
python kb_cli.py ingest ~/Documents/Ebooks                   # Process EPUB books
python kb_cli.py -d document_summaries build                 # Build unified knowledge base
```

### 📺 Example Output

**Document Ingestion:**
```
╔══════════════════════════════════════════════════════════╗
║         AI-Powered Markdown Knowledge Base System         ║
║                  Intelligent Q&A from Markdown            ║
╚══════════════════════════════════════════════════════════╝

════════════════════════════════════════════════════════════
  Document Ingestion
════════════════════════════════════════════════════════════
📁 Processing directory: ~/Research/Papers
📝 Output directory: document_summaries

🔍 Scanning for supported documents...
📄 Found 47 supported documents

✅ Processing completed!

📊 Processing Statistics:
   📄 Total found: 47
   ✅ Processed: 45
   ⏭️  Skipped: 0
   ❌ Failed: 2

📚 Master index: document_summaries/index.md
```

**Knowledge Base Building & Querying:**
```
📁 Scanning directory: document_summaries
📄 Found 45 markdown files
🤖 Processing files with Gemini API...
✅ Successfully processed 45 files

❓ Your question: What are the main findings about neural networks?
🔍 Searching knowledge base...

💡 Answer:
Based on your research library, the main findings about neural networks include:
1. Deep learning architectures show superior performance on image recognition tasks
2. Transformer models have revolutionized natural language processing
3. Attention mechanisms significantly improve model interpretability

📚 Sources: deep_learning_review.md, transformer_paper.md, cnn_analysis.md
🎯 Confidence: high
```

## 📚 Documentation

For detailed usage instructions, see:
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Comprehensive usage guide
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation  
- **[PROVIDER_GUIDE.md](PROVIDER_GUIDE.md)** - API provider configuration

## 🧪 Testing & Quality Assurance

The system includes comprehensive testing:
```bash
# Run all tests
python run_all_tests.py

# Run specific test suites
python -m pytest test_knowledge_base_builder.py -v
python -m pytest test_semantic_search.py -v
```

**Test Coverage:**
- 82+ tests across 9 test files
- Core functionality: ✅ Full coverage
- API integrations: ✅ Mocked and tested
- Error handling: ✅ Comprehensive
- CLI interface: ✅ Complete coverage

## 🏗️ Architecture

### Core Components

**Document Ingestion Pipeline:**
- **`document_ingester.py`** - PDF/EPUB text extraction and markdown generation
- **`api_providers.py`** - Multi-provider AI API abstraction (OpenAI/Gemini/Claude)

**Knowledge Base System:**
- **`kb_cli.py`** - Unified CLI interface for both ingestion and knowledge base
- **`knowledge_base_builder.py`** - Core system orchestrator
- **`markdown_scanner.py`** - File discovery and scanning
- **`markdown_summarizer_v2.py`** - Multi-provider AI summarization
- **`semantic_search_v2.py`** - Multi-provider embedding-based search
- **`question_answerer.py`** - Natural language Q&A
- **`knowledge_database.py`** - Database management
- **`config.py`** - Configuration management
- **`error_handler.py`** - Centralized error handling

### Data Flow
```
PDFs/EPUBs → Document Ingester → Markdown Summaries → Knowledge Base
                ↓                        ↓                  ↓
           Text Extraction        Organized Storage    Search/Q&A
                ↓                        ↓                  ↓
           AI Summarization       Master Index     Embeddings Cache
```

**File Organization:**
```
Your Documents/
├── research-paper.pdf
├── textbook.epub
└── manual.pdf

            ↓ ingest

document_summaries/
├── index.md                          # Master index
├── by_type/
│   ├── pdfs/
│   │   ├── author_research_paper.md
│   │   └── manual_summary.md
│   └── ebooks/
│       └── author_textbook.md
└── metadata/
    └── processing_log.json

            ↓ build

data/
├── knowledge_base.json              # Searchable database
└── embeddings_cache.json           # AI embeddings for search
```

## ⚙️ Configuration Options

The system supports multiple API providers and extensive customization:

```env
# Primary API (choose one)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Model Configuration
OPENAI_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-small

# Processing Settings
MAX_CONTENT_LENGTH=15000
MAX_RETRIES=3
DEFAULT_TOP_K=5
DEFAULT_SIMILARITY_THRESHOLD=0.7

# Logging
LOG_LEVEL=INFO
```

## 📁 Legacy Tools

### Audio to Notion Processor
```bash
python audio_to_notion.py
```
Requires: `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `OPENAI_API_KEY`

### Zotero to Anki  
```bash
python zotero_to_anki.py
```
Requires: `ZOTERO_API_KEY`, `ZOTERO_USER_ID`, `OPENAI_API_KEY`

## 🤝 Contributing

1. **Quality Standards**: All code must pass the comprehensive test suite
2. **Test Coverage**: New features require corresponding tests
3. **Documentation**: Update relevant documentation files
4. **Error Handling**: Follow the centralized error handling patterns

## 📄 License

This project is for educational and research purposes at CMU.

---

## 🚨 Getting Help

1. **Check the logs**: `logs/application.log` and `logs/error.log`
2. **Validate configuration**: `python config.py validate`
3. **Run diagnostics**: `python kb_cli.py stats`
4. **Review documentation**: [USAGE_GUIDE.md](USAGE_GUIDE.md)

**Common Issues:**
- Missing API key → Check `.env` file
- Import errors → Run `pip install -r requirements.txt`
- Empty results → Ensure markdown files exist and are readable
- API errors → Check API key validity and quota
- **"No existing database found" error** → You forgot to specify `--db-path`. Use the full command:
  ```bash
  python kb_cli.py -d document_summaries --db-path document_summaries/data/knowledge_base.json [command]
  ```
  Or use the helper script: `python lit_review_search.py [command]`
- **No semantic search results** → Lower the threshold with `-t 0.4` or use more descriptive queries
- **Knowledge base not building** → Check that your markdown files are in the specified directory

For more detailed troubleshooting, see [USAGE_GUIDE.md](USAGE_GUIDE.md#troubleshooting).