#!/usr/bin/env python3
"""
Integration tests for the knowledge base builder module.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest
from knowledge_base_builder import KnowledgeBaseBuilder


@pytest.fixture
def temp_directory():
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test markdown files
    (Path(temp_dir) / "README.md").write_text("# Test Project\nThis is a test readme file.")
    (Path(temp_dir) / "docs").mkdir()
    (Path(temp_dir) / "docs" / "guide.md").write_text("# User Guide\nThis is the user guide.")
    (Path(temp_dir) / "docs" / "api.md").write_text("# API Documentation\nAPI reference.")
    
    # Create subdirectory
    (Path(temp_dir) / "examples").mkdir()
    (Path(temp_dir) / "examples" / "example1.md").write_text("# Example 1\nFirst example.")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_openai_key():
    """Mock OpenAI API key."""
    original = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "test-api-key"
    yield
    if original:
        os.environ["OPENAI_API_KEY"] = original
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def temp_db_path():
    """Create temporary database path."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.close()
    yield temp_file.name
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def temp_embeddings_path():
    """Create temporary embeddings cache path."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.close()
    yield temp_file.name
    try:
        os.unlink(temp_file.name)
    except:
        pass


def test_initialization(temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test KnowledgeBaseBuilder initialization."""
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    assert builder.base_directory == Path(temp_directory).resolve()
    assert builder.force_update is False
    assert builder.scanner is not None
    assert builder.summarizer is not None
    assert builder.database is not None
    assert builder.semantic_search is not None
    assert builder.qa_system is not None


