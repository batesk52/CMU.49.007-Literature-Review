# CMU.49.007 Literature Review Tools

This repository contains various tools for processing academic literature and audio files for research purposes.

## Tools Included

### 1. Audio to Notion Processor (`audio_to_notion.py`)
A tool that monitors a folder for new MP3 files, transcribes them using OpenAI Whisper, summarizes the content, and saves both transcript and summary to Notion.

### 2. Zotero to Anki Converter (`zotero_to_anki.ipynb`)
Converts Zotero annotations to Anki flashcards using OpenAI for question generation.

### 3. Paper Summarizer (`summarize_paper_to_database.ipynb`)
Summarizes academic papers and stores them in a database.

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

3. Create a `.env` file in the project root with the following variables:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   NOTION_TOKEN=your_notion_integration_token_here
   NOTION_DATABASE_ID=your_notion_database_id_here
   AUDIO_FOLDER_PATH=./audio_files
   ```

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

### Zotero to Anki
See the Jupyter notebook for converting Zotero annotations to Anki flashcards.

### Paper Summarizer
See the Jupyter notebook for summarizing academic papers.

## License

This project is for educational and research purposes. 