#!/usr/bin/env python3
"""
Unit tests for the Knowledge Base CLI interface.
"""

import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch, Mock, MagicMock, call
from pathlib import Path
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kb_cli import KnowledgeBaseCLI, create_parser, main, colorize, Colors


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Mock environment variables for all tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    # Clear cached modules to ensure fresh import
    if 'config' in sys.modules:
        del sys.modules['config']


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def cli():
    """Create a CLI instance for testing."""
    return KnowledgeBaseCLI()


@pytest.fixture
def mock_builder():
    """Create a mock KnowledgeBaseBuilder."""
    builder = Mock()
    builder.get_database_stats.return_value = {
        'total_files': 5,
        'total_content_length': 10000,
        'average_content_length': 2000,
        'average_summary_length': 200,
        'newest_file': 'new_file.md',
        'oldest_file': 'old_file.md'
    }
    builder.build_knowledge_base.return_value = {
        'duration_seconds': 1.5,
        'files_found': 10,
        'files_processed': 8,
        'files_failed': 2,
        'files_removed': 0
    }
    builder.search_knowledge_base.return_value = [
        {
            'filename': 'test1.md',
            'file_path': '/test/test1.md',
            'content_length': 1000,
            'summary': 'This is a test file summary'
        }
    ]
    builder.semantic_search_knowledge_base.return_value = [
        {
            'filename': 'test2.md',
            'file_path': '/test/test2.md',
            'content_length': 1500,
            'summary': 'Another test file summary',
            'similarity_score': 0.85
        }
    ]
    builder.answer_question.return_value = {
        'answer': 'This is a test answer',
        'source_files': [
            {'filename': 'source1.md', 'similarity_score': 0.9},
            {'filename': 'source2.md', 'similarity_score': 0.8}
        ]
    }
    builder.build_embeddings.return_value = 5
    return builder


class TestColorFunctions:
    """Test color and display functions."""
    
    def test_colorize(self):
        """Test colorize function."""
        text = "test"
        colored = colorize(text, Colors.GREEN)
        assert colored.startswith(Colors.GREEN)
        assert colored.endswith(Colors.ENDC)
        assert text in colored


