#!/usr/bin/env python3
"""
Test suite for the document_ingester module.

This module tests the document ingestion functionality including PDF and EPUB
extraction, content processing, and markdown summary generation.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module we're testing
from document_ingester import DocumentIngester


class TestDocumentIngester:
    """Test suite for DocumentIngester class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"
        
        # Mock the API provider
        self.mock_provider = Mock()
        self.mock_provider.generate_summary.return_value = {
            'summary': 'Test summary of the document',
            'key_points': ['Point 1', 'Point 2', 'Point 3'],
            'content_type': 'academic'
        }
        
    def teardown_method(self):
        """Clean up after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_initialization(self, mock_factory):
        """Test DocumentIngester initialization."""
        mock_factory.return_value = self.mock_provider
        
        ingester = DocumentIngester(
            output_dir=str(self.output_dir),
            provider_name="openai"
        )
        
        # Check that directories were created
        assert ingester.output_dir.exists()
        assert (ingester.output_dir / "by_type" / "pdfs").exists()
        assert (ingester.output_dir / "by_type" / "ebooks").exists()
        assert (ingester.output_dir / "by_type" / "documents").exists()
        assert (ingester.output_dir / "by_category" / "academic").exists()
        assert (ingester.output_dir / "by_category" / "technical").exists()
        assert (ingester.output_dir / "by_category" / "reference").exists()
        assert (ingester.output_dir / "metadata").exists()
        
        # Check provider initialization
        mock_factory.assert_called_once_with("openai")
        assert ingester.provider == self.mock_provider
        assert ingester.provider_name == "openai"
        
        # Check processing log initialization
        assert isinstance(ingester.processing_log, dict)
        assert "processed_files" in ingester.processing_log
        assert "statistics" in ingester.processing_log
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_load_existing_processing_log(self, mock_factory):
        """Test loading an existing processing log."""
        mock_factory.return_value = self.mock_provider
        
        # Create a mock processing log
        (self.output_dir / "metadata").mkdir(parents=True)
        log_path = self.output_dir / "metadata" / "processing_log.json"
        
        existing_log = {
            "processed_files": {
                "test.pdf": {
                    "hash": "abc123",
                    "processed_at": "2024-01-01T10:00:00"
                }
            },
            "statistics": {
                "total_processed": 1,
                "by_type": {"PDF": 1},
                "last_updated": "2024-01-01T10:00:00"
            }
        }
        
        with open(log_path, 'w') as f:
            json.dump(existing_log, f)
        
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        assert ingester.processing_log["processed_files"]["test.pdf"]["hash"] == "abc123"
        assert ingester.processing_log["statistics"]["total_processed"] == 1
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_get_file_hash(self, mock_factory):
        """Test file hash calculation."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create a test file
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("Test content for hashing")
        
        # Calculate hash
        hash1 = ingester._get_file_hash(test_file)
        assert len(hash1) == 32  # MD5 hash length
        
        # Same content should produce same hash
        hash2 = ingester._get_file_hash(test_file)
        assert hash1 == hash2
        
        # Different content should produce different hash
        test_file.write_text("Different content")
        hash3 = ingester._get_file_hash(test_file)
        assert hash1 != hash3
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    @patch('document_ingester.PyPDF2.PdfReader')
    def test_extract_pdf_content_success(self, mock_pdf_reader, mock_factory):
        """Test successful PDF content extraction."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Mock PDF reader
        mock_reader = Mock()
        mock_pdf_reader.return_value = mock_reader
        
        # Mock metadata
        mock_reader.metadata = {
            '/Title': 'Test PDF Document',
            '/Author': 'Test Author'
        }
        
        # Mock pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"
        mock_reader.pages = [mock_page1, mock_page2]
        
        # Create test PDF file
        test_pdf = Path(self.temp_dir) / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")
        
        # Extract content
        result = ingester._extract_pdf_content(test_pdf)
        
        assert result is not None
        assert result["metadata"]["title"] == "Test PDF Document"
        assert result["metadata"]["author"] == "Test Author"
        assert result["metadata"]["pages"] == 2
        assert result["metadata"]["type"] == "PDF"
        assert len(result["pages"]) == 2
        assert result["pages"][0]["text"] == "Page 1 content"
        assert result["pages"][1]["text"] == "Page 2 content"
        assert "Page 1 content" in result["full_text"]
        assert "Page 2 content" in result["full_text"]
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    @patch('document_ingester.PyPDF2.PdfReader')
    def test_extract_pdf_content_failure(self, mock_pdf_reader, mock_factory):
        """Test PDF extraction with errors."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Mock PDF reader to raise exception
        mock_pdf_reader.side_effect = Exception("PDF reading failed")
        
        # Create test PDF file
        test_pdf = Path(self.temp_dir) / "corrupted.pdf"
        test_pdf.write_bytes(b"Corrupted PDF")
        
        # Extract content should handle error gracefully
        result = ingester._extract_pdf_content(test_pdf)
        assert result is None
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    @patch('document_ingester.epub.read_epub')
    def test_extract_epub_content_success(self, mock_epub_read, mock_factory):
        """Test successful EPUB content extraction."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Mock EPUB book
        mock_book = Mock()
        mock_epub_read.return_value = mock_book
        
        # Mock metadata
        mock_book.get_metadata.side_effect = lambda ns, key: {
            ('DC', 'title'): [('Test EPUB Book',)],
            ('DC', 'creator'): [('Test Author',)]
        }.get((ns, key), [])
        
        # Mock chapters
        mock_chapter1 = Mock()
        mock_chapter1.get_type.return_value = 9  # ITEM_DOCUMENT value
        mock_chapter1.get_body_content.return_value = b'<html><body><p>Chapter 1 content</p></body></html>'
        mock_chapter1.get_name.return_value = 'chapter1.xhtml'
        
        mock_chapter2 = Mock()
        mock_chapter2.get_type.return_value = 9  # ITEM_DOCUMENT value
        mock_chapter2.get_body_content.return_value = b'<html><body><p>Chapter 2 content</p></body></html>'
        mock_chapter2.get_name.return_value = 'chapter2.xhtml'
        
        mock_book.items = [mock_chapter1, mock_chapter2]
        
        # Create test EPUB file
        test_epub = Path(self.temp_dir) / "test.epub"
        test_epub.write_bytes(b"Mock EPUB content")
        
        # Extract content
        result = ingester._extract_epub_content(test_epub)
        
        assert result is not None
        assert result["metadata"]["title"] == "Test EPUB Book"
        assert result["metadata"]["author"] == "Test Author"
        assert result["metadata"]["type"] == "EPUB"
        assert len(result["chapters"]) == 2
        assert "Chapter 1 content" in result["full_text"]
        assert "Chapter 2 content" in result["full_text"]
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_extract_text_content(self, mock_factory):
        """Test text file content extraction."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test text file
        test_txt = Path(self.temp_dir) / "test.txt"
        test_content = "This is a test text file.\nWith multiple lines.\nAnd some content."
        test_txt.write_text(test_content)
        
        # Extract content
        result = ingester._extract_text_content(test_txt)
        
        assert result is not None
        assert result["metadata"]["title"] == "test"
        assert result["metadata"]["type"] == "Text"
        assert result["full_text"] == test_content
        assert result["extraction_method"] == "direct"
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_generate_markdown_summary(self, mock_factory):
        """Test markdown summary generation."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Mock document content
        doc_content = {
            "metadata": {
                "title": "Test Document",
                "author": "Test Author",
                "type": "PDF",
                "pages": 10
            },
            "full_text": "This is the full text content of the document.",
            "extraction_method": "PyPDF2"
        }
        
        # Generate summary
        test_file = Path(self.temp_dir) / "test.pdf"
        markdown = ingester._generate_markdown_summary(doc_content, test_file)
        
        assert markdown is not None
        assert isinstance(markdown, str)
        
        # Check markdown content structure
        assert "# Test Document" in markdown
        assert "Test Author" in markdown
        assert "Test summary of the document" in markdown
        assert "Point 1" in markdown
        assert "Point 2" in markdown
        assert "Point 3" in markdown
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_save_markdown_summary(self, mock_factory):
        """Test saving markdown summary to disk."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test data
        markdown_content = "# Test Summary\n\nThis is a test summary."
        metadata = {
            "title": "Test Document",
            "type": "PDF",
            "category": "academic"
        }
        original_path = Path(self.temp_dir) / "test.pdf"
        
        # Save summary
        file_path = ingester._save_markdown_summary(markdown_content, metadata, original_path)
        
        assert file_path is not None
        assert file_path.exists()
        assert file_path.suffix == ".md"
        
        # Check file content
        content = file_path.read_text()
        assert "# Test Summary" in content
        assert "This is a test summary." in content
        
        # Check file location
        assert "by_type/pdfs" in str(file_path)
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_process_document_new_file(self, mock_factory):
        """Test processing a new document."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test PDF file
        test_pdf = Path(self.temp_dir) / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")
        
        # Mock extraction
        with patch.object(ingester, '_extract_pdf_content') as mock_extract:
            mock_extract.return_value = {
                "metadata": {"title": "Test", "type": "PDF"},
                "full_text": "Test content",
                "extraction_method": "PyPDF2"
            }
            
            # Process document
            result = ingester.process_document(test_pdf)
            
            assert result["status"] == "success"
            assert result["file"] == str(test_pdf)
            assert "summary_path" in result
            assert result["cached"] is False
            
            # Check processing log was updated
            assert str(test_pdf) in ingester.processing_log["processed_files"]
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_process_document_cached(self, mock_factory):
        """Test processing a cached document."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test file
        test_pdf = Path(self.temp_dir) / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")
        
        # Add to processing log
        file_hash = ingester._get_file_hash(test_pdf)
        ingester.processing_log["processed_files"][str(test_pdf)] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "summary_path": "test_summary.md"
        }
        
        # Mock summary file existence
        summary_path = ingester.output_dir / "by_type" / "pdfs" / "test_summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("Existing summary")
        
        # Process document (should be cached)
        result = ingester.process_document(test_pdf)
        
        assert result["status"] == "cached"
        assert result["cached"] is True
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_process_document_force_regenerate(self, mock_factory):
        """Test force regenerating a document."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test file
        test_pdf = Path(self.temp_dir) / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")
        
        # Add to processing log
        file_hash = ingester._get_file_hash(test_pdf)
        ingester.processing_log["processed_files"][str(test_pdf)] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat()
        }
        
        # Mock extraction
        with patch.object(ingester, '_extract_pdf_content') as mock_extract:
            mock_extract.return_value = {
                "metadata": {"title": "Test", "type": "PDF"},
                "full_text": "Test content",
                "extraction_method": "PyPDF2"
            }
            
            # Process with force=True
            result = ingester.process_document(test_pdf, force=True)
            
            assert result["status"] == "success"
            assert result["cached"] is False
            mock_extract.assert_called_once()
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_process_directory(self, mock_factory):
        """Test processing a directory of documents."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test files
        test_dir = Path(self.temp_dir) / "docs"
        test_dir.mkdir()
        
        (test_dir / "doc1.pdf").write_bytes(b"PDF 1")
        (test_dir / "doc2.txt").write_text("Text file")
        (test_dir / "doc3.epub").write_bytes(b"EPUB")
        (test_dir / "image.jpg").write_bytes(b"Not a document")
        
        # Create subdirectory
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "doc4.pdf").write_bytes(b"PDF 2")
        
        # Mock process_document
        with patch.object(ingester, 'process_document') as mock_process:
            mock_process.return_value = {"status": "success", "cached": False}
            
            # Process directory
            results = ingester.process_directory(test_dir, recursive=True)
            
            assert results["total_files"] == 4  # Should find 4 documents
            assert results["processed"] == 4
            assert results["failed"] == 0
            assert mock_process.call_count == 4
            
            # Check that non-recursive works
            results = ingester.process_directory(test_dir, recursive=False)
            assert results["total_files"] == 3  # Should not include subdirectory
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_process_directory_with_patterns(self, mock_factory):
        """Test processing directory with file patterns."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Create test files
        test_dir = Path(self.temp_dir) / "docs"
        test_dir.mkdir()
        
        (test_dir / "doc1.pdf").write_bytes(b"PDF 1")
        (test_dir / "doc2.txt").write_text("Text file")
        (test_dir / "doc3.epub").write_bytes(b"EPUB")
        
        # Mock process_document
        with patch.object(ingester, 'process_document') as mock_process:
            mock_process.return_value = {"status": "success", "cached": False}
            
            # Process only PDFs
            results = ingester.process_directory(
                test_dir,
                file_patterns=["*.pdf"]
            )
            
            assert results["total_files"] == 1
            assert mock_process.call_count == 1
    
    @patch('document_ingester.APIProviderFactory.create_provider')
    def test_get_statistics(self, mock_factory):
        """Test getting processing statistics."""
        mock_factory.return_value = self.mock_provider
        ingester = DocumentIngester(output_dir=str(self.output_dir))
        
        # Add some processed files to log
        ingester.processing_log["processed_files"] = {
            "file1.pdf": {"hash": "abc", "type": "PDF"},
            "file2.pdf": {"hash": "def", "type": "PDF"},
            "file3.epub": {"hash": "ghi", "type": "EPUB"}
        }
        
        ingester.processing_log["statistics"]["total_processed"] = 3
        ingester.processing_log["statistics"]["by_type"] = {
            "PDF": 2,
            "EPUB": 1
        }
        
        # Get statistics
        stats = ingester.get_statistics()
        
        assert stats["total_processed"] == 3
        assert stats["by_type"]["PDF"] == 2
        assert stats["by_type"]["EPUB"] == 1
        assert "last_updated" in stats
        assert "summary_dir" in stats
        assert stats["summary_dir"] == str(ingester.output_dir)


def test_document_ingester_integration():
    """Integration test for the full document processing pipeline."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock provider
        mock_provider = Mock()
        mock_provider.generate_summary.return_value = {
            'summary': 'Integration test summary',
            'key_points': ['Point A', 'Point B'],
            'content_type': 'technical'
        }
        
        with patch('document_ingester.APIProviderFactory.create_provider') as mock_factory:
            mock_factory.return_value = mock_provider
            
            # Initialize ingester
            output_dir = Path(temp_dir) / "output"
            ingester = DocumentIngester(output_dir=str(output_dir))
            
            # Create test document
            test_doc = Path(temp_dir) / "test_doc.txt"
            test_doc.write_text("This is a test document for integration testing.")
            
            # Process document
            result = ingester.process_document(test_doc)
            
            # Verify results
            assert result["status"] == "success"
            assert "summary_path" in result
            
            # Check that summary was saved
            summary_files = list(output_dir.glob("**/*.md"))
            assert len(summary_files) > 0
            
            # Check statistics
            stats = ingester.get_statistics()
            assert stats["total_processed"] == 1
            assert stats["by_type"]["Text"] == 1


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()