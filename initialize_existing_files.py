#!/usr/bin/env python3
"""
Initialize existing MP3 files as already processed.

This script scans a folder of existing MP3 files and marks them as already processed
so they won't be reprocessed by the audio_to_notion.py tool.
"""

import os
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv

def get_file_hash(file_path: Path) -> str:
    """Generate a hash for a file to detect changes."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def initialize_existing_files(folder_path: str, state_file: str = "audio_processing_state.json"):
    """
    Initialize the processing state with existing MP3 files.
    
    Args:
        folder_path: Path to the folder containing existing MP3 files
        state_file: JSON file to store the processing state
    """
    folder = Path(folder_path)
    state_file_path = Path(state_file)
    
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist!")
        return False
    
    # Get all MP3 files in the folder
    mp3_files = list(folder.glob("*.mp3"))
    
    if not mp3_files:
        print(f"No MP3 files found in '{folder_path}'")
        return False
    
    print(f"Found {len(mp3_files)} MP3 files in '{folder_path}'")
    
    # Load existing state (if any)
    existing_state = {}
    if state_file_path.exists():
        try:
            with open(state_file_path, 'r') as f:
                existing_state = json.load(f)
            print(f"Loaded existing state with {len(existing_state)} files")
        except (json.JSONDecodeError, FileNotFoundError):
            print("No existing state found, starting fresh")
    
    # Process each MP3 file
    new_files_added = 0
    existing_files_updated = 0
    
    for file_path in mp3_files:
        file_hash = get_file_hash(file_path)
        file_key = str(file_path)
        
        if file_key in existing_state:
            if existing_state[file_key] != file_hash:
                existing_state[file_key] = file_hash
                existing_files_updated += 1
                print(f"  Updated: {file_path.name}")
            else:
                print(f"  Already tracked: {file_path.name}")
        else:
            existing_state[file_key] = file_hash
            new_files_added += 1
            print(f"  Added: {file_path.name}")
    
    # Save the updated state
    with open(state_file_path, 'w') as f:
        json.dump(existing_state, f, indent=2)
    
    print(f"\n=== Summary ===")
    print(f"Total files in state: {len(existing_state)}")
    print(f"New files added: {new_files_added}")
    print(f"Existing files updated: {existing_files_updated}")
    print(f"State saved to: {state_file_path}")
    return True

def main():
    """Main function."""
    load_dotenv()
    
    # Get folder path from environment or use default
    folder_path = os.getenv("AUDIO_FOLDER_PATH", r"D:\OneDrive\Apps\Easy Voice Recorder Pro")
    state_file = "data/audio_processing_state.json"
    
    print("=== Initialize Existing MP3 Files ===\n")
    print(f"Folder: {folder_path}")
    print(f"State file: {state_file}")
    print()
    
    # Confirm with user
    response = input("This will mark all existing MP3 files as already processed. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return 1
    
    try:
        success = initialize_existing_files(folder_path, state_file)
        if success:
            print("\n✓ Initialization completed successfully!")
            print("\nNext steps:")
            print("1. Add new MP3 files to the folder")
            print("2. Run: python audio_to_notion.py")
            return 0
        else:
            print("\n✗ Initialization failed.")
            return 1
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 