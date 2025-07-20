#!/usr/bin/env python3
"""
Test script for error handling and logging functionality.
"""

import os
import tempfile
import logging
import pytest
from pathlib import Path
from error_handler import (
    setup_logging, get_logger, error_handler, safe_execute, 
    validate_environment, KnowledgeBaseLogger
)

def test_logging_setup():
    """Test logging setup functionality."""
    # Create temporary log directory
    with tempfile.TemporaryDirectory() as temp_dir:
        logger_instance = setup_logging(
            log_level="DEBUG",
            log_dir=temp_dir,
            enable_file_logging=True,
            enable_error_tracking=True
        )
        
        assert logger_instance is not None, "Logging setup failed"
        assert isinstance(logger_instance, KnowledgeBaseLogger), "Logger is not a KnowledgeBaseLogger instance"
        
        # Test that we can get the global logger
        global_logger = get_logger()
        assert global_logger is logger_instance, "Global logger retrieval failed"

def test_error_decorator():
    """Test the error handler decorator."""
    # Set up logging for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        setup_logging(log_dir=temp_dir)
        
        @error_handler
        def test_function_success():
            return "success"
        
        @error_handler
        def test_function_error():
            raise ValueError("Test error")
        
        # Test successful function
        result = test_function_success()
        assert result == "success", "Decorator failed with successful functions"
        
        # Test function that raises error
        with pytest.raises(ValueError) as exc_info:
            test_function_error()
        assert "Test error" in str(exc_info.value), "Decorator modified the error incorrectly"

def test_safe_execute():
    """Test safe execution functionality."""
    # Function that succeeds
    def success_function():
        return "success"
    
    # Function that fails
    def fail_function():
        raise RuntimeError("Test failure")
    
    # Test successful execution
    result = safe_execute(success_function, default_return="default")
    assert result == "success", "Safe execute failed with successful functions"
    
    # Test failed execution
    result = safe_execute(fail_function, default_return="default")
    assert result == "default", "Safe execute failed to return default on failure"

def test_error_tracking():
    """Test error tracking functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        logger_instance = setup_logging(
            log_dir=temp_dir,
            enable_error_tracking=True
        )
        
        # Track a test error
        test_error = ValueError("Test tracking error")
        test_context = {"test_key": "test_value"}
        
        logger_instance.track_error(test_error, test_context)
        
        # Check error summary
        summary = logger_instance.get_error_summary()
        assert summary["total_errors"] == 1, f"Error tracking count incorrect: {summary['total_errors']}"
        assert "ValueError" in summary["error_types"], "Error types not tracked correctly"
        
        # Test error report generation
        report_path = logger_instance.save_error_report()
        assert Path(report_path).exists(), "Error report generation failed"

def test_environment_validation():
    """Test environment validation."""
    # Run validation
    results = validate_environment()
    
    # Check that we get a proper validation result structure
    required_keys = ["valid", "warnings", "errors", "environment_variables", "directories", "dependencies"]
    for key in required_keys:
        assert key in results, f"Missing key in validation results: {key}"
    
    # Check that OPENAI_API_KEY is checked
    assert "OPENAI_API_KEY" in results["environment_variables"], "OPENAI_API_KEY validation missing"

def main():
    """Run all error handling and logging tests."""
    print("Running error handling and logging tests...\n")
    
    tests = [
        test_logging_setup,
        test_error_decorator,
        test_safe_execute,
        test_error_tracking,
        test_environment_validation
    ]
    
    tests_passed = 0
    total_tests = len(tests)
    
    for test_func in tests:
        if test_func():
            tests_passed += 1
        print()  # Add spacing between tests
    
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All error handling and logging tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())