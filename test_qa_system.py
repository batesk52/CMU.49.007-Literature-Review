#!/usr/bin/env python3
"""
Test script for question answering system functionality.
"""

import os
import tempfile
from pathlib import Path
from question_answerer import QuestionAnswerer
from knowledge_database import KnowledgeDatabase

def test_qa_initialization():
    """Test that the QA system can be initialized without API credentials."""
    # Import config module to reset it
    from config import reset_config
    
    # Test without API key to check error handling
    original_key = os.environ.get("OPENAI_API_KEY")
    
    # Force remove the API key even if set by fixtures
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    # Clear cached modules to ensure fresh import
    import sys
    if 'question_answerer' in sys.modules:
        del sys.modules['question_answerer']
    
    # Reset the global config to ensure it re-reads environment
    reset_config()
    
    try:
        # Re-import to get fresh instance
        from question_answerer import QuestionAnswerer
        qa = QuestionAnswerer()
        print("ERROR: Should have failed without API key")
        # For pytest compatibility
        assert False, "Should have failed without API key"
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            print("✓ Correctly raised ValueError for missing API key")
            # Test passed - do nothing
        else:
            print(f"✗ Unexpected error: {e}")
            # For pytest compatibility
            if __name__ != "__main__":
                raise
            assert False, f"Unexpected error: {e}"
    finally:
        # Restore API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        else:
            # Restore the test key if we're in a test environment
            os.environ["OPENAI_API_KEY"] = "test-api-key"
        # Reset config again to pick up restored environment
        reset_config()

def test_file_reading():
    """Test file reading functionality."""
    # Import config module to reset it
    from config import reset_config
    
    # Set dummy API key for testing
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Reset config to pick up the test key
    reset_config()
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        tmp_db_path = tmp_file.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_cache:
        tmp_cache_path = tmp_cache.name
    
    try:
        qa = QuestionAnswerer(tmp_db_path, tmp_cache_path)
        print("✓ QuestionAnswerer initialized with test API key")
        
        # Test file reading
        readme_path = "README.md"
        if Path(readme_path).exists():
            content = qa.read_file_content(readme_path)
            if content and len(content) > 0:
                print("✓ Successfully read file content")
            else:
                print("✗ Failed to read file content")
                assert False, "Failed to read file content"
        
        # Test context preparation (with empty files list)
        context = qa.prepare_context([], "test query")
        if context == "":
            print("✓ Context preparation works with empty input")
        else:
            print("✗ Context preparation failed with empty input")
            # For pytest compatibility
            assert False, "Context preparation failed with empty input"
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        # For pytest compatibility
        if __name__ != "__main__":
            raise
        assert False, f"Test failed with error: {e}"
        
    finally:
        # Clean up
        try:
            os.unlink(tmp_db_path)
            os.unlink(tmp_cache_path)
        except:
            pass
        
        # Restore original API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        # Reset config
        reset_config()

def main():
    """Run all QA system tests."""
    print("Running question answering system tests...\n")
    
    tests_passed = 0
    total_tests = 2
    
    try:
        test_qa_initialization()
        tests_passed += 1
    except AssertionError:
        pass
    
    try:
        test_file_reading()
        tests_passed += 1
    except AssertionError:
        pass
    
    print(f"\nTests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! The question answering system is ready.")
        print("\nNote: Full functionality requires OPENAI_API_KEY and a populated knowledge base.")
        return 0
    else:
        print("✗ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())