def test_scan_files(temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test file scanning functionality."""
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    files = builder.scan_files()
    
    assert len(files) == 4  # README.md, guide.md, api.md, example1.md
    file_names = [f.name for f in files]
    assert "README.md" in file_names
    assert "guide.md" in file_names
    assert "api.md" in file_names
    assert "example1.md" in file_names


@patch('knowledge_base_builder.MarkdownSummarizerV2.summarize_file')
def test_process_file(mock_summarize, temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test processing a single file."""
    # Mock summarizer response
    mock_summarize.return_value = {
        'summary': 'Test summary',
        'content_length': 100
    }
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    test_file = Path(temp_directory) / "README.md"
    success = builder.process_file(test_file)
    
    assert success is True
    mock_summarize.assert_called_once_with(test_file)
    
    # Check that file was added to database
    entry = builder.database.get_file_entry(test_file)
    assert entry is not None
    assert entry['summary'] == 'Test summary'


@patch('knowledge_base_builder.MarkdownSummarizerV2.summarize_file')
def test_process_file_failure(mock_summarize, temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test handling of file processing failure."""
    # Mock summarizer to raise exception
    mock_summarize.side_effect = Exception("Summarization failed")
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    test_file = Path(temp_directory) / "README.md"
    success = builder.process_file(test_file)
    
    assert success is False


@patch('knowledge_base_builder.MarkdownSummarizerV2.summarize_file')
def test_build_knowledge_base(mock_summarize, temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test building the complete knowledge base."""
    # Mock summarizer response
    mock_summarize.return_value = {
        'summary': 'Test summary',
        'content_length': 100
    }
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    # Remove delay for testing
    with patch('time.sleep'):
        result = builder.build_knowledge_base()
    
    assert result['status'] == 'completed'
    assert result['files_found'] == 4
    assert result['files_processed'] == 4
    assert result['files_failed'] == 0
    assert 'duration_seconds' in result
    
    # Verify database was saved
    assert Path(temp_db_path).exists()


def test_build_knowledge_base_no_files(temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test building knowledge base with no markdown files."""
    with tempfile.TemporaryDirectory() as empty_dir:
        builder = KnowledgeBaseBuilder(
            base_directory=empty_dir,
            db_path=temp_db_path,
            embeddings_cache_path=temp_embeddings_path
        )
        
        result = builder.build_knowledge_base()
        
        assert result['status'] == 'completed'
        assert result['files_found'] == 0
        assert result['files_processed'] == 0
        assert result['files_failed'] == 0


@patch('knowledge_base_builder.MarkdownSummarizerV2.summarize_file')
def test_search_knowledge_base(mock_summarize, temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test keyword search functionality."""
    # Setup: Build knowledge base first
    mock_summarize.return_value = {
        'summary': 'This is a test readme file with important information.',
        'content_length': 100
    }
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    # Process one file
    test_file = Path(temp_directory) / "README.md"
    builder.process_file(test_file)
    
    # Search for keyword
    results = builder.search_knowledge_base("readme")
    
    assert len(results) > 0
    assert results[0]['filename'] == "README.md"
    assert results[0]['search_type'] == "keyword"
    assert 'summary' in results[0]
    assert 'file_path' in results[0]


@patch('knowledge_base_builder.SemanticSearchV2.semantic_search')
def test_semantic_search_knowledge_base(mock_semantic_search, temp_directory, temp_db_path, 
                                       temp_embeddings_path, mock_openai_key):
    """Test semantic search functionality."""
    # Mock semantic search results
    mock_semantic_search.return_value = [
        {
            'filename': 'README.md',
            'file_path': str(Path(temp_directory) / "README.md"),
            'summary': 'Test summary',
            'content_length': 100,
            'similarity_score': 0.95
        }
    ]
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    results = builder.semantic_search_knowledge_base("test query", top_k=5)
    
    assert len(results) == 1
    assert results[0]['filename'] == 'README.md'
    assert results[0]['search_type'] == 'semantic'
    assert results[0]['similarity_score'] == 0.95


def test_semantic_search_failure(temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test handling of semantic search failure."""
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    # Mock semantic search to raise exception
    with patch.object(builder.semantic_search, 'semantic_search', side_effect=Exception("Search failed")):
        results = builder.semantic_search_knowledge_base("test query")
        
        assert results == []


@patch('knowledge_base_builder.SemanticSearchV2.build_embeddings_for_database')
def test_build_embeddings(mock_build_embeddings, temp_directory, temp_db_path, 
                         temp_embeddings_path, mock_openai_key):
    """Test building embeddings."""
    mock_build_embeddings.return_value = 4  # Number of embeddings created
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    count = builder.build_embeddings()
    
    assert count == 4
    mock_build_embeddings.assert_called_once_with(builder.database, False)


@patch('knowledge_base_builder.QuestionAnswerer.answer_question')
def test_answer_question(mock_answer, temp_directory, temp_db_path, 
                        temp_embeddings_path, mock_openai_key):
    """Test question answering functionality."""
    mock_answer.return_value = {
        'answer': 'Test answer',
        'sources': ['README.md'],
        'confidence': 0.9
    }
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    result = builder.answer_question("What is this project about?")
    
    assert result['answer'] == 'Test answer'
    assert 'README.md' in result['sources']
    mock_answer.assert_called_once_with("What is this project about?", 5, 0.6)


@patch('knowledge_base_builder.MarkdownSummarizerV2.summarize_file')
def test_force_update(mock_summarize, temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test force update functionality."""
    mock_summarize.return_value = {
        'summary': 'First summary',
        'content_length': 100
    }
    
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path,
        force_update=False
    )
    
    test_file = Path(temp_directory) / "README.md"
    
    # Process file first time
    builder.process_file(test_file)
    assert mock_summarize.call_count == 1
    
    # Process again without force update - should skip
    builder.process_file(test_file)
    assert mock_summarize.call_count == 1  # No additional call
    
    # Process with force update
    builder.force_update = True
    builder.process_file(test_file)
    assert mock_summarize.call_count == 2  # Additional call made


def test_get_database_stats(temp_directory, temp_db_path, temp_embeddings_path, mock_openai_key):
    """Test getting database statistics."""
    builder = KnowledgeBaseBuilder(
        base_directory=temp_directory,
        db_path=temp_db_path,
        embeddings_cache_path=temp_embeddings_path
    )
    
    stats = builder.get_database_stats()
    
    assert 'total_files' in stats
    assert 'total_content_length' in stats
    assert 'average_content_length' in stats
    assert 'average_summary_length' in stats


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()