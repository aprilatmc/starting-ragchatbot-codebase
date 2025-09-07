# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>
```

### Code Quality Tools

#### Formatting and Linting
```bash
# Format code with black and organize imports with isort
./scripts/format.sh

# Run all quality checks (flake8, mypy, formatting)
./scripts/lint.sh

# Run tests with quality checks
./scripts/test.sh
```

#### Individual Tools
```bash
# Format code
uv run black backend/ main.py

# Organize imports
uv run isort backend/ main.py

# Check code style
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503

# Type checking
uv run mypy backend/ main.py
```

The application runs on:
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a full-stack RAG (Retrieval-Augmented Generation) system with the following structure:

### Backend Architecture (`backend/`)
- **FastAPI Application** (`app.py`): Main web server with CORS middleware, static file serving, and API endpoints
- **RAG System** (`rag_system.py`): Core orchestrator that coordinates all components
- **Document Processing** (`document_processor.py`): Handles PDF/DOCX/TXT parsing and chunking
- **Vector Store** (`vector_store.py`): ChromaDB interface for semantic search
- **AI Generator** (`ai_generator.py`): Anthropic Claude integration with tool support
- **Session Management** (`session_manager.py`): Conversation history tracking
- **Search Tools** (`search_tools.py`): Tool-based search system for AI function calling
- **Models** (`models.py`): Pydantic data models for courses, lessons, and chunks
- **Configuration** (`config.py`): Environment-based settings management

### Frontend (`frontend/`)
Simple HTML/CSS/JavaScript interface for interacting with the RAG system.

### Key Design Patterns
- **Tool-based Search**: The AI uses function calling to search course materials rather than direct retrieval
- **Session-based Conversations**: User queries maintain context across interactions
- **Incremental Document Loading**: New documents are only added if not already processed
- **Component Separation**: Clear separation between document processing, storage, and generation

### Data Models
- **Course**: Represents a course with title, description, and lessons
- **Lesson**: Individual sections within a course
- **CourseChunk**: Text segments for vector search with metadata

### Environment Setup
Requires `.env` file with:
```
ANTHROPIC_API_KEY=your_key_here
```

### Document Storage
- Documents go in `docs/` directory (auto-loaded on startup)
- Supports PDF, DOCX, and TXT files
- Vector embeddings stored in `./chroma_db/`
- don't run the server using ./run.sh, I'll do it myself