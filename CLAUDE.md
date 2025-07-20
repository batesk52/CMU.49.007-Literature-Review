# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains tools for processing academic literature and audio files for research purposes, specifically for CMU literature review workflows. The main components are:

1. **Audio to Notion Processor** (`audio_to_notion.py`) - Monitors folders for MP3 files, transcribes them using OpenAI Whisper, summarizes content, and creates Notion pages
2. **Zotero to Anki Converter** (`zotero_to_anki.py`) - Converts Zotero annotations to Anki flashcards using OpenAI for question generation
3. **Paper Summarizer** (`summarize_paper_to_database.ipynb`) - Extracts and summarizes academic papers into a structured database

## Common Development Commands

### Python Environment Setup
```bash
pip install -r requirements.txt
```

### Running Tools
```bash
# Audio to Notion processor
python audio_to_notion.py

# Test setup and connectivity
python _test_setup.py

# Initialize existing audio files as processed
python _initialize_existing_files.py

# Zotero to Anki converter (run the script cells)
python zotero_to_anki.py
```

### Jupyter Notebooks
```bash
# Start Jupyter for paper summarization
jupyter notebook summarize_paper_to_database.ipynb
```

## Code Architecture

### Audio Processing Pipeline (`audio_to_notion.py`)
- **AudioToNotionProcessor class**: Main orchestrator for the audio processing workflow
- **File monitoring**: Uses MD5 hashing to detect new/modified MP3 files
- **Audio splitting**: Automatically chunks large files (>25MB) for OpenAI Whisper API limits
- **OpenAI integration**: Whisper for transcription, GPT-4 for summarization and title generation
- **Notion integration**: Creates structured pages with summary and full transcript sections
- **State management**: JSON-based tracking in `data/audio_processing_state.json`

### Literature Processing (`zotero_to_anki.py`)
- **Zotero API integration**: Fetches collections, items, and annotations using pyzotero
- **Annotation processing**: Converts HTML annotations to markdown, groups by parent paper
- **OpenAI card generation**: Uses GPT-4 to create question-answer pairs from annotations
- **Anki integration**: Creates flashcard decks organized by paper author/year
- **Batch processing**: Processes multiple Zotero collections automatically

### Paper Database System (`summarize_paper_to_database.ipynb`)
- **PDF text extraction**: PyPDF2-based text extraction from academic papers
- **AI-driven analysis**: GPT-4 extracts structured data (device specs, performance metrics)
- **Database management**: CSV-based literature database with standardized formatting
- **Duplicate detection**: Author/year matching to avoid reprocessing papers
- **Data cleaning**: AI-powered standardization of database formatting

## Environment Configuration

Required environment variables in `.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
NOTION_TOKEN=your_notion_integration_token_here
NOTION_DATABASE_ID=your_notion_database_id_here
AUDIO_FOLDER_PATH=./audio_files
ZOTERO_API_KEY=your_zotero_api_key_here
ZOTERO_USER_ID=your_zotero_user_id_here
ZOTERO_LIBRARY_TYPE=user
```

## Data Structure

### File Organization
- `data/` - Contains processing state files and databases
- `literature_data/` - CSV databases for literature review data
- `!archive/` - Archived/backup versions of tools

### Key Data Files
- `data/audio_processing_state.json` - Tracks processed audio files
- `literature_data/literature_database_v3.csv` - Main literature database
- Audio files are expected in the folder specified by `AUDIO_FOLDER_PATH`

## API Integration Patterns

All tools use similar patterns for API integration:
- **Error handling**: Exponential backoff retry logic for rate limits
- **Response validation**: JSON parsing with error catching
- **Token management**: Environment variable-based API key management
- **Chunking strategies**: Large content is split to respect API limits (25MB for Whisper, token limits for GPT)

## Development Notes

- The codebase uses defensive programming patterns with extensive error handling
- File processing uses state management to avoid reprocessing
- OpenAI API calls include rate limiting and retry logic
- Database operations preserve instruction rows and handle formatting standardization
- Notion API integration handles rich text formatting and block structure requirements