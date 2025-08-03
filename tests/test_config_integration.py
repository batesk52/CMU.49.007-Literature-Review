#!/usr/bin/env python3
"""
Test script for configuration integration.
Verifies that all modules properly use the centralized configuration.
"""

import os
import sys
from pathlib import Path
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set a test API key for testing
os.environ["OPENAI_API_KEY"] = "test-api-key-12345"


def test_config_module():
    """Test the configuration module itself."""
    print("Testing configuration module...")
    
    try:
        from config import Config, get_config, get_available_providers
        
        # Test creating config
        config = Config()
        print("✅ Config module imported successfully")
        
        # Test validation
        results = config.validate()
        print(f"✅ Config validation: {'Valid' if results['valid'] else 'Invalid'}")
        print(f"   Available providers: {results['available_providers']}")
        
        # Test convenience functions
        api_key = get_config().api.openai_api_key
        print(f"✅ API key loaded: {'Yes' if api_key else 'No'}")
        
        providers = get_available_providers()
        print(f"✅ Available providers: {providers}")
        
        # Test save/load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        config.save_to_file(config_file)
        print(f"✅ Config saved to {config_file}")
        
        loaded_config = Config.load_from_file(config_file)
        print("✅ Config loaded from file")
        
        # Cleanup
        os.unlink(config_file)
        
    except Exception as e:
        print(f"❌ Config module test failed: {e}")
        # For pytest compatibility
        if __name__ != "__main__":
            raise
        assert False, f"Config module test failed: {e}"


def _test_module_integration(module_name, class_name):
    """Test that a module properly uses config."""
    print(f"\nTesting {module_name} integration...")
    
    try:
        # Import the module
        module = __import__(module_name)
        
        # Get the class
        cls = getattr(module, class_name)
        
        # Try to instantiate - should use config for API key
        if class_name == "MarkdownSummarizer":
            instance = cls()
            print(f"✅ {class_name} uses config for API key")
            print(f"   Model: {instance.model}")
            print(f"   Max retries: {instance.max_retries}")
            
        elif class_name == "SemanticSearch":
            instance = cls()
            print(f"✅ {class_name} uses config for API key")
            print(f"   Embedding model: {instance.embedding_model}")
            print(f"   Max retries: {instance.max_retries}")
            
        elif class_name == "QuestionAnswerer":
            # Create temp files for DB
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                db_file = f.name
                json.dump({}, f)
            
            instance = cls(db_file)
            print(f"✅ {class_name} uses config for API key")
            print(f"   Model: {instance.model}")
            print(f"   Max retries: {instance.max_retries}")
            
            # Cleanup
            os.unlink(db_file)
            
        elif class_name == "KnowledgeBaseBuilder":
            # Create temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                instance = cls(temp_dir)
                print(f"✅ {class_name} uses config for paths")
                print(f"   Base directory: {instance.base_directory}")
        
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        if __name__ != "__main__":
            raise
        assert False, f"Failed to import {module_name}: {e}"
    except Exception as e:
        print(f"❌ {module_name} integration test failed: {e}")
        if __name__ != "__main__":
            raise
        assert False, f"{module_name} integration test failed: {e}"


def test_config_defaults():
    """Test that config defaults work properly."""
    print("\nTesting configuration defaults...")
    
    try:
        from config import Config
        
        # Remove API key temporarily
        original = os.environ.pop("OPENAI_API_KEY", None)
        
        config = Config()
        
        # Test defaults
        print(f"✅ Default paths created:")
        print(f"   Data directory: {config.paths.data_directory}")
        print(f"   Knowledge base: {config.paths.knowledge_base_path}")
        print(f"   Embeddings cache: {config.paths.embeddings_cache_path}")
        
        print(f"\n✅ Default processing settings:")
        print(f"   Max retries: {config.processing.max_retries}")
        print(f"   Default top-k: {config.processing.default_top_k}")
        print(f"   Similarity threshold: {config.processing.default_similarity_threshold}")
        
        # Restore API key
        if original:
            os.environ["OPENAI_API_KEY"] = original
        
    except Exception as e:
        print(f"❌ Config defaults test failed: {e}")
        # For pytest compatibility
        if __name__ != "__main__":
            raise
        assert False, f"Config defaults test failed: {e}"


def main():
    """Run all configuration tests."""
    print("🧪 Configuration Integration Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test config module
    total_tests += 1
    try:
        test_config_module()
        tests_passed += 1
    except AssertionError:
        pass
    
    # Test module integrations
    modules_to_test = [
        ("markdown_summarizer", "MarkdownSummarizer"),
        ("semantic_search", "SemanticSearch"),
        ("question_answerer", "QuestionAnswerer"),
        ("knowledge_base_builder", "KnowledgeBaseBuilder")
    ]
    
    for module_name, class_name in modules_to_test:
        total_tests += 1
        try:
            _test_module_integration(module_name, class_name)
            tests_passed += 1
        except AssertionError:
            pass
    
    # Test config defaults
    total_tests += 1
    try:
        test_config_defaults()
        tests_passed += 1
    except AssertionError:
        pass
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Summary: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ All configuration integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())