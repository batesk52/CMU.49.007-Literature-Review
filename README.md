# CMU.49.007 Literature Review Tools

This repository contains tools for automated literature review, including scripts to convert Zotero annotations to Anki flashcards and process academic papers.

## Project Structure

```
.

├── literature_data/     # Directory for storing paper data
├── zotero_to_anki.ipynb # Script to convert Zotero annotations to Anki cards
├── audio_to_anki.ipynb  # Script to convert audio notes to Anki cards
└── summarize_paper_to_database.ipynb # Script to process and summarize papers
```

## Setup Instructions

### 1. Environment Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

### 2. Environment Variables (.env)

Create a `.env` file in the root directory with the following variables:

```
# Zotero API Configuration
ZOTERO_API_KEY=your_api_key_here
ZOTERO_USER_ID=your_user_id_here
ZOTERO_LIBRARY_TYPE=user  # or 'group' if using a group library

# Anki Configuration (if using AnkiConnect)
ANKI_CONNECT_URL=http://localhost:8765
```

To get your Zotero API key:
1. Log in to your Zotero account
2. Go to Settings → Feeds/API
3. Create a new private key with appropriate permissions

### 3. Running the Scripts

1. **Zotero to Anki Conversion**:
   - Open `zotero_to_anki.ipynb` in Jupyter Notebook
   - Follow the steps in the notebook:
     1. Open a paper in Zotero
     2. Copy the paper into a text file named "paper.txt"
     3. Create annotations and save as "notes.txt"
     4. Place files in the `_inbox` folder
     5. Run the notebook cells

2. **Audio to Anki Conversion**:
   - Open `audio_to_anki.ipynb`
   - Follow the instructions in the notebook

3. **Paper Summarization**:
   - Open `summarize_paper_to_database.ipynb`
   - Follow the instructions in the notebook

## Dependencies

The project requires the following main dependencies:
- python-dotenv
- pyzotero
- html2text
- requests
- jupyter

## Notes

- Make sure Anki is running with AnkiConnect plugin installed when using the Anki-related scripts
- Keep your `.env` file secure and never commit it to version control
- The `literature_data` directory is used for storing processed papers and annotations

## Contributing

Feel free to submit issues and enhancement requests! 