class TestKnowledgeBaseCLI:
    """Test the main CLI class."""
    
    def test_initialization(self, cli):
        """Test CLI initialization."""
        assert cli.builder is None
        assert cli.logger is not None
    
    @patch('kb_cli.KnowledgeBaseBuilder')
    def test_initialize_builder_success(self, mock_kb_class, cli):
        """Test successful builder initialization."""
        mock_args = Mock()
        mock_args.directory = "/test"
        mock_args.db_path = "/test/db.json"
        mock_args.embeddings_cache = "/test/embeddings.json"
        mock_args.force_update = False
        
        result = cli.initialize_builder(mock_args)
        
        assert result is True
        assert cli.builder is not None
        mock_kb_class.assert_called_once_with(
            base_directory="/test",
            db_path="/test/db.json",
            embeddings_cache_path="/test/embeddings.json",
            force_update=False
        )
    
    @patch('kb_cli.KnowledgeBaseBuilder')
    @patch('builtins.print')
    def test_initialize_builder_failure(self, mock_print, mock_kb_class, cli):
        """Test builder initialization failure."""
        mock_kb_class.side_effect = Exception("Test error")
        mock_args = Mock()
        mock_args.directory = "/test"
        mock_args.db_path = "/test/db.json"
        mock_args.embeddings_cache = "/test/embeddings.json"
        
        result = cli.initialize_builder(mock_args)
        
        assert result is False
        assert cli.builder is None
        mock_print.assert_called_once()
        printed_text = mock_print.call_args[0][0]
        assert "Failed to initialize" in printed_text
    
    @patch('builtins.print')
    def test_cmd_build(self, mock_print, cli, mock_builder):
        """Test build command."""
        cli.builder = mock_builder
        mock_args = Mock()
        mock_args.directory = "/test"
        mock_args.db_path = "/test/db.json"
        mock_args.force_update = False
        
        cli.cmd_build(mock_args)
        
        mock_builder.build_knowledge_base.assert_called_once()
        
        # Check that build success message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        success_messages = [msg for msg in printed_calls if "Build completed successfully" in msg]
        assert len(success_messages) > 0
    
    @patch('builtins.print')
    def test_cmd_search(self, mock_print, cli, mock_builder):
        """Test search command."""
        cli.builder = mock_builder
        mock_args = Mock()
        mock_args.query = "test query"
        mock_args.case_sensitive = False
        
        cli.cmd_search(mock_args)
        
        mock_builder.search_knowledge_base.assert_called_once_with("test query", False)
        
        # Check that search results were printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        result_messages = [msg for msg in printed_calls if "Found 1 matching files" in msg]
        assert len(result_messages) > 0
    
    @patch('builtins.print')
    def test_cmd_semantic_search(self, mock_print, cli, mock_builder):
        """Test semantic search command."""
        cli.builder = mock_builder
        mock_args = Mock()
        mock_args.query = "semantic query"
        mock_args.top_k = 5
        mock_args.threshold = 0.7
        
        cli.cmd_semantic_search(mock_args)
        
        mock_builder.semantic_search_knowledge_base.assert_called_once_with("semantic query", 5, 0.7)
        
        # Check that semantic search results were printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        result_messages = [msg for msg in printed_calls if "Found 1 semantically similar files" in msg]
        assert len(result_messages) > 0
    
    @patch('builtins.print')
    def test_cmd_ask(self, mock_print, cli, mock_builder):
        """Test ask command."""
        cli.builder = mock_builder
        mock_args = Mock()
        mock_args.question = "What is this about?"
        mock_args.top_k = 5
        mock_args.threshold = 0.6
        
        cli.cmd_ask(mock_args)
        
        mock_builder.answer_question.assert_called_once_with("What is this about?", 5, 0.6)
        
        # Check that answer was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        answer_messages = [msg for msg in printed_calls if "This is a test answer" in msg]
        assert len(answer_messages) > 0
    
    @patch('builtins.print')
    def test_cmd_stats(self, mock_print, cli, mock_builder):
        """Test stats command."""
        cli.builder = mock_builder
        mock_args = Mock()
        
        cli.cmd_stats(mock_args)
        
        mock_builder.get_database_stats.assert_called_once()
        
        # Check that stats were printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        stats_messages = [msg for msg in printed_calls if "Total files: 5" in msg]
        assert len(stats_messages) > 0
    
    @patch('builtins.print')
    def test_cmd_embeddings(self, mock_print, cli, mock_builder):
        """Test embeddings command."""
        cli.builder = mock_builder
        mock_args = Mock()
        mock_args.force = False
        
        cli.cmd_embeddings(mock_args)
        
        mock_builder.build_embeddings.assert_called_once_with(False)
        
        # Check that embeddings success message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        success_messages = [msg for msg in printed_calls if "Created 5 new embeddings" in msg]
        assert len(success_messages) > 0
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cmd_interactive_help(self, mock_print, mock_input, cli, mock_builder):
        """Test interactive mode help command."""
        cli.builder = mock_builder
        mock_args = Mock()
        
        # Simulate user input: help command then exit
        mock_input.side_effect = ['/help', '/exit']
        
        cli.cmd_interactive(mock_args)
        
        # Check that help was displayed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        help_messages = [msg for msg in printed_calls if "Available commands" in msg]
        assert len(help_messages) > 0
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cmd_interactive_question(self, mock_print, mock_input, cli, mock_builder):
        """Test interactive mode with question."""
        cli.builder = mock_builder
        mock_args = Mock()
        
        # Simulate user input: question then exit
        mock_input.side_effect = ['What is this?', '/exit']
        
        cli.cmd_interactive(mock_args)
        
        # Check that question was processed
        mock_builder.answer_question.assert_called_with('What is this?')
        
        # Check that answer was displayed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        answer_messages = [msg for msg in printed_calls if "This is a test answer" in msg]
        assert len(answer_messages) > 0
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cmd_interactive_empty_input(self, mock_print, mock_input, cli, mock_builder):
        """Test interactive mode with empty input."""
        cli.builder = mock_builder
        mock_args = Mock()
        
        # Simulate user input: empty string then exit
        mock_input.side_effect = ['', '/exit']
        
        cli.cmd_interactive(mock_args)
        
        # Should not call answer_question for empty input
        mock_builder.answer_question.assert_not_called()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cmd_interactive_keyboard_interrupt(self, mock_print, mock_input, cli, mock_builder):
        """Test interactive mode with keyboard interrupt."""
        cli.builder = mock_builder
        mock_args = Mock()
        
        # Simulate keyboard interrupt
        mock_input.side_effect = KeyboardInterrupt()
        
        cli.cmd_interactive(mock_args)
        
        # Check that goodbye message was printed
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        goodbye_messages = [msg for msg in printed_calls if "Goodbye" in msg]
        assert len(goodbye_messages) > 0


class TestArgumentParser:
    """Test argument parsing functionality."""
    
    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None
        assert parser.description is not None
    
    def test_build_command(self):
        """Test build command parsing."""
        parser = create_parser()
        args = parser.parse_args(['build', '--force-update'])
        
        assert args.command == 'build'
        assert args.force_update is True
    
    def test_search_command(self):
        """Test search command parsing."""
        parser = create_parser()
        args = parser.parse_args(['search', 'test', '--case-sensitive'])
        
        assert args.command == 'search'
        assert args.query == 'test'
        assert args.case_sensitive is True
    
    def test_semantic_command(self):
        """Test semantic search command parsing."""
        parser = create_parser()
        args = parser.parse_args(['semantic', 'test semantic', '--top-k', '3', '--threshold', '0.8'])
        
        assert args.command == 'semantic'
        assert args.query == 'test semantic'
        assert args.top_k == 3
        assert args.threshold == 0.8
    
    def test_ask_command(self):
        """Test ask command parsing."""
        parser = create_parser()
        args = parser.parse_args(['ask', 'What is this?', '--top-k', '3'])
        
        assert args.command == 'ask'
        assert args.question == 'What is this?'
        assert args.top_k == 3
    
    def test_embeddings_command(self):
        """Test embeddings command parsing."""
        parser = create_parser()
        args = parser.parse_args(['embeddings', '--force'])
        
        assert args.command == 'embeddings'
        assert args.force is True
    
    def test_stats_command(self):
        """Test stats command parsing."""
        parser = create_parser()
        args = parser.parse_args(['stats'])
        
        assert args.command == 'stats'
    
    def test_interactive_command(self):
        """Test interactive command parsing."""
        parser = create_parser()
        args = parser.parse_args(['interactive'])
        
        assert args.command == 'interactive'


class TestMainFunction:
    """Test the main function."""
    
    @patch('kb_cli.setup_logging')
    @patch('kb_cli.KnowledgeBaseCLI')
    @patch('kb_cli.create_parser')
    def test_main_success(self, mock_parser, mock_cli_class, mock_setup_logging):
        """Test successful main function execution."""
        # Mock parser
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_args = Mock()
        mock_args.command = 'build'
        mock_args.directory = '/test'
        mock_args.db_path = '/test/db.json'
        mock_args.embeddings_cache = '/test/embeddings.json'
        mock_parser_instance.parse_args.return_value = mock_args
        
        # Mock CLI
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        mock_cli.initialize_builder.return_value = True
        mock_cli.cmd_build = Mock()
        
        result = main()
        
        assert result == 0
        mock_setup_logging.assert_called_once()
        mock_cli.initialize_builder.assert_called_once_with(mock_args)
        mock_cli.cmd_build.assert_called_once_with(mock_args)
    
    @patch('kb_cli.setup_logging')
    @patch('kb_cli.KnowledgeBaseCLI')
    @patch('kb_cli.create_parser')
    @patch('builtins.print')
    def test_main_unknown_command(self, mock_print, mock_parser, mock_cli_class, mock_setup_logging):
        """Test main function with unknown command."""
        # Mock parser
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_args = Mock()
        mock_args.command = 'unknown'
        mock_parser_instance.parse_args.return_value = mock_args
        
        # Mock CLI
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        mock_cli.initialize_builder.return_value = True
        
        result = main()
        
        assert result == 1
        mock_print.assert_called()
        error_message = mock_print.call_args[0][0]
        assert "Unknown command" in error_message
    
    @patch('kb_cli.setup_logging')
    @patch('kb_cli.KnowledgeBaseCLI')
    @patch('kb_cli.create_parser')
    def test_main_initialization_failure(self, mock_parser, mock_cli_class, mock_setup_logging):
        """Test main function with initialization failure."""
        # Mock parser
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_args = Mock()
        mock_args.command = 'build'
        mock_parser_instance.parse_args.return_value = mock_args
        
        # Mock CLI with initialization failure
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        mock_cli.initialize_builder.return_value = False
        
        result = main()
        
        assert result == 1
    
    @patch('kb_cli.setup_logging')
    @patch('kb_cli.KnowledgeBaseCLI')
    @patch('kb_cli.create_parser')
    @patch('builtins.print')
    def test_main_keyboard_interrupt(self, mock_print, mock_parser, mock_cli_class, mock_setup_logging):
        """Test main function with keyboard interrupt."""
        # Mock parser
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        mock_args = Mock()
        mock_args.command = 'build'
        mock_parser_instance.parse_args.return_value = mock_args
        
        # Mock CLI that raises KeyboardInterrupt
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        mock_cli.initialize_builder.return_value = True
        mock_cli.cmd_build.side_effect = KeyboardInterrupt()
        
        result = main()
        
        assert result == 1
        mock_print.assert_called()
        cancel_message = mock_print.call_args[0][0]
        assert "cancelled by user" in cancel_message


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('builtins.print')
    def test_search_no_results(self, mock_print, cli, mock_builder):
        """Test search command with no results."""
        cli.builder = mock_builder
        mock_builder.search_knowledge_base.return_value = []
        mock_args = Mock()
        mock_args.query = "nonexistent"
        mock_args.case_sensitive = False
        
        cli.cmd_search(mock_args)
        
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        no_results_messages = [msg for msg in printed_calls if "No files found" in msg]
        assert len(no_results_messages) > 0
    
    @patch('builtins.print')
    def test_ask_no_answer(self, mock_print, cli, mock_builder):
        """Test ask command with no answer."""
        cli.builder = mock_builder
        mock_builder.answer_question.return_value = {}
        mock_args = Mock()
        mock_args.question = "unanswerable"
        
        cli.cmd_ask(mock_args)
        
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        no_answer_messages = [msg for msg in printed_calls if "Failed to generate answer" in msg]
        assert len(no_answer_messages) > 0
    
    @patch('builtins.print')
    def test_stats_failure(self, mock_print, cli, mock_builder):
        """Test stats command with failure."""
        cli.builder = mock_builder
        mock_builder.get_database_stats.return_value = {}
        mock_args = Mock()
        
        cli.cmd_stats(mock_args)
        
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        failure_messages = [msg for msg in printed_calls if "Failed to retrieve statistics" in msg]
        assert len(failure_messages) > 0


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])