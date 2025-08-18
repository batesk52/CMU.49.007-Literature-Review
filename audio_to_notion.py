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
import time

class AudioToNotionProcessor:
    def __init__(self, folder_path: str, state_file: str = "audio_processing_state.json"):
        """
        Initialize the audio processor.
        
        Args:
            folder_path: Path to the folder containing MP3 files
            state_file: JSON file to track processed files
        """
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
        """Identify new MP3 files that haven't been processed yet."""
        current_files = self._get_mp3_files()
        new_files = []
        
        # Get set of processed filenames for faster lookup
        processed_filenames = set()
        for state_path in self.processed_files.keys():
            # Extract just the filename for comparison
            # Handle both Windows and Unix path separators
            state_filename = state_path.replace('\\', '/').split('/')[-1]
            processed_filenames.add(state_filename)
        
        for file_path in current_files:
            current_filename = os.path.basename(str(file_path))
            
            # Check if this file was already processed
            if current_filename not in processed_filenames:
                new_files.append(file_path)
                print(f"DEBUG: File {file_path.name} is NEW")
        
        print(f"DEBUG: Found {len(new_files)} new files to process")
        return new_files
    
    def _split_audio_if_needed(self, file_path: Path, max_bytes: int = 25 * 1024 * 1024) -> List[Path]:
        """
        Split the audio file into smaller chunks if it exceeds max_bytes.
        Returns a list of Path objects to the chunk files (original if not split).
        """
        file_size = file_path.stat().st_size
        
        # Use a more conservative threshold - split if over 20MB to leave buffer
        safe_max_bytes = 20 * 1024 * 1024  # 20MB to be safe with API limits
        
        if file_size <= safe_max_bytes:
            return [file_path]
        
        print(f"  File {file_path.name} is {file_size / (1024*1024):.1f}MB, splitting into smaller chunks...")
        
        try:
            audio = AudioSegment.from_file(file_path)
            audio_duration_minutes = len(audio) / (1000 * 60)  # Convert ms to minutes
            
            # Calculate optimal chunk size based on file size
            # Aim for chunks around 10-15MB each
            target_chunk_size = 12 * 1024 * 1024  # 12MB target
            num_chunks = max(2, int(file_size / target_chunk_size) + 1)
            chunk_duration_ms = len(audio) // num_chunks
            
            print(f"  Audio duration: {audio_duration_minutes:.1f} minutes")
            print(f"  Splitting into {num_chunks} chunks of approximately {chunk_duration_ms / 60000:.1f} minutes each")
            
            chunks = []
            
            for i in range(num_chunks):
                start_ms = i * chunk_duration_ms
                end_ms = min((i + 1) * chunk_duration_ms, len(audio))
                
                chunk = audio[start_ms:end_ms]
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                    # Export with compression to reduce size
                    chunk.export(tmp.name, format="mp3", bitrate="128k")
                    chunk_path = Path(tmp.name)
                    chunk_size = chunk_path.stat().st_size
                    
                    if chunk_size > max_bytes:
                        # If still too big, split this chunk further
                        print(f"    Chunk {i+1} is {chunk_size / (1024*1024):.1f}MB, splitting further...")
                        
                        # Split into smaller sub-chunks
                        sub_chunk_duration = len(chunk) // 2
                        for j in range(2):
                            sub_start = j * sub_chunk_duration
                            sub_end = len(chunk) if j == 1 else sub_chunk_duration
                            sub_chunk = chunk[sub_start:sub_end]
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as sub_tmp:
                                sub_chunk.export(sub_tmp.name, format="mp3", bitrate="128k")
                                sub_chunk_path = Path(sub_tmp.name)
                                print(f"      Sub-chunk {j+1}: {sub_chunk_path.stat().st_size / (1024*1024):.1f}MB")
                                chunks.append(sub_chunk_path)
                        
                        # Remove the original large chunk temp file
                        try:
                            chunk_path.unlink()
                        except:
                            pass
                    else:
                        print(f"    Chunk {i+1}: {chunk_size / (1024*1024):.1f}MB")
                        chunks.append(chunk_path)
            
            print(f"  Successfully split into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            print(f"  Warning: Audio splitting failed: {str(e)}")
            print("  This might be due to missing FFmpeg. Please install FFmpeg:")
            print("    sudo apt-get update && sudo apt-get install ffmpeg")
            print("  Or on Windows: winget install Gyan.FFmpeg")
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
            
            # Retry logic with exponential backoff
            max_retries = 3
            retry_delay = 2  # Start with 2 seconds
            
            for attempt in range(max_retries):
                try:
                    with open(chunk_path, "rb") as audio_file:
                        files = {"file": (chunk_path.name, audio_file, "audio/mpeg")}
                        data = {"model": "whisper-1"}
                        
                        # Increase timeout for larger files
                        timeout_seconds = max(120, int(chunk_size * 10))  # At least 120s, or 10s per MB
                        print(f"    Attempt {attempt + 1}/{max_retries} with timeout of {timeout_seconds}s...")
                        
                        response = requests.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers=headers,
                            files=files,
                            data=data,
                            timeout=timeout_seconds
                        )
                        
                        if response.status_code == 200:
                            chunk_transcript = response.json()["text"]
                            transcript += chunk_transcript + "\n"
                            print(f"    ✓ Chunk {idx+1} transcribed successfully ({len(chunk_transcript)} characters)")
                            break  # Success, exit retry loop
                        elif response.status_code == 504 or response.status_code == 502:
                            # Gateway timeout or bad gateway - retry
                            if attempt < max_retries - 1:
                                print(f"    Gateway timeout/error (status {response.status_code}). Retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                            else:
                                raise Exception(f"Transcription failed after {max_retries} attempts: {response.status_code}")
                        elif response.status_code == 429:
                            # Rate limit - wait longer
                            wait_time = int(response.headers.get('Retry-After', retry_delay))
                            print(f"    Rate limited. Waiting {wait_time}s before retry...")
                            time.sleep(wait_time)
                            continue
                        else:
                            error_msg = f"Transcription failed for chunk {chunk_path.name}: Status {response.status_code}"
                            if "file too large" in response.text.lower():
                                error_msg += f"\n    File size: {chunk_size:.1f}MB (limit: 25MB)"
                            raise Exception(error_msg)
                            
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        print(f"    Request timeout. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise Exception(f"Transcription timed out after {max_retries} attempts")
                except requests.exceptions.ConnectionError as e:
                    if attempt < max_retries - 1:
                        print(f"    Connection error: {str(e)}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise Exception(f"Connection failed after {max_retries} attempts: {str(e)}")
                except Exception as e:
                    # For other exceptions, clean up and re-raise
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
        """Summarize text using OpenAI GPT API with chunking for long texts."""
        print("Generating summary...")
        
        # If text is short enough, summarize directly
        if len(text) <= 6000:  # Conservative limit to stay well under token limit
            return self._summarize_chunk(text)
        
        # For long texts, split into chunks and summarize each
        print(f"Text is {len(text)} characters long, splitting into chunks...")
        chunks = self._split_text_for_summarization(text)
        summaries = []
        
        for i, chunk in enumerate(chunks):
            print(f"  Summarizing chunk {i+1}/{len(chunks)} ({len(chunk)} characters)...")
            chunk_summary = self._summarize_chunk(chunk)
            summaries.append(chunk_summary)
        
        # Combine summaries if there are multiple
        if len(summaries) == 1:
            return summaries[0]
        else:
            print("Combining chunk summaries...")
            combined_summaries = "\n\n".join(summaries)
            return self._summarize_chunk(combined_summaries, is_summary_of_summaries=True)
    
    def _split_text_for_summarization(self, text: str, max_length: int = 5000) -> List[str]:
        """Split text into chunks suitable for summarization."""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            
            # Find a good split point near the max_length
            split_point = max_length
            for i in range(max_length, max(0, max_length - 200), -1):
                if text[i] in '.!?':
                    split_point = i + 1
                    break
                elif text[i] == ' ':
                    split_point = i + 1
                    break
            
            chunks.append(text[:split_point])
            text = text[split_point:].lstrip()
        
        return chunks
    
    def _summarize_chunk(self, text: str, is_summary_of_summaries: bool = False) -> str:
        """Summarize a single chunk of text."""
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        if is_summary_of_summaries:
            system_prompt = "You are a helpful assistant that creates a final, comprehensive summary from multiple partial summaries. Combine them into one coherent, well-structured summary that captures all the key points."
            user_prompt = f"Please create a final comprehensive summary from these partial summaries:\n\n{text}"
        else:
            system_prompt = "You are a helpful assistant that creates concise, informative summaries of audio transcriptions. Focus on key points, main ideas, and important details."
            user_prompt = f"Please provide a comprehensive summary of the following audio transcription:\n\n{text}"
        
        data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
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
        
        # Split both transcript and summary if needed
        transcript_chunks = split_text(transcript)
        summary_chunks = split_text(summary)
        
        # Build children blocks
        children = []
        
        # Add Summary heading
        children.append({
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
        })
        
        # Add summary chunks
        for chunk in summary_chunks:
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
        
        # Add Full Transcript heading
        children.append({
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
        })
        
        # Add transcript chunks
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
        print("DEBUG: process_new_files() called")
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
                print(f"\nDEBUG: Processing file {file_path.name}...")
                # Transcribe the audio
                print(f"DEBUG: Starting transcription for {file_path.name}")
                transcript = self._transcribe_audio(file_path)
                print(f"DEBUG: Transcription complete, got {len(transcript)} characters")
                
                # Summarize the transcript
                summary = self._summarize_text(transcript)
                
                # Create Notion page
                page_id = self._create_notion_page(file_path.name, transcript, summary)
                created_pages.append(page_id)
                
                # Update state - preserve original path format if file exists
                file_hash = self._get_file_hash(file_path)
                file_path_str = str(file_path)
                stored_path = file_path_str
                
                # Check if this filename already exists in state
                for state_path in self.processed_files:
                    if os.path.basename(state_path) == os.path.basename(file_path_str):
                        stored_path = state_path  # Keep the original format
                        break
                
                self.processed_files[stored_path] = file_hash
                
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


def convert_windows_to_wsl_path(windows_path: str) -> str:
    """Convert Windows path to WSL path."""
    # Handle different Windows path formats
    if windows_path.startswith("D:"):
        # Convert D:\ or D:/ to /mnt/d/
        wsl_path = windows_path.replace("D:\\", "/mnt/d/").replace("D:/", "/mnt/d/")
    elif windows_path.startswith("C:"):
        # Convert C:\ or C:/ to /mnt/c/
        wsl_path = windows_path.replace("C:\\", "/mnt/c/").replace("C:/", "/mnt/c/")
    else:
        # If it doesn't start with a Windows drive letter, return as is
        return windows_path
    
    # Replace backslashes with forward slashes
    wsl_path = wsl_path.replace("\\", "/")
    
    return wsl_path

def find_accessible_path(original_path: str) -> str:
    """Find an accessible path, trying both Windows and WSL formats."""
    # First try the original path
    if os.path.exists(original_path):
        return original_path
    
    # If on WSL, try converting Windows path to WSL format
    if os.name == 'posix' and (original_path.startswith("D:") or original_path.startswith("C:")):
        wsl_path = convert_windows_to_wsl_path(original_path)
        if os.path.exists(wsl_path):
            print(f"Using WSL path: {wsl_path}")
            return wsl_path
    
    # If neither works, return the original path
    return original_path

def main():
    """Main function to run the audio processor."""
    print("Main function started")
    
    # Load environment variables
    load_dotenv()
    print("Environment loaded")
    
    # Configuration
    FOLDER_PATH = os.getenv("AUDIO_FOLDER_PATH", "./audio_files")
    STATE_FILE = "data/audio_processing_state.json"
    
    # Try to find accessible path
    print(f"Original path from env: {FOLDER_PATH}")
    FOLDER_PATH = find_accessible_path(FOLDER_PATH)
    print(f"Using path: {FOLDER_PATH}")
    
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
