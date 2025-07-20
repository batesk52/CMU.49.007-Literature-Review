# Product Requirements: AI-Powered Document-to-Markdown Knowledge Base

## 1. Project Vision & Goal

To create an intelligent system that ingests various document formats (PDFs, e-books, and other media files) and transforms them into a well-organized collection of markdown summaries. The system will extract content from these documents, generate thorough markdown summaries that serve as navigation guides to the original content, and maintain a searchable knowledge base. The goal is to enable future AI agents to quickly understand document contents and know exactly where to find specific information in the source materials.

## 2. Core Features & User Stories

### 2.1 Document Ingestion & Processing
- **As a user, I want to** have the system automatically find all supported document files (PDFs, EPUBs, MOBIs, etc.) within a specified directory and its subdirectories.
- **As a user, I want the system to** extract text content from each document and generate a thorough markdown summary that includes:
  - Document metadata (title, author, type, page count)
  - Comprehensive content overview with chapter/section breakdown
  - Key concepts, themes, and important points
  - Page/location references for finding specific information in the original
- **As a user, I want the system to** save these markdown summaries locally in an organized structure within the repository.
- **As a system, I need to** create and maintain a central database (e.g., a JSON file) that maps original documents to their markdown summaries and metadata.
- **As a user, I want to** search through both the generated markdown summaries and original document metadata using keyword and semantic search.

### 2.2 Markdown Summary Organization & Management
- **As a user, I want the system to** organize generated markdown summaries in a logical directory structure that mirrors or categorizes the source documents.
- **As a user, I want each markdown summary to** contain structured sections that make it easy for future agents to navigate:
  - Quick reference header with document location and type
  - Table of contents with page/section mappings
  - Detailed content summaries with location markers
  - Cross-references to related documents
- **As a user, I want the system to** maintain a master index markdown file that lists all processed documents and their summary locations.
- **As a user, I want to** regenerate markdown summaries when source documents are updated or when better extraction methods become available.
- **As a user, I want the system to** track which documents have been processed and when, avoiding duplicate processing.
- **As a user, I want the system to** provide progress feedback during batch document processing operations.

### 2.3 Search & Navigation Operations
- **As a user or AI agent, I want to** search the markdown summaries to quickly understand what documents are available and their contents.
- **As a user or AI agent, I want to** use the detailed location markers in the summaries to know exactly where to look in the original documents for specific information.
- **As a user, I want to** browse the organized markdown summaries to get an overview of the entire document collection.
- **As an AI agent, I want to** read the markdown summaries to understand document relationships and determine which original documents need deeper analysis.
- **As a user, I want the system to** maintain search functionality across both the markdown summaries and the metadata database.

## 3. Technical Requirements

### 3.1 Document Processing & Extraction
- Support for multiple document formats: PDF, EPUB, MOBI, TXT, DOC/DOCX, and other common formats.
- Robust text extraction that preserves document structure (chapters, sections, page numbers).
- Ability to extract and preserve metadata (title, author, publication date, ISBN, etc.).
- Graceful handling of corrupted or password-protected files.
- Memory-efficient processing for large documents (100+ MB files).

### 3.2 Database & File Management
- The metadata database should be in JSON format, mapping source documents to their markdown summaries.
- Generated markdown files should be stored in a organized directory structure within the repository.
- File naming conventions should be consistent and human-readable (e.g., `author_year_title.md`).
- The system must track processing timestamps and source file checksums to detect changes.
- Support for incremental updates without reprocessing unchanged documents.

### 3.3 Markdown Summary Generation Requirements
- Generated markdown summaries should be comprehensive (target: 500-2000 words depending on source length).
- Summaries must include structured sections: metadata, overview, detailed content breakdown, and navigation aids.
- Each summary must contain page/location references to help agents find information in the source.
- The system must validate that generated summaries accurately reflect source content structure.
- Summary generation should be resumable if interrupted during batch operations.
- Markdown files should follow a consistent template for easy parsing by future agents.

### 3.4 Performance & Scalability
- Document text extraction should be efficient, handling PDFs of 500+ pages within reasonable time.
- The system should support parallel processing for multiple documents.
- API calls for summary generation must implement proper rate limiting and retry logic.
- Memory usage should be optimized when processing large document collections.
- Search functionality should remain fast even with thousands of generated markdown summaries.

## 4. Document Processing Specifications

### 4.1 Supported Document Types
The system should support processing of:
- **PDF files**: Academic papers, books, reports
- **E-book formats**: EPUB, MOBI, AZW, FB2
- **Office documents**: DOC/DOCX, ODT, RTF
- **Plain text**: TXT, Markdown (as source documents)
- **Future expansion**: Audio transcripts, video subtitles

### 4.2 Processing Workflow
1. **Discovery Phase**: Scan directories for supported document types
2. **Extraction Phase**: Extract text content and metadata from each document
3. **Analysis Phase**: Analyze document structure (chapters, sections, headings)
4. **Generation Phase**: Create comprehensive markdown summary with AI assistance
5. **Organization Phase**: Save markdown files in structured directory layout
6. **Index Phase**: Update master index and metadata database

### 4.3 Markdown Summary Structure
Each generated markdown file should contain:
```markdown
# [Title]
**Author**: [Author Name]
**Type**: [PDF/EPUB/etc]
**Source**: [Original file path]
**Pages/Length**: [Page count or word count]
**Processed**: [Date]

## Quick Overview
[1-2 paragraph high-level summary]

## Table of Contents
- Chapter 1: [Title] (p. 1-25)
- Chapter 2: [Title] (p. 26-50)
...

## Detailed Summary
### Chapter 1: [Title]
**Pages**: 1-25
**Key Points**:
- [Main point with page reference]
- [Supporting concepts]

[Detailed chapter summary...]

## Key Concepts & Themes
- [Concept 1]: Found in chapters X, Y (pages...)
- [Concept 2]: Primary discussion on pages...

## Navigation Guide
For information about [topic], see:
- Chapter 3, pages 45-52
- Appendix A, page 201
```

### 4.4 User Interface Requirements
- CLI command: `kb_cli.py ingest --directory=/path/to/documents`
- CLI command: `kb_cli.py ingest --file=/path/to/document.pdf`
- CLI command: `kb_cli.py regenerate --document="Title or Path"`
- Progress indicators showing current document being processed
- Summary statistics showing documents processed, markdown files created
- Option to specify output directory for markdown summaries

## 5. Success Criteria

### 5.1 Functional Success
- The system can discover and process all supported document types in a directory structure
- Text extraction works reliably for PDFs, EPUBs, and other formats
- Generated markdown summaries are comprehensive and well-structured
- Markdown summaries contain accurate page/location references to source material
- The system maintains an organized directory of markdown summaries
- Future AI agents can effectively use the summaries to navigate source documents

### 5.2 Performance Success
- Document processing completes within reasonable time (target: <2 minutes for a 300-page PDF)
- The system handles collections of 1000+ documents efficiently
- Text extraction handles large files (100MB+) without memory issues
- Batch processing can run for hours without degradation
- Search across markdown summaries returns results in <2 seconds

### 5.3 Usability Success
- Document ingestion requires minimal configuration
- Generated markdown summaries are human-readable and well-formatted
- Error messages clearly indicate issues (corrupted files, unsupported formats)
- Progress feedback shows which document is being processed
- The markdown summary directory structure is intuitive and browsable

### 5.4 Quality Success
- Markdown summaries accurately represent document content
- Chapter/section breakdowns match the source document structure
- Key concepts and themes are correctly identified
- Page references are accurate and helpful for navigation
- Cross-references between related documents are identified

## 6. Markdown Summary Storage & Organization

### 6.1 Directory Structure
Generated markdown summaries should be organized as follows:
```
document_summaries/
├── index.md                    # Master index of all processed documents
├── by_type/                   # Organized by document type
│   ├── pdfs/
│   ├── ebooks/
│   └── documents/
├── by_category/               # Optional categorization
│   ├── academic/
│   ├── technical/
│   └── reference/
└── metadata/
    └── processing_log.json    # Track what's been processed
```

### 6.2 File Naming Convention
- Academic papers: `author_year_title.md` (e.g., `smith_2023_machine_learning_overview.md`)
- Books: `author_title_year.md` (e.g., `tolkien_lord_of_the_rings_1954.md`)
- Technical documents: `title_version_date.md` (e.g., `python_guide_v3_2023.md`)

### 6.3 Master Index Structure
The `index.md` file should provide:
- Total documents processed
- Categorized lists with links to summaries
- Recently processed documents
- Search tips for finding specific content
- Statistics about the document collection
