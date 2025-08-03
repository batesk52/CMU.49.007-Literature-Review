#!/usr/bin/env python3
"""
Test script for knowledge database functionality.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from knowledge_database import KnowledgeDatabase

def test_database_operations():
    """Test basic database operations."""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        tmp_db_path = tmp_file.name
    
    try:
        # Initialize database
        db = KnowledgeDatabase(tmp_db_path)
        
        # Test adding a file
        test_file = Path("README.md")
        assert test_file.exists(), "README.md not found for testing"
        
        db.add_file(test_file, "Test summary for README file", 1000)
        
        # Test retrieving the file
        entry = db.get_file_entry(test_file)
        assert entry is not None, "Failed to retrieve file from database"
        assert entry["summary"] == "Test summary for README file", "Retrieved summary doesn't match"
        
        # Test search functionality
        matches = db.search_summaries("README")
        assert len(matches) > 0, "Search functionality failed"
        
        # Test file change detection
        assert not db.has_file_changed(test_file), "File change detection failed"
        
        # Test saving and loading
        db.save_database()
        
        # Create new instance and load
        db2 = KnowledgeDatabase(tmp_db_path)
        entry2 = db2.get_file_entry(test_file)
        assert entry2 is not None, "Database loading failed"
        assert entry2["summary"] == "Test summary for README file", "Loaded summary doesn't match"
        
        # Test statistics
        stats = db.get_statistics()
        assert stats["total_files"] == 1, "Statistics calculation failed"
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_db_path)
        except:
            pass

def main():
    """Run all database tests."""
    print("Running knowledge database tests...\n")
    
    tests_passed = 0
    total_tests = 1
    
    if test_database_operations():
        tests_passed += 1
    
    print(f"\nTests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! The database module is ready.")
        return 0
    else:
        print("✗ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())