import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

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
