#!/usr/bin/env python3
"""
Test script for markdown summarizer functionality.
"""

import os
from pathlib import Path
from markdown_summarizer import MarkdownSummarizer

def test_file_reading():
    """Test that we can read markdown files correctly."""
    # Test with README.md
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md not found"
    
    # Create summarizer without API key for testing file reading
    original_key = os.environ.get("OPENAI_API_KEY")
    try:
        # Temporarily set a dummy API key to bypass the check
        os.environ["OPENAI_API_KEY"] = "test-key"
        summarizer = MarkdownSummarizer()
        
        # Test file reading
        content = summarizer.read_markdown_file(readme_path)
        assert len(content) > 0, "Failed to read content from README.md"
        
        # Test content truncation
        long_content = "x" * 20000
        truncated = summarizer.truncate_content(long_content)
        assert len(truncated) < len(long_content), "Content truncation failed"
        # Account for the "[Content truncated...]" suffix
        assert len(truncated) <= 15030, "Truncated content is too long"
        assert "[Content truncated...]" in truncated, "Truncation message missing"
        
    finally:
        # Restore original API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

def main():
    """Run all tests."""
    print("Running markdown summarizer tests...\n")
    
    tests_passed = 0
    total_tests = 1
    
    if test_file_reading():
        tests_passed += 1
    
    print(f"\nTests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! The summarizer module is ready.")
        return 0
    else:
        print("✗ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())