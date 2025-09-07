import os
import sys
import tempfile
from typing import AsyncGenerator
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add backend directory to Python path so we can import modules
backend_path = os.path.dirname(os.path.abspath(__file__)).replace("/tests", "")
sys.path.insert(0, backend_path)

from config import Config
from models import Course, CourseChunk, Lesson
from vector_store import SearchResults


@pytest.fixture
def mock_config():
    """Mock configuration for tests"""
    config = Mock(spec=Config)
    config.ANTHROPIC_API_KEY = "test_key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"
    return config


@pytest.fixture
def sample_course():
    """Sample course for testing"""
    return Course(
        title="Introduction to Machine Learning",
        instructor="Dr. Smith",
        course_link="https://example.com/ml-course",
        lessons=[
            Lesson(
                lesson_number=1,
                title="What is ML?",
                lesson_link="https://example.com/ml-course/lesson1",
            ),
            Lesson(
                lesson_number=2,
                title="Types of ML",
                lesson_link="https://example.com/ml-course/lesson2",
            ),
            Lesson(
                lesson_number=3,
                title="Linear Regression",
                lesson_link="https://example.com/ml-course/lesson3",
            ),
        ],
    )


@pytest.fixture
def sample_course_chunks(sample_course):
    """Sample course chunks for testing"""
    return [
        CourseChunk(
            content="Machine learning is a method of data analysis that automates analytical model building.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="It is a branch of artificial intelligence (AI) based on the idea that systems can learn from data.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="There are three main types of machine learning: supervised, unsupervised, and reinforcement learning.",
            course_title=sample_course.title,
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return SearchResults(
        documents=[
            "Machine learning is a method of data analysis that automates analytical model building.",
            "It is a branch of artificial intelligence (AI) based on the idea that systems can learn from data.",
        ],
        metadata=[
            {"course_title": "Introduction to Machine Learning", "lesson_number": 1},
            {"course_title": "Introduction to Machine Learning", "lesson_number": 1},
        ],
        distances=[0.1, 0.2],
    )


@pytest.fixture
def empty_search_results():
    """Empty search results for testing"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Error search results for testing"""
    return SearchResults.empty("Search error occurred")


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    mock_store = Mock()
    mock_store.search.return_value = SearchResults(
        documents=["Test content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1],
    )
    mock_store.get_lesson_link.return_value = "https://example.com/test/lesson1"
    mock_store.get_course_link.return_value = "https://example.com/test"
    return mock_store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Test response")]
    mock_response.stop_reason = "end_turn"
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_tool_use_response():
    """Mock tool use response from Anthropic"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    # Mock tool use content block
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "search_course_content"
    mock_tool_block.input = {"query": "test query"}
    mock_tool_block.id = "tool_use_123"

    mock_response.content = [mock_tool_block]
    return mock_response


@pytest.fixture
def mock_final_response():
    """Mock final response after tool execution"""
    mock_response = Mock()
    mock_response.content = [Mock(text="Here's what I found about test query...")]
    return mock_response


# API Testing Fixtures

@pytest.fixture
def temp_frontend_dir():
    """Create a temporary frontend directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create basic files to avoid static file mounting errors
        frontend_path = os.path.join(temp_dir, "frontend")
        os.makedirs(frontend_path)
        
        # Create a basic index.html
        with open(os.path.join(frontend_path, "index.html"), "w") as f:
            f.write("<html><body>Test Frontend</body></html>")
            
        yield frontend_path


@pytest.fixture
def test_app(temp_frontend_dir):
    """Create a test FastAPI app instance"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict, Any
    
    # Define models inline to avoid importing from app.py (which mounts static files)
    class QueryRequest(BaseModel):
        """Request model for course queries"""
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        """Response model for course queries"""
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str

    class CourseStats(BaseModel):
        """Response model for course statistics"""
        total_courses: int
        course_titles: List[str]
    
    # Create test app without mounting problematic static files in production
    test_app = FastAPI(title="Test RAG System")
    
    # Add CORS middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mock RAG system for testing
    mock_rag_system = Mock()
    
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Test endpoint for document queries"""
        try:
            session_id = request.session_id or "test_session"
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Test endpoint for course statistics"""
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/")
    async def root():
        """Test root endpoint"""
        return {"message": "RAG System API"}
    
    # Store mock for access in tests
    test_app.state.mock_rag_system = mock_rag_system
    
    return test_app


@pytest.fixture
def test_client(test_app):
    """Create a test client for synchronous testing"""
    return TestClient(test_app)


@pytest.fixture
async def async_test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for async testing"""
    from httpx import ASGITransport
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_rag_system(test_app):
    """Access the mock RAG system from the test app"""
    return test_app.state.mock_rag_system


@pytest.fixture
def sample_query_request():
    """Sample query request for testing"""
    return {
        "query": "What is machine learning?",
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_query_response():
    """Sample query response for testing"""
    return {
        "answer": "Machine learning is a subset of artificial intelligence...",
        "sources": [
            {"text": "ML Course - Introduction", "link": "http://example.com/ml/intro"},
            {"text": "ML Course - Fundamentals", "link": "http://example.com/ml/fundamentals"}
        ],
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_course_analytics():
    """Sample course analytics for testing"""
    return {
        "total_courses": 3,
        "course_titles": [
            "Introduction to Machine Learning",
            "Advanced Python Programming", 
            "Data Structures and Algorithms"
        ]
    }
