#!/usr/bin/env python3
"""
Test suite for the question_answerer module.

This module tests the question answering system that uses semantic search
to find relevant files and synthesizes answers using AI.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
import requests

# Import the module we're testing
from question_answerer import QuestionAnswerer


class TestQuestionAnswerer:
    """Test suite for QuestionAnswerer class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_knowledge_base.json"
        self.cache_path = Path(self.temp_dir) / "test_embeddings_cache.json"
        
        # Mock knowledge database
        self.mock_db = Mock()
        self.mock_db.get_all_files.return_value = [
            {
                "file_path": "/path/to/file1.md",
                "filename": "file1.md",
                "summary": "Test summary 1",
                "content_length": 100
            },
            {
                "file_path": "/path/to/file2.md",
                "filename": "file2.md",
                "summary": "Test summary 2",
                "content_length": 200
            }
        ]
        
        # Mock semantic search
        self.mock_search = Mock()
        self.mock_search.semantic_search.return_value = [
            {
                "filename": "file1.md",
                "file_path": "/path/to/file1.md",
                "summary": "Test summary 1",
                "similarity_score": 0.85
            }
        ]
        
        # Mock summarizer
        self.mock_summarizer = Mock()
        
        # Mock config
        self.mock_config = Mock()
        self.mock_config.api.openai_api_key = "test-api-key"
        self.mock_config.api.openai_model = "gpt-4"
        self.mock_config.paths.knowledge_base_path = self.db_path
        self.mock_config.paths.embeddings_cache_path = self.cache_path
        self.mock_config.processing.max_retries = 3
        self.mock_config.processing.retry_delay = 1.0
        
    def teardown_method(self):
        """Clean up after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_initialization_success(self, mock_summarizer_class, mock_search_class, 
                                  mock_db_class, mock_get_config):
        """Test successful initialization."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        assert qa.openai_api_key == "test-api-key"
        assert qa.model == "gpt-4"
        assert qa.max_context_length == 12000
        assert qa.max_retries == 3
        assert qa.retry_delay == 1.0
        
        # Check components were initialized
        mock_db_class.assert_called_once_with(str(self.db_path))
        mock_search_class.assert_called_once_with(str(self.cache_path))
        mock_summarizer_class.assert_called_once()
    
    @patch('question_answerer.get_config')
    def test_initialization_no_api_key(self, mock_get_config):
        """Test initialization fails without API key."""
        self.mock_config.api.openai_api_key = None
        mock_get_config.return_value = self.mock_config
        
        with pytest.raises(ValueError) as exc_info:
            QuestionAnswerer()
        
        assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_find_relevant_files(self, mock_summarizer_class, mock_search_class,
                                mock_db_class, mock_get_config):
        """Test finding relevant files."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Find relevant files
        results = qa.find_relevant_files("test query", top_k=3, similarity_threshold=0.7)
        
        assert len(results) == 1
        assert results[0]["filename"] == "file1.md"
        assert results[0]["similarity_score"] == 0.85
        
        # Check semantic search was called correctly
        self.mock_search.semantic_search.assert_called_once_with(
            "test query",
            self.mock_db,
            top_k=3,
            similarity_threshold=0.7
        )
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_read_file_content_success(self, mock_summarizer_class, mock_search_class,
                                     mock_db_class, mock_get_config):
        """Test reading file content."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Create test file
        test_file = Path(self.temp_dir) / "test.md"
        test_content = "# Test File\n\nThis is test content."
        test_file.write_text(test_content)
        
        # Read file
        content = qa.read_file_content(str(test_file))
        
        assert content == test_content
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_read_file_content_not_found(self, mock_summarizer_class, mock_search_class,
                                       mock_db_class, mock_get_config):
        """Test reading non-existent file."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Try to read non-existent file
        content = qa.read_file_content("/path/to/nonexistent.md")
        
        assert "[File not found]" in content
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_prepare_context(self, mock_summarizer_class, mock_search_class,
                           mock_db_class, mock_get_config):
        """Test context preparation from relevant files."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Create test files
        file1 = Path(self.temp_dir) / "file1.md"
        file1.write_text("# File 1\n\nContent of file 1.")
        
        file2 = Path(self.temp_dir) / "file2.md"
        file2.write_text("# File 2\n\nContent of file 2.")
        
        # Mock relevant files
        relevant_files = [
            {
                "filename": "file1.md",
                "file_path": str(file1),
                "summary": "Summary 1",
                "similarity_score": 0.9
            },
            {
                "filename": "file2.md",
                "file_path": str(file2),
                "summary": "Summary 2",
                "similarity_score": 0.8
            }
        ]
        
        # Prepare context
        context = qa.prepare_context(relevant_files, "test query")
        
        assert "test query" in context
        assert "file1.md" in context
        assert "file2.md" in context
        assert "Content of file 1" in context
        assert "Content of file 2" in context
        assert "Summary 1" in context
        assert "Summary 2" in context
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_prepare_context_truncation(self, mock_summarizer_class, mock_search_class,
                                      mock_db_class, mock_get_config):
        """Test context truncation when too long."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        qa.max_context_length = 100  # Set very low limit for testing
        
        # Create test file with long content
        test_file = Path(self.temp_dir) / "long.md"
        test_file.write_text("A" * 1000)  # Very long content
        
        relevant_files = [{
            "filename": "long.md",
            "file_path": str(test_file),
            "summary": "Long file",
            "similarity_score": 0.9
        }]
        
        # Prepare context
        context = qa.prepare_context(relevant_files, "test")
        
        # Context should be truncated
        assert len(context) < 1000
        assert "[truncated]" in context
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    @patch('requests.post')
    def test_synthesize_answer_success(self, mock_post, mock_summarizer_class, 
                                     mock_search_class, mock_db_class, mock_get_config):
        """Test successful answer synthesis."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "The answer is 42."
                }
            }]
        }
        mock_post.return_value = mock_response
        
        qa = QuestionAnswerer()
        
        # Synthesize answer
        answer = qa.synthesize_answer("What is the answer?", "Context with 42")
        
        assert answer == "The answer is 42."
        mock_post.assert_called_once()
        
        # Check request structure
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
        assert call_args[1]["json"]["model"] == "gpt-4"
        assert "What is the answer?" in str(call_args[1]["json"]["messages"])
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    @patch('requests.post')
    def test_synthesize_answer_rate_limit(self, mock_post, mock_summarizer_class,
                                        mock_search_class, mock_db_class, mock_get_config):
        """Test handling rate limit during synthesis."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        # Mock rate limit then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Success after retry"
                }
            }]
        }
        
        mock_post.side_effect = [mock_response_429, mock_response_200]
        
        qa = QuestionAnswerer()
        
        # Synthesize answer
        with patch('time.sleep'):  # Speed up test
            answer = qa.synthesize_answer("Test", "Context")
        
        assert answer == "Success after retry"
        assert mock_post.call_count == 2
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    @patch('requests.post')
    def test_synthesize_answer_failure(self, mock_post, mock_summarizer_class,
                                     mock_search_class, mock_db_class, mock_get_config):
        """Test synthesis failure after retries."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        # Mock error responses
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        qa = QuestionAnswerer()
        
        # Synthesize answer
        with patch('time.sleep'):  # Speed up test
            answer = qa.synthesize_answer("Test", "Context")
        
        assert answer == "I was unable to generate an answer due to an API error."
        assert mock_post.call_count == 3  # Max retries
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_answer_question_full_flow(self, mock_summarizer_class, mock_search_class,
                                     mock_db_class, mock_get_config):
        """Test the full question answering flow."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Create test file
        test_file = Path(self.temp_dir) / "test.md"
        test_file.write_text("# Test\n\nThe answer is 42.")
        
        # Mock search results
        self.mock_search.semantic_search.return_value = [{
            "filename": "test.md",
            "file_path": str(test_file),
            "summary": "Contains the answer",
            "similarity_score": 0.95
        }]
        
        # Mock synthesis
        with patch.object(qa, 'synthesize_answer') as mock_synthesize:
            mock_synthesize.return_value = "Based on the context, the answer is 42."
            
            # Answer question
            result = qa.answer_question("What is the answer?")
            
            assert result["answer"] == "Based on the context, the answer is 42."
            assert len(result["sources"]) == 1
            assert result["sources"][0]["filename"] == "test.md"
            assert result["sources"][0]["similarity_score"] == 0.95
            assert "context_length" in result
            assert result["files_searched"] > 0
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_answer_question_no_relevant_files(self, mock_summarizer_class, mock_search_class,
                                             mock_db_class, mock_get_config):
        """Test answering when no relevant files found."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Mock no search results
        self.mock_search.semantic_search.return_value = []
        
        # Answer question
        result = qa.answer_question("Obscure question")
        
        assert "couldn't find any relevant files" in result["answer"]
        assert result["sources"] == []
        assert result["files_searched"] > 0
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_interactive_qa_exit(self, mock_summarizer_class, mock_search_class,
                               mock_db_class, mock_get_config):
        """Test interactive QA mode exit commands."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Test various exit commands
        with patch('builtins.input', side_effect=['exit']):
            qa.interactive_qa()  # Should exit immediately
        
        with patch('builtins.input', side_effect=['quit']):
            qa.interactive_qa()  # Should exit immediately
        
        with patch('builtins.input', side_effect=['q']):
            qa.interactive_qa()  # Should exit immediately
    
    @patch('question_answerer.get_config')
    @patch('question_answerer.KnowledgeDatabase')
    @patch('question_answerer.SemanticSearch')
    @patch('question_answerer.MarkdownSummarizer')
    def test_interactive_qa_question(self, mock_summarizer_class, mock_search_class,
                                   mock_db_class, mock_get_config):
        """Test interactive QA with a question."""
        mock_get_config.return_value = self.mock_config
        mock_db_class.return_value = self.mock_db
        mock_search_class.return_value = self.mock_search
        mock_summarizer_class.return_value = self.mock_summarizer
        
        qa = QuestionAnswerer()
        
        # Mock answer_question
        with patch.object(qa, 'answer_question') as mock_answer:
            mock_answer.return_value = {
                "answer": "Test answer",
                "sources": [{"filename": "test.md", "similarity_score": 0.9}],
                "context_length": 100,
                "files_searched": 5
            }
            
            # Test with question then exit
            with patch('builtins.input', side_effect=['What is the test?', 'exit']):
                qa.interactive_qa()
                
                mock_answer.assert_called_once_with('What is the test?')


def test_question_answerer_integration():
    """Integration test for question answering system."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_kb.json"
        cache_path = Path(temp_dir) / "test_cache.json"
        
        # Create mock config
        mock_config = Mock()
        mock_config.api.openai_api_key = "test-key"
        mock_config.api.openai_model = "gpt-4"
        mock_config.paths.knowledge_base_path = db_path
        mock_config.paths.embeddings_cache_path = cache_path
        mock_config.processing.max_retries = 3
        mock_config.processing.retry_delay = 1.0
        
        # Create test database
        test_db = {
            "metadata": {"version": "1.0"},
            "files": {
                "test.md": {
                    "file_path": str(Path(temp_dir) / "test.md"),
                    "summary": "Test file about AI",
                    "content_length": 100,
                    "last_updated": "2024-01-01T10:00:00"
                }
            }
        }
        
        with open(db_path, 'w') as f:
            json.dump(test_db, f)
        
        # Create test file
        test_file = Path(temp_dir) / "test.md"
        test_file.write_text("# AI Document\n\nArtificial Intelligence is...")
        
        with patch('question_answerer.get_config') as mock_get_config:
            mock_get_config.return_value = mock_config
            
            # Mock components
            with patch('question_answerer.SemanticSearch') as mock_search_class:
                mock_search = Mock()
                mock_search.semantic_search.return_value = [{
                    "filename": "test.md",
                    "file_path": str(test_file),
                    "summary": "Test file about AI",
                    "similarity_score": 0.9
                }]
                mock_search_class.return_value = mock_search
                
                with patch('question_answerer.MarkdownSummarizer'):
                    # Initialize QA system
                    qa = QuestionAnswerer()
                    
                    # Test finding relevant files
                    files = qa.find_relevant_files("What is AI?")
                    assert len(files) == 1
                    assert files[0]["filename"] == "test.md"
                    
                    # Test reading file
                    content = qa.read_file_content(str(test_file))
                    assert "Artificial Intelligence" in content
                    
                    # Test context preparation
                    context = qa.prepare_context(files, "What is AI?")
                    assert "AI Document" in context
                    assert "Test file about AI" in context


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()