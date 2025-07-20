#!/usr/bin/env python3
"""
Unit tests for the markdown scanner module.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from markdown_scanner import MarkdownScanner


@pytest.fixture
def temp_directory():
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test directory structure
    (Path(temp_dir) / "docs").mkdir()
    (Path(temp_dir) / "src").mkdir()
    (Path(temp_dir) / ".git").mkdir()
    (Path(temp_dir) / "node_modules").mkdir()
    
    # Create test files
    (Path(temp_dir) / "README.md").write_text("# Test README")
    (Path(temp_dir) / "docs" / "guide.md").write_text("# Guide")
    (Path(temp_dir) / "docs" / "api.markdown").write_text("# API")
    (Path(temp_dir) / "src" / "code.py").write_text("print('hello')")
    (Path(temp_dir) / ".git" / "config.md").write_text("# Git config")
    (Path(temp_dir) / "temp.tmp").write_text("Temp file")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_scanner_initialization():
    """Test scanner initialization."""
    scanner = MarkdownScanner()
    assert scanner.base_directory == Path(".").resolve()
    assert len(scanner.markdown_files) == 0
    assert ".git" in scanner.excluded_patterns


def test_scanner_with_custom_directory():
    """Test scanner with custom directory."""
    scanner = MarkdownScanner("/tmp")
    assert scanner.base_directory == Path("/tmp").resolve()


def test_add_exclusion_pattern():
    """Test adding exclusion patterns."""
    scanner = MarkdownScanner()
    scanner.add_exclusion_pattern("test_dir")
    assert "test_dir" in scanner.excluded_patterns


def test_should_exclude_path():
    """Test path exclusion logic."""
    scanner = MarkdownScanner()
    
    # Test directory exclusions
    assert scanner.should_exclude_path(Path(".git/config"))
    assert scanner.should_exclude_path(Path("project/.git/config"))
    assert scanner.should_exclude_path(Path("node_modules/package"))
    
    # Test pattern exclusions
    assert scanner.should_exclude_path(Path("file.tmp"))
    assert scanner.should_exclude_path(Path("temp.temp"))
    
    # Test non-excluded paths
    assert not scanner.should_exclude_path(Path("docs/readme.md"))
    assert not scanner.should_exclude_path(Path("src/code.py"))


def test_scan_directory(temp_directory):
    """Test directory scanning."""
    scanner = MarkdownScanner(temp_directory)
    files = scanner.scan_directory()
    
    # Should find 2 markdown files (README.md and docs/guide.md and docs/api.markdown)
    # Should NOT find .git/config.md due to exclusion
    assert len(files) == 3
    
    # Check that correct files were found
    file_names = [f.name for f in files]
    assert "README.md" in file_names
    assert "guide.md" in file_names
    assert "api.markdown" in file_names
    assert "config.md" not in file_names  # Should be excluded


def test_scan_nonexistent_directory():
    """Test scanning non-existent directory."""
    scanner = MarkdownScanner()
    files = scanner.scan_directory(Path("/nonexistent/directory"))
    assert len(files) == 0


def test_scan_file_instead_of_directory():
    """Test scanning a file instead of directory."""
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp_file:
        scanner = MarkdownScanner()
        files = scanner.scan_directory(Path(tmp_file.name))
        assert len(files) == 0


def test_scan_and_update(temp_directory):
    """Test scan and update functionality."""
    scanner = MarkdownScanner(temp_directory)
    assert len(scanner.markdown_files) == 0
    
    scanner.scan_and_update()
    assert len(scanner.markdown_files) == 3


def test_get_markdown_files(temp_directory):
    """Test getting markdown files list."""
    scanner = MarkdownScanner(temp_directory)
    scanner.scan_and_update()
    
    files = scanner.get_markdown_files()
    assert len(files) == 3
    assert all(isinstance(f, Path) for f in files)
    
    # Ensure it returns a copy
    files.clear()
    assert len(scanner.get_markdown_files()) == 3


def test_get_file_count(temp_directory):
    """Test file count method."""
    scanner = MarkdownScanner(temp_directory)
    assert scanner.get_file_count() == 0
    
    scanner.scan_and_update()
    assert scanner.get_file_count() == 3


def test_get_relative_paths(temp_directory):
    """Test getting relative paths."""
    scanner = MarkdownScanner(temp_directory)
    scanner.scan_and_update()
    
    relative_paths = scanner.get_relative_paths()
    assert len(relative_paths) == 3
    assert all(isinstance(p, str) for p in relative_paths)
    
    # Check that paths are relative
    assert "README.md" in relative_paths
    assert any("guide.md" in p for p in relative_paths)
    assert any("api.markdown" in p for p in relative_paths)
    
    # No path should be absolute
    assert not any(p.startswith("/") for p in relative_paths)


def test_custom_exclusions(temp_directory):
    """Test custom exclusion patterns."""
    scanner = MarkdownScanner(temp_directory)
    scanner.add_exclusion_pattern("docs")
    
    files = scanner.scan_directory()
    # Should only find README.md, not files in docs/
    assert len(files) == 1
    assert files[0].name == "README.md"


def test_case_insensitive_extensions(temp_directory):
    """Test case-insensitive file extension matching."""
    # Create files with different case extensions
    (Path(temp_directory) / "UPPERCASE.MD").write_text("# Uppercase")
    (Path(temp_directory) / "mixedCase.Md").write_text("# Mixed")
    
    scanner = MarkdownScanner(temp_directory)
    files = scanner.scan_directory()
    
    # Should find all markdown files regardless of case
    file_names = [f.name for f in files]
    assert "UPPERCASE.MD" in file_names
    assert "mixedCase.Md" in file_names


def main():
    """Run tests with pytest."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()