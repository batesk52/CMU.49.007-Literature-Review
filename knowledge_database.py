"""
Knowledge Database Module

This module provides functionality to create and manage a JSON database for storing
markdown file paths, summaries, and metadata for the knowledge base system.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeDatabase:
    """
    Manages a JSON-based database for storing markdown file information and summaries.
    """
    
    def __init__(self, db_path: str = "data/knowledge_base.json"):
        """
        Initialize the database manager.
        
        Args:
            db_path (str): Path to the JSON database file
        """
        self.db_path = Path(db_path)
        self.db_data = {
            "metadata": {
                "created_at": None,
                "last_updated": None,
                "version": "1.0",
                "file_count": 0
            },
            "files": {}
        }
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing database if it exists
        self.load_database()
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of a file for change detection.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            str: MD5 hash of the file content
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return ""
    
    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Get metadata for a file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            Dict[str, Any]: File metadata including size, timestamps, etc.
        """
        try:
            stat = file_path.stat()
            return {
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "file_hash": self._calculate_file_hash(file_path)
            }
        except Exception as e:
            logger.warning(f"Could not get metadata for {file_path}: {e}")
            return {
                "size_bytes": 0,
                "modified_time": datetime.now().isoformat(),
                "created_time": datetime.now().isoformat(),
                "file_hash": ""
            }
    
    def load_database(self) -> None:
        """
        Load the database from the JSON file if it exists.
        """
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                # Ensure the loaded data has the expected structure
                if "metadata" in loaded_data and "files" in loaded_data:
                    self.db_data = loaded_data
                    logger.info(f"Loaded database with {len(self.db_data['files'])} files")
                else:
                    logger.warning("Database file has unexpected structure, starting fresh")
                    
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading database: {e}. Starting with empty database.")
        else:
            logger.info("No existing database found, creating new one")
            self.db_data["metadata"]["created_at"] = datetime.now().isoformat()
    
    def save_database(self) -> None:
        """
        Save the database to the JSON file.
        """
        try:
            self.db_data["metadata"]["last_updated"] = datetime.now().isoformat()
            self.db_data["metadata"]["file_count"] = len(self.db_data["files"])
            
            # Create backup of existing database
            if self.db_path.exists():
                backup_path = self.db_path.with_suffix('.json.backup')
                backup_path.write_text(self.db_path.read_text())
            
            # Write the updated database
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.db_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Database saved to {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            raise
    
    def add_file(self, file_path: Path, summary: str, content_length: int = 0) -> None:
        """
        Add or update a file entry in the database.
        
        Args:
            file_path (Path): Path to the markdown file
            summary (str): Generated summary of the file
            content_length (int): Length of the original content
        """
        file_key = str(file_path.resolve())
        
        # Get file metadata
        metadata = self._get_file_metadata(file_path)
        
        # Create file entry
        file_entry = {
            "file_path": file_key,
            "relative_path": str(file_path),
            "filename": file_path.name,
            "summary": summary,
            "content_length": content_length,
            "added_to_db": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "metadata": metadata
        }
        
        # Check if this is an update or new entry
        if file_key in self.db_data["files"]:
            # Preserve original add time
            file_entry["added_to_db"] = self.db_data["files"][file_key].get(
                "added_to_db", file_entry["added_to_db"]
            )
            logger.info(f"Updated existing file entry: {file_path.name}")
        else:
            logger.info(f"Added new file entry: {file_path.name}")
        
        self.db_data["files"][file_key] = file_entry
    
    def has_file_changed(self, file_path: Path) -> bool:
        """
        Check if a file has changed since it was last processed.
        
        Args:
            file_path (Path): Path to the file to check
            
        Returns:
            bool: True if the file has changed or is new
        """
        file_key = str(file_path.resolve())
        
        if file_key not in self.db_data["files"]:
            return True  # New file
        
        # Check if file hash has changed
        current_hash = self._calculate_file_hash(file_path)
        stored_hash = self.db_data["files"][file_key].get("metadata", {}).get("file_hash", "")
        
        return current_hash != stored_hash
    
    def get_file_entry(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get the database entry for a specific file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            Optional[Dict[str, Any]]: File entry or None if not found
        """
        file_key = str(file_path.resolve())
        return self.db_data["files"].get(file_key)
    
    def has_file(self, file_key: str) -> bool:
        """
        Check if a file exists in the database.
        
        Args:
            file_key (str): File key (resolved path)
            
        Returns:
            bool: True if file exists in database
        """
        return file_key in self.db_data["files"]
    
    def get_file_data(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file data by file key.
        
        Args:
            file_key (str): File key (resolved path)
            
        Returns:
            Optional[Dict[str, Any]]: File data or None if not found
        """
        return self.db_data["files"].get(file_key)
    
    def get_all_files_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all files as a dictionary with file keys.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of file key to file data
        """
        return self.db_data["files"]
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        Get all file entries from the database.
        
        Returns:
            List[Dict[str, Any]]: List of all file entries
        """
        return list(self.db_data["files"].values())
    
    def search_summaries(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Simple text search through file summaries.
        
        Args:
            query (str): Search query
            case_sensitive (bool): Whether to perform case-sensitive search
            
        Returns:
            List[Dict[str, Any]]: List of matching file entries
        """
        if not case_sensitive:
            query = query.lower()
        
        matches = []
        for file_entry in self.db_data["files"].values():
            summary = file_entry.get("summary", "")
            filename = file_entry.get("filename", "")
            
            if not case_sensitive:
                summary = summary.lower()
                filename = filename.lower()
            
            # Search in summary and filename
            if query in summary or query in filename:
                matches.append(file_entry)
        
        logger.info(f"Found {len(matches)} files matching query: '{query}'")
        return matches
    
    def remove_file(self, file_path: Path) -> bool:
        """
        Remove a file entry from the database.
        
        Args:
            file_path (Path): Path to the file to remove
            
        Returns:
            bool: True if the file was removed, False if it wasn't found
        """
        file_key = str(file_path.resolve())
        
        if file_key in self.db_data["files"]:
            del self.db_data["files"][file_key]
            logger.info(f"Removed file entry: {file_path.name}")
            return True
        else:
            logger.warning(f"File not found in database: {file_path.name}")
            return False
    
    def cleanup_missing_files(self) -> int:
        """
        Remove entries for files that no longer exist on disk.
        
        Returns:
            int: Number of entries removed
        """
        files_to_remove = []
        
        for file_key, file_entry in self.db_data["files"].items():
            file_path = Path(file_key)
            if not file_path.exists():
                files_to_remove.append(file_key)
        
        for file_key in files_to_remove:
            del self.db_data["files"][file_key]
        
        if files_to_remove:
            logger.info(f"Cleaned up {len(files_to_remove)} entries for missing files")
        
        return len(files_to_remove)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict[str, Any]: Database statistics
        """
        files = list(self.db_data["files"].values())
        
        if not files:
            return {
                "total_files": 0,
                "total_content_length": 0,
                "average_content_length": 0,
                "average_summary_length": 0,
                "newest_file": None,
                "oldest_file": None
            }
        
        content_lengths = [f.get("content_length", 0) for f in files]
        summary_lengths = [len(f.get("summary", "")) for f in files]
        add_times = [f.get("added_to_db", "") for f in files if f.get("added_to_db")]
        
        return {
            "total_files": len(files),
            "total_content_length": sum(content_lengths),
            "average_content_length": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
            "average_summary_length": sum(summary_lengths) / len(summary_lengths) if summary_lengths else 0,
            "newest_file": max(add_times) if add_times else None,
            "oldest_file": min(add_times) if add_times else None
        }


def main():
    """
    Command-line interface for database management.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage the knowledge base database")
    parser.add_argument("--db-path", default="data/knowledge_base.json",
                       help="Path to the database file")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all files in database")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search files by content")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--case-sensitive", action="store_true",
                              help="Perform case-sensitive search")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove entries for missing files")
    
    args = parser.parse_args()
    
    # Create database instance
    db = KnowledgeDatabase(args.db_path)
    
    if args.command == "list":
        files = db.get_all_files()
        print(f"Database contains {len(files)} files:")
        for file_entry in files:
            print(f"  {file_entry['filename']}: {file_entry['summary'][:100]}...")
    
    elif args.command == "search":
        matches = db.search_summaries(args.query, args.case_sensitive)
        print(f"Found {len(matches)} matches for '{args.query}':")
        for match in matches:
            print(f"  {match['filename']}: {match['summary']}")
    
    elif args.command == "stats":
        stats = db.get_statistics()
        print("Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif args.command == "cleanup":
        removed = db.cleanup_missing_files()
        db.save_database()
        print(f"Removed {removed} entries for missing files")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()