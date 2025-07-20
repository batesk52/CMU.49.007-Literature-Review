"""
Document Ingester Module

This module handles the ingestion of various document formats (PDF, EPUB, etc.)
and converts them into comprehensive markdown summaries with navigation aids.
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime
import PyPDF2
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re

# Import our API providers for summary generation
from api_providers import APIProviderFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentIngester:
    """
    Handles ingestion of various document formats and converts them to markdown summaries.
    """
    
    SUPPORTED_FORMATS = {
        '.pdf': 'PDF',
        '.epub': 'EPUB',
        '.mobi': 'MOBI',
        '.txt': 'Text',
        '.doc': 'Word',
        '.docx': 'Word'
    }
    
    def __init__(self, output_dir: str = "document_summaries", provider_name: str = None):
        """
        Initialize the document ingester.
        
        Args:
            output_dir: Directory to store generated markdown summaries
            provider_name: API provider to use for summary generation
        """
        self.output_dir = Path(output_dir)
        self.provider = APIProviderFactory.create_provider(provider_name)
        self.provider_name = provider_name or self.provider.__class__.__name__.replace('Provider', '').lower()
        
        # Create output directory structure
        self._setup_directories()
        
        # Load processing log
        self.processing_log_path = self.output_dir / "metadata" / "processing_log.json"
        self.processing_log = self._load_processing_log()
        
        logger.info(f"Initialized document ingester with {self.provider_name} provider")
    
    def _setup_directories(self):
        """Create the output directory structure."""
        # Main directories
        (self.output_dir / "by_type" / "pdfs").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "by_type" / "ebooks").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "by_type" / "documents").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "by_category" / "academic").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "by_category" / "technical").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "by_category" / "reference").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "metadata").mkdir(parents=True, exist_ok=True)
    
    def _load_processing_log(self) -> Dict[str, Any]:
        """Load the processing log from disk."""
        if self.processing_log_path.exists():
            try:
                with open(self.processing_log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load processing log: {e}")
        
        return {
            "processed_files": {},
            "statistics": {
                "total_processed": 0,
                "by_type": {},
                "last_updated": None
            }
        }
    
    def _save_processing_log(self):
        """Save the processing log to disk."""
        self.processing_log["statistics"]["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.processing_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.processing_log, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save processing log: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate hash of a file for change detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _extract_pdf_content(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract text content and metadata from a PDF file.
        
        Returns:
            Dict containing text, metadata, and structure information
        """
        logger.info(f"Extracting content from PDF: {file_path.name}")
        
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Extract metadata
                metadata = {
                    "title": file_path.stem,
                    "author": "Unknown",
                    "pages": len(reader.pages),
                    "type": "PDF"
                }
                
                if reader.metadata:
                    metadata["title"] = reader.metadata.get('/Title', file_path.stem)
                    metadata["author"] = reader.metadata.get('/Author', 'Unknown')
                
                # Extract text from each page
                pages_content = []
                full_text = []
                
                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        pages_content.append({
                            "page": i + 1,
                            "text": text,
                            "length": len(text)
                        })
                        full_text.append(f"\n--- Page {i + 1} ---\n{text}")
                    except Exception as e:
                        logger.warning(f"Could not extract page {i + 1}: {e}")
                        pages_content.append({
                            "page": i + 1,
                            "text": "[Page extraction failed]",
                            "length": 0
                        })
                
                return {
                    "metadata": metadata,
                    "full_text": "\n".join(full_text),
                    "pages": pages_content,
                    "extraction_method": "PyPDF2"
                }
                
        except Exception as e:
            logger.error(f"Failed to extract PDF content: {e}")
            return None
    
    def _extract_epub_content(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract text content and metadata from an EPUB file.
        
        Returns:
            Dict containing text, metadata, and structure information
        """
        logger.info(f"Extracting content from EPUB: {file_path.name}")
        
        try:
            # Try to read EPUB with error handling for corrupted files
            try:
                book = epub.read_epub(str(file_path))
            except Exception as epub_error:
                logger.warning(f"Primary EPUB reader failed: {epub_error}")
                # Try alternative approach - read as zip and extract HTML
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    # Look for HTML/XHTML files
                    html_files = [f for f in zip_file.namelist() if f.endswith(('.html', '.xhtml', '.htm'))]
                    
                    if not html_files:
                        logger.error("No HTML content found in EPUB")
                        return None
                    
                    chapters = []
                    full_text = []
                    
                    for html_file in html_files[:20]:  # Limit to first 20 files
                        try:
                            content = zip_file.read(html_file).decode('utf-8', errors='ignore')
                            soup = BeautifulSoup(content, 'html.parser')
                            text = soup.get_text()
                            
                            if len(text.strip()) < 100:
                                continue
                                
                            title = f"Section: {Path(html_file).stem}"
                            chapters.append({
                                "title": title,
                                "text": text,
                                "length": len(text)
                            })
                            full_text.append(f"\n--- {title} ---\n{text}")
                        except Exception as e:
                            logger.warning(f"Failed to extract {html_file}: {e}")
                            continue
                    
                    if not chapters:
                        logger.error("No readable content extracted from EPUB")
                        return None
                    
                    return {
                        "metadata": {
                            "title": file_path.stem,
                            "author": "Unknown",
                            "type": "EPUB",
                            "chapters": len(chapters)
                        },
                        "full_text": "\n".join(full_text),
                        "chapters": chapters,
                        "extraction_method": "zipfile"
                    }
            
            # Extract metadata with error handling
            metadata = {
                "title": file_path.stem,
                "author": "Unknown",
                "type": "EPUB",
                "chapters": 0
            }
            
            try:
                title_meta = book.get_metadata('DC', 'title')
                if title_meta:
                    metadata["title"] = title_meta[0][0]
            except:
                pass
                
            try:
                author_meta = book.get_metadata('DC', 'creator')
                if author_meta:
                    metadata["author"] = author_meta[0][0]
            except:
                pass
            
            # Extract chapters with better error handling
            chapters = []
            full_text = []
            
            for item in book.get_items():
                try:
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        content = item.get_content()
                        if content:
                            soup = BeautifulSoup(content, 'html.parser')
                            text = soup.get_text()
                            
                            # Skip if text is too short (likely navigation or metadata)
                            if len(text.strip()) < 100:
                                continue
                            
                            # Try to extract chapter title
                            title = "Chapter"
                            for header_tag in ['h1', 'h2', 'h3']:
                                header = soup.find(header_tag)
                                if header:
                                    title = header.get_text().strip()[:100]  # Limit title length
                                    break
                            
                            # If no header found, use item id or filename
                            if title == "Chapter" and hasattr(item, 'id'):
                                title = f"Section: {item.id}"
                            
                            chapters.append({
                                "title": title,
                                "text": text,
                                "length": len(text)
                            })
                            full_text.append(f"\n--- {title} ---\n{text}")
                except Exception as e:
                    logger.warning(f"Failed to extract item content: {e}")
                    continue
            
            metadata["chapters"] = len(chapters)
            
            if not chapters:
                logger.warning("No readable content found in EPUB")
                return None
            
            return {
                "metadata": metadata,
                "full_text": "\n".join(full_text),
                "chapters": chapters,
                "extraction_method": "ebooklib"
            }
            
        except Exception as e:
            logger.error(f"Failed to extract EPUB content: {e}")
            return None
    
    def _extract_text_content(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return {
                "metadata": {
                    "title": file_path.stem,
                    "author": "Unknown",
                    "type": "Text",
                    "length": len(text)
                },
                "full_text": text,
                "extraction_method": "direct"
            }
        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            return None
    
    def extract_document_content(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract content from a document based on its type.
        
        Returns:
            Dict containing extracted content or None if extraction fails
        """
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self._extract_pdf_content(file_path)
        elif suffix == '.epub':
            return self._extract_epub_content(file_path)
        elif suffix in ['.txt', '.md']:
            return self._extract_text_content(file_path)
        else:
            logger.warning(f"Unsupported file format: {suffix}")
            return None
    
    def _generate_markdown_summary(self, content: Dict[str, Any], file_path: Path) -> str:
        """
        Generate a comprehensive markdown summary using AI.
        
        Args:
            content: Extracted document content
            file_path: Original document path
            
        Returns:
            Formatted markdown summary
        """
        metadata = content["metadata"]
        
        # Drastically reduce content size - use only first 400 characters
        content_preview = content['full_text'][:400]
        
        # Ultra-minimal prompt to minimize API load
        prompt = f"One sentence about this {metadata.get('type', 'document')}: {content_preview}"

        try:
            # Generate summary using API provider
            summary_content = self.provider.generate_summary(prompt, f" for {metadata.get('title', 'document')}")
            
            if not summary_content:
                # Try backup provider if available
                backup_summary = self._try_backup_provider(prompt, metadata)
                if backup_summary:
                    summary_content = backup_summary
                else:
                    logger.warning("Failed to generate AI summary, creating basic summary")
                    # Create a basic summary without AI
                    summary_content = f"""## Quick Overview

This {metadata.get('type', 'document')} by {metadata.get('author', 'Unknown Author')} contains {metadata.get('pages', metadata.get('chapters', 'unknown'))} pages/chapters.

## Content Preview

{content_preview[:500]}...

## Basic Information

- **Title**: {metadata.get('title', 'Unknown')}
- **Author**: {metadata.get('author', 'Unknown')}
- **Type**: {metadata.get('type', 'Unknown')}
- **Length**: {metadata.get('pages', metadata.get('chapters', 'Unknown'))} pages/chapters

*Note: This is a basic summary as AI generation was unavailable.*"""
            
            # Format the complete markdown document
            markdown = f"""# {metadata.get('title', 'Untitled Document')}

**Author**: {metadata.get('author', 'Unknown')}
**Type**: {metadata.get('type', 'Unknown')}
**Source**: `{file_path}`
**Pages/Length**: {metadata.get('pages', metadata.get('chapters', 'Unknown'))}
**Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Generated with**: {self.provider_name}

## Document Information

- **Original Location**: `{file_path.absolute()}`
- **File Size**: {file_path.stat().st_size / 1024 / 1024:.1f} MB
- **Hash**: {self._get_file_hash(file_path)}

---

{summary_content}

---

## Metadata

This summary was automatically generated to help AI agents navigate the source document.
For the complete content, refer to the original file at: `{file_path}`
"""
            
            return markdown
            
        except Exception as e:
            logger.error(f"Failed to generate markdown summary: {e}")
            return None
    
    def _try_backup_provider(self, prompt: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Try to use a backup API provider if primary fails."""
        try:
            from api_providers import APIProviderFactory
            
            # If current provider is Gemini, try OpenAI as backup
            if self.provider_name.lower() == 'gemini':
                try:
                    backup_provider = APIProviderFactory.create_provider('openai')
                    logger.info("Trying OpenAI as backup provider...")
                    return backup_provider.generate_summary(prompt, f" for {metadata.get('title', 'document')}")
                except:
                    pass
            
            # If current provider is OpenAI, try Gemini as backup
            elif self.provider_name.lower() == 'openai':
                try:
                    backup_provider = APIProviderFactory.create_provider('gemini')
                    logger.info("Trying Gemini as backup provider...")
                    return backup_provider.generate_summary(prompt, f" for {metadata.get('title', 'document')}")
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"Backup provider attempt failed: {e}")
        
        return None
    
    def _save_markdown_summary(self, markdown: str, metadata: Dict[str, Any], 
                              original_path: Path) -> Optional[Path]:
        """
        Save the markdown summary to the appropriate directory.
        
        Returns:
            Path to saved markdown file or None if save fails
        """
        # Determine output directory based on file type
        file_type = metadata.get('type', 'Unknown').lower()
        if file_type == 'pdf':
            type_dir = self.output_dir / "by_type" / "pdfs"
        elif file_type in ['epub', 'mobi']:
            type_dir = self.output_dir / "by_type" / "ebooks"
        else:
            type_dir = self.output_dir / "by_type" / "documents"
        
        # Generate filename
        author = re.sub(r'[^\w\s-]', '', metadata.get('author', 'unknown')).strip()
        title = re.sub(r'[^\w\s-]', '', metadata.get('title', 'untitled')).strip()
        filename = f"{author}_{title}.md".replace(' ', '_').lower()
        
        # Ensure unique filename
        output_path = type_dir / filename
        counter = 1
        while output_path.exists():
            output_path = type_dir / f"{author}_{title}_{counter}.md".replace(' ', '_').lower()
            counter += 1
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            logger.info(f"Saved markdown summary to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save markdown summary: {e}")
            return None
    
    def process_document(self, file_path: Path, force: bool = False) -> Dict[str, Any]:
        """
        Process a single document and generate its markdown summary.
        
        Args:
            file_path: Path to the document
            force: Force reprocessing even if already processed
            
        Returns:
            Dict with processing results
        """
        file_path = Path(file_path).absolute()
        
        # Check if already processed
        file_hash = self._get_file_hash(file_path)
        file_key = str(file_path)
        
        if not force and file_key in self.processing_log["processed_files"]:
            existing = self.processing_log["processed_files"][file_key]
            if existing["hash"] == file_hash:
                logger.info(f"Skipping already processed file: {file_path.name}")
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "markdown_path": existing["markdown_path"]
                }
        
        logger.info(f"Processing document: {file_path.name}")
        
        # Extract content
        content = self.extract_document_content(file_path)
        if not content:
            return {
                "status": "failed",
                "reason": "extraction_failed",
                "file": str(file_path)
            }
        
        # Generate markdown summary
        markdown = self._generate_markdown_summary(content, file_path)
        if not markdown:
            return {
                "status": "failed",
                "reason": "summary_generation_failed",
                "file": str(file_path)
            }
        
        # Save markdown
        markdown_path = self._save_markdown_summary(markdown, content["metadata"], file_path)
        if not markdown_path:
            return {
                "status": "failed",
                "reason": "save_failed",
                "file": str(file_path)
            }
        
        # Update processing log
        self.processing_log["processed_files"][file_key] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "markdown_path": str(markdown_path),
            "metadata": content["metadata"],
            "provider": self.provider_name
        }
        
        # Update statistics
        file_type = content["metadata"].get("type", "Unknown")
        self.processing_log["statistics"]["total_processed"] += 1
        if file_type not in self.processing_log["statistics"]["by_type"]:
            self.processing_log["statistics"]["by_type"][file_type] = 0
        self.processing_log["statistics"]["by_type"][file_type] += 1
        
        self._save_processing_log()
        
        return {
            "status": "success",
            "file": str(file_path),
            "markdown_path": str(markdown_path),
            "metadata": content["metadata"]
        }
    
    def process_directory(self, directory: Path, recursive: bool = True, 
                         force: bool = False) -> Dict[str, Any]:
        """
        Process all supported documents in a directory.
        
        Args:
            directory: Directory to process
            recursive: Process subdirectories
            force: Force reprocessing of all files
            
        Returns:
            Dict with processing statistics
        """
        directory = Path(directory).absolute()
        logger.info(f"Processing directory: {directory}")
        
        # Find all supported files
        pattern = "**/*" if recursive else "*"
        supported_files = []
        
        for suffix in self.SUPPORTED_FORMATS:
            supported_files.extend(directory.glob(f"{pattern}{suffix}"))
            supported_files.extend(directory.glob(f"{pattern}{suffix.upper()}"))
        
        logger.info(f"Found {len(supported_files)} supported documents")
        
        # Initial delay to avoid immediate rate limiting
        if supported_files:
            logger.info("Waiting 15 seconds before starting to avoid rate limits...")
            time.sleep(15.0)
        
        # Process each file
        results = {
            "total_found": len(supported_files),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "results": []
        }
        
        for i, file_path in enumerate(supported_files, 1):
            logger.info(f"Processing {i}/{len(supported_files)}: {file_path.name}")
            
            result = self.process_document(file_path, force)
            results["results"].append(result)
            
            if result["status"] == "success":
                results["processed"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1
            
            # Add longer delay between documents to avoid rate limiting
            if i < len(supported_files):
                time.sleep(10.0)  # 10 second delay between documents
        
        # Update master index
        self._update_master_index()
        
        return results
    
    def _update_master_index(self):
        """Update the master index.md file with all processed documents."""
        logger.info("Updating master index")
        
        index_content = f"""# Document Summary Index

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Documents**: {self.processing_log['statistics']['total_processed']}

## Statistics

"""
        
        # Add statistics by type
        for doc_type, count in self.processing_log['statistics']['by_type'].items():
            index_content += f"- **{doc_type}**: {count} documents\n"
        
        index_content += "\n## All Documents\n\n"
        
        # Group by type
        by_type = {}
        for file_path, info in self.processing_log["processed_files"].items():
            doc_type = info["metadata"].get("type", "Unknown")
            if doc_type not in by_type:
                by_type[doc_type] = []
            by_type[doc_type].append((file_path, info))
        
        # Add sections for each type
        for doc_type, docs in sorted(by_type.items()):
            index_content += f"\n### {doc_type} Documents\n\n"
            
            for file_path, info in sorted(docs, key=lambda x: x[1]["metadata"].get("title", "")):
                metadata = info["metadata"]
                markdown_path = Path(info["markdown_path"])
                relative_path = markdown_path.relative_to(self.output_dir)
                
                index_content += f"- **[{metadata.get('title', 'Untitled')}]({relative_path})**"
                index_content += f" by {metadata.get('author', 'Unknown')}"
                index_content += f" ({metadata.get('pages', metadata.get('chapters', 'Unknown'))} pages/chapters)\n"
        
        index_content += f"\n---\n\n*Generated by Document Ingester using {self.provider_name}*\n"
        
        # Save index
        index_path = self.output_dir / "index.md"
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            logger.info("Master index updated successfully")
        except Exception as e:
            logger.error(f"Failed to update master index: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.processing_log["statistics"]


def main():
    """Command-line interface for document ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest documents and create markdown summaries")
    parser.add_argument("path", help="File or directory to process")
    parser.add_argument("--output-dir", default="document_summaries",
                       help="Output directory for markdown summaries")
    parser.add_argument("--provider", choices=['openai', 'gemini', 'claude'],
                       help="API provider to use")
    parser.add_argument("--force", action="store_true",
                       help="Force reprocessing of already processed files")
    parser.add_argument("--no-recursive", action="store_true",
                       help="Don't process subdirectories")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize ingester
    try:
        ingester = DocumentIngester(args.output_dir, args.provider)
    except Exception as e:
        print(f"Error initializing ingester: {e}")
        return 1
    
    # Process path
    path = Path(args.path)
    
    if path.is_file():
        # Process single file
        result = ingester.process_document(path, args.force)
        print(f"\nProcessing result: {result['status']}")
        if result['status'] == 'success':
            print(f"Markdown saved to: {result['markdown_path']}")
    else:
        # Process directory
        results = ingester.process_directory(path, not args.no_recursive, args.force)
        print(f"\nProcessing complete:")
        print(f"  Total found: {results['total_found']}")
        print(f"  Processed: {results['processed']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Failed: {results['failed']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())