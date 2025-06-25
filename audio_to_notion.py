import os
import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydub import AudioSegment
import tempfile

class AudioToNotionProcessor:
    def __init__(self, folder_path: str, state_file: str = "audio_processing_state.json"):
        """
        Initialize the audio processor.
        
        Args:
            folder_path: Path to the folder containing MP3 files
            state_file: JSON file to track processed files
        """
        load_dotenv()
        
        self.folder_path = Path(folder_path)
        self.state_file = Path(state_file)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID")
        
        # Validate required environment variables
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not self.notion_token:
            raise ValueError("NOTION_TOKEN environment variable is required")
        if not self.notion_database_id:
            raise ValueError("NOTION_DATABASE_ID environment variable is required")
        
        # Load previous state
        self.processed_files = self._load_state()
        
    def _load_state(self) -> Dict[str, str]:
        """Load the state of previously processed files."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_state(self):
        """Save the current state of processed files."""
        with open(self.state_file, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate a hash for a file to detect changes."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_mp3_files(self) -> List[Path]:
        """Get all MP3 files in the monitored folder."""
        mp3_files = []
        if self.folder_path.exists():
            mp3_files = list(self.folder_path.glob("*.mp3"))
        return mp3_files
    
    def _get_new_files(self) -> List[Path]:
        """Identify new or modified MP3 files."""
        current_files = self._get_mp3_files()
        new_files = []
        
        for file_path in current_files:
            file_hash = self._get_file_hash(file_path)
            if (str(file_path) not in self.processed_files or 
                self.processed_files[str(file_path)] != file_hash):
                new_files.append(file_path)
        
        return new_files
    
    def _split_audio_if_needed(self, file_path: Path, max_bytes: int = 25 * 1024 * 1024) -> List[Path]:
        """
        Split the audio file into smaller chunks if it exceeds max_bytes.
        Returns a list of Path objects to the chunk files (original if not split).
        """
        if file_path.stat().st_size <= max_bytes:
            return [file_path]
        
        print(f"  File {file_path.name} is too large, attempting to split into chunks...")
        
        try:
            audio = AudioSegment.from_file(file_path)
            chunk_length_ms = 10 * 60 * 1000  # 10 minutes in ms
            chunks = []
            
            for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
                chunk = audio[start:start + chunk_length_ms]
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                    chunk.export(tmp.name, format="mp3")
                    chunk_path = Path(tmp.name)
                    
                    if chunk_path.stat().st_size > max_bytes:
                        # If still too big, split further (5 min)
                        print(f"    Chunk {i+1} still too large, splitting further...")
                        sub_chunk_length_ms = 5 * 60 * 1000
                        for j, sub_start in enumerate(range(0, len(chunk), sub_chunk_length_ms)):
                            sub_chunk = chunk[sub_start:sub_start + sub_chunk_length_ms]
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as sub_tmp:
                                sub_chunk.export(sub_tmp.name, format="mp3")
                                chunks.append(Path(sub_tmp.name))
                    else:
                        chunks.append(chunk_path)
            
            print(f"  Successfully split into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            print(f"  Warning: Audio splitting failed: {str(e)}")
            print("  This might be due to missing FFmpeg. Please install FFmpeg:")
            print("    winget install Gyan.FFmpeg")
            print("  Or download from: https://ffmpeg.org/download.html")
            print("  Falling back to original file (may fail if too large)...")
            return [file_path]
    
    def _transcribe_audio(self, file_path: Path) -> str:
        """Transcribe audio file using OpenAI Whisper API, splitting if needed."""
        max_bytes = 25 * 1024 * 1024  # 25MB limit for OpenAI
        
        # Check if original file is too large
        if file_path.stat().st_size > max_bytes:
            print(f"  File size: {file_path.stat().st_size / (1024*1024):.1f}MB (limit: 25MB)")
        
        chunk_paths = self._split_audio_if_needed(file_path, max_bytes=max_bytes)
        transcript = ""
        
        for idx, chunk_path in enumerate(chunk_paths):
            chunk_size = chunk_path.stat().st_size / (1024*1024)
            print(f"  Transcribing chunk {idx+1}/{len(chunk_paths)}: {chunk_path.name} ({chunk_size:.1f}MB)")
            
            # Check if chunk is still too large
            if chunk_path.stat().st_size > max_bytes:
                print(f"  Warning: Chunk {idx+1} is still too large ({chunk_size:.1f}MB > 25MB)")
                print("  This chunk will likely fail transcription. Consider:")
                print("    1. Installing FFmpeg for better audio splitting")
                print("    2. Manually splitting the audio file")
                print("    3. Using a smaller audio file")
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            try:
                with open(chunk_path, "rb") as audio_file:
                    files = {"file": (chunk_path.name, audio_file, "audio/mpeg")}
                    data = {"model": "whisper-1"}
                    response = requests.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers=headers,
                        files=files,
                        data=data
                    )
                    if response.status_code == 200:
                        chunk_transcript = response.json()["text"]
                        transcript += chunk_transcript + "\n"
                        print(f"    ✓ Chunk {idx+1} transcribed successfully ({len(chunk_transcript)} characters)")
                    else:
                        error_msg = f"Transcription failed for chunk {chunk_path.name}: {response.text}"
                        if "file too large" in response.text.lower():
                            error_msg += f"\n    File size: {chunk_size:.1f}MB (limit: 25MB)"
                        raise Exception(error_msg)
            except Exception as e:
                # Clean up temp files before re-raising
                for temp_path in chunk_paths:
                    if temp_path != file_path and temp_path.exists():
                        try:
                            temp_path.unlink()
                        except Exception:
                            pass
                raise e
        
        # Clean up temp files
        for chunk_path in chunk_paths:
            if chunk_path != file_path and chunk_path.exists():
                try:
                    chunk_path.unlink()
                except Exception:
                    pass
        
        return transcript.strip()
    
    def _summarize_text(self, text: str) -> str:
        """Summarize text using OpenAI GPT API."""
        print("Generating summary...")
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise, informative summaries of audio transcriptions. Focus on key points, main ideas, and important details."
                },
                {
                    "role": "user",
                    "content": f"Please provide a comprehensive summary of the following audio transcription:\n\n{text}"
                }
            ],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Summarization failed: {response.text}")
    
    def _generate_title(self, transcript: str) -> str:
        """Generate a concise title for the audio using OpenAI."""
        print("Generating AI title...")
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an assistant that generates concise, informative titles for audio transcripts. Return only the title, no extra text."
                },
                {
                    "role": "user",
                    "content": f"Please propose a short, descriptive title for the following audio transcript.\n\n{transcript[:3000]}"
                }
            ],
            "max_tokens": 20,
            "temperature": 0.5
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip().replace('\n', ' ')
        else:
            raise Exception(f"Title generation failed: {response.text}")
    
    def _create_notion_page(self, file_name: str, transcript: str, summary: str) -> str:
        """Create a new page in Notion database."""
        print(f"Creating Notion page for: {file_name}")

        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Generate a better title using AI
        title_prompt = f"Generate a concise, descriptive title (3-8 words) for this audio recording. Do not use quotation marks. Return only the title text. Audio filename: {file_name}\n\nTranscript preview: {transcript[:200]}..."
        
        try:
            title_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that generates concise, descriptive titles for audio recordings. Do not use quotation marks. Return only the title text."},
                        {"role": "user", "content": title_prompt}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.3
                }
            )
            
            if title_response.status_code == 200:
                ai_title = title_response.json()["choices"][0]["message"]["content"].strip()
                # Remove any quotation marks and excessive whitespace
                ai_title = ai_title.replace('"', '').replace("'", '').strip()
                # Fallback if title is empty
                if not ai_title:
                    ai_title = "Untitled"
                notion_title = f"{ai_title} - {file_name}"
            else:
                notion_title = file_name
        except Exception as e:
            print(f"  Warning: Title generation failed: {str(e)}")
            notion_title = file_name
        
        print(f"Proposed title: {notion_title}")
        
        def split_text(text: str, max_length: int = 1900) -> List[str]:
            if len(text) <= max_length:
                return [text]
            chunks = []
            while text:
                if len(text) <= max_length:
                    chunks.append(text)
                    break
                split_point = max_length
                for i in range(max_length, max(0, max_length - 100), -1):
                    if text[i] in '.!?':
                        split_point = i + 1
                        break
                    elif text[i] == ' ':
                        split_point = i + 1
                        break
                chunks.append(text[:split_point])
                text = text[split_point:].lstrip()
            return chunks
        transcript_chunks = split_text(transcript)
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Summary"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Full Transcript"
                            }
                        }
                    ]
                }
            }
        ]
        for chunk in transcript_chunks:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk
                            }
                        }
                    ]
                }
            })
        page_data = {
            "parent": {"database_id": self.notion_database_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": notion_title
                            }
                        }
                    ]
                }
            },
            "children": children
        }
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=page_data
        )
        if response.status_code == 200:
            return response.json()["id"]
        else:
            raise Exception(f"Notion page creation failed: {response.text}")
    
    def process_new_files(self) -> List[str]:
        """Process all new MP3 files and return list of created page IDs."""
        new_files = self._get_new_files()
        
        if not new_files:
            print("No new files to process.")
            return []
        
        print(f"Found {len(new_files)} new files to process:")
        for file_path in new_files:
            print(f"  - {file_path.name}")
        
        created_pages = []
        
        for file_path in new_files:
            try:
                # Transcribe the audio
                transcript = self._transcribe_audio(file_path)
                
                # Summarize the transcript
                summary = self._summarize_text(transcript)
                
                # Create Notion page
                page_id = self._create_notion_page(file_path.name, transcript, summary)
                created_pages.append(page_id)
                
                # Update state
                self.processed_files[str(file_path)] = self._get_file_hash(file_path)
                
                print(f"✓ Successfully processed: {file_path.name}")
                
            except Exception as e:
                print(f"✗ Error processing {file_path.name}: {str(e)}")
                continue
        
        # Save updated state
        self._save_state()
        
        return created_pages
    
    def get_processing_stats(self) -> Dict:
        """Get statistics about processed files."""
        total_files = len(self._get_mp3_files())
        processed_count = len(self.processed_files)
        
        return {
            "total_mp3_files": total_files,
            "processed_files": processed_count,
            "unprocessed_files": total_files - processed_count
        }


def main():
    """Main function to run the audio processor."""
    # Configuration
    FOLDER_PATH = os.getenv("AUDIO_FOLDER_PATH", "./audio_files")
    STATE_FILE = "data/audio_processing_state.json"
    
    try:
        # Initialize processor
        processor = AudioToNotionProcessor(FOLDER_PATH, STATE_FILE)
        
        # Get stats before processing
        stats_before = processor.get_processing_stats()
        print(f"Processing stats: {stats_before}")
        
        # Process new files
        created_pages = processor.process_new_files()
        
        if created_pages:
            print(f"\n✓ Successfully created {len(created_pages)} Notion pages:")
            for page_id in created_pages:
                print(f"  - Page ID: {page_id}")
        else:
            print("\nNo new pages created.")
        
        # Get stats after processing
        stats_after = processor.get_processing_stats()
        print(f"\nFinal stats: {stats_after}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
