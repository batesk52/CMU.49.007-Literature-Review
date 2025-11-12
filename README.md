# CMU.49.007 Literature Review Tools

This repository contains a streamlined suite of tools for processing academic literature and audio files for research purposes.

## Project Structure

```
CMU.49.007-Literature-Review/
├── Core Tools (3 files):
│   ├── audio_to_notion.py                  # Audio → Notion workflow
│   ├── zotero_to_anki.py                   # Zotero → Anki flashcards
│   └── summarize_paper_to_database.ipynb   # Papers → CSV database
├── Configuration:
│   ├── .env.example                        # Environment variables template
│   ├── requirements.txt                    # Python dependencies
│   └── README.md                           # This file
├── Data (generated):
│   ├── data/                               # Processing state
│   ├── literature_data/                    # CSV databases
│   └── document_summaries/                 # Generated summaries
```

## Tools Overview

### 1. Audio to Notion Processor (`audio_to_notion.py`)
Monitors a folder for new MP3 files, transcribes them using OpenAI Whisper, generates AI-powered summaries, and saves both transcript and summary to Notion.

**Features:**
- Automatic file monitoring and change detection
- Large file handling (splits files >25MB)
- AI-generated titles and summaries
- State persistence to avoid reprocessing

### 2. Zotero to Anki Converter (`zotero_to_anki.py`)
Converts Zotero annotations to Anki flashcards using OpenAI for question generation.

**Features:**
- Batch processing of 20+ Zotero collections
- Nested deck creation by collection/author
- Smart skipping of already-processed papers
- GPT-4 powered Q&A generation

### 3. Paper Summarizer (`summarize_paper_to_database.ipynb`)
Extracts structured data from research papers and stores them in a CSV database.

**Features:**
- PDF text extraction and analysis
- Identifies review vs. research papers
- Structured metadata extraction (materials, methods, results)
- Version-controlled database with cleaning tools

## Audio to Notion Processor Setup

### Prerequisites

1. **OpenAI API Key**: You need an OpenAI API key with access to:
   - Whisper API (for audio transcription)
   - GPT-4 API (for text summarization)

2. **Notion Integration**:
   - Create a Notion integration at https://www.notion.so/my-integrations
   - Get your integration token
   - Create a database in Notion and share it with your integration
   - Copy the database ID from the URL

3. **Python Environment**: Ensure you have Python 3.7+ installed

### Installation

1. Clone this repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env and add your actual API keys and credentials
   nano .env  # or use your preferred editor
   ```

   Required environment variables:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `NOTION_TOKEN` - Your Notion integration token
   - `NOTION_DATABASE_ID` - Your Notion database ID
   - `AUDIO_FOLDER_PATH` - Path to audio files folder (optional, defaults to `./audio_files`)

   For Zotero to Anki tool, also add:
   - `ZOTERO_USER_ID` - Your Zotero user ID
   - `ZOTERO_API_KEY` - Your Zotero API key
   - `ZOTERO_LIBRARY_TYPE` - Usually "user" (optional)

### Notion Database Setup

Your Notion database should have the following properties:
- **Title** (Title type) - Will contain the MP3 filename
- **Date** (Date type) - Will contain the processing date

The tool will automatically add:
- Summary section
- Full transcript section

### Usage

1. **Create your audio folder**:
   ```bash
   mkdir audio_files
   ```

2. **Add MP3 files** to the `audio_files` folder (or the folder specified in `AUDIO_FOLDER_PATH`)

3. **Run the processor**:
   ```bash
   python audio_to_notion.py
   ```

### How It Works

1. **File Detection**: The tool scans the specified folder for MP3 files
2. **Change Detection**: Uses file hashing to detect new or modified files
3. **Transcription**: Sends audio files to OpenAI Whisper API for transcription
4. **Summarization**: Uses GPT-4 to create a concise summary of the transcript
5. **Notion Integration**: Creates a new page in your Notion database with:
   - File name as the title
   - Processing date
   - Summary section
   - Full transcript section
6. **State Tracking**: Saves processing state to avoid reprocessing the same files

### Features

- **Incremental Processing**: Only processes new or modified files
- **Error Handling**: Continues processing even if individual files fail
- **Progress Tracking**: Shows processing statistics and progress
- **State Persistence**: Remembers which files have been processed
- **Flexible Configuration**: Configurable via environment variables

### Example Output

```
Processing stats: {'total_mp3_files': 3, 'processed_files': 0, 'unprocessed_files': 3}
Found 3 new files to process:
  - lecture_1.mp3
  - interview_2.mp3
  - meeting_3.mp3
Transcribing: lecture_1.mp3
Generating summary...
Creating Notion page for: lecture_1.mp3
✓ Successfully processed: lecture_1.mp3
...

✓ Successfully created 3 Notion pages:
  - Page ID: abc123def456
  - Page ID: ghi789jkl012
  - Page ID: mno345pqr678

Final stats: {'total_mp3_files': 3, 'processed_files': 3, 'unprocessed_files': 0}
```

### Troubleshooting

1. **API Key Issues**: Ensure your OpenAI API key is valid and has sufficient credits
2. **Notion Permissions**: Make sure your integration has access to the database
3. **File Format**: Only MP3 files are supported
4. **Network Issues**: Check your internet connection for API calls

### Advanced Usage

You can also use the `AudioToNotionProcessor` class programmatically:

```python
from audio_to_notion import AudioToNotionProcessor

# Initialize with custom settings
processor = AudioToNotionProcessor(
    folder_path="./my_audio_files",
    state_file="custom_state.json"
)

# Process files
created_pages = processor.process_new_files()

# Get statistics
stats = processor.get_processing_stats()
print(stats)
```

## Other Tools

### Zotero to Anki (`zotero_to_anki.py`)
Run the Python script to convert Zotero annotations to Anki flashcards:
```bash
python zotero_to_anki.py
```

**Prerequisites:**
- Zotero account with API key
- Anki desktop app running with AnkiConnect plugin
- Environment variables configured (see Installation section)

### Paper Summarizer (`summarize_paper_to_database.ipynb`)
Open the Jupyter notebook to extract structured data from research papers:
```bash
jupyter notebook summarize_paper_to_database.ipynb
```

**Prerequisites:**
- PDF files in the appropriate directory
- OpenAI API key configured

## License

This project is for educational and research purposes. 