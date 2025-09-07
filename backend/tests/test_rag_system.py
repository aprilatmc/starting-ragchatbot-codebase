import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend directory to Python path
backend_path = os.path.dirname(os.path.abspath(__file__)).replace("/tests", "")
sys.path.insert(0, backend_path)

from models import Course, Lesson
from rag_system import RAGSystem


class TestRAGSystem:
    """Integration tests for RAGSystem query handling"""

    @pytest.fixture
    def mock_dependencies(self, mock_config):
        """Mock all RAGSystem dependencies"""
        mocks = {}

        # Mock all the components
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session_mgr,
            patch("rag_system.ToolManager") as mock_tool_mgr,
            patch("rag_system.CourseSearchTool") as mock_search_tool,
            patch("rag_system.CourseOutlineTool") as mock_outline_tool,
        ):

            mocks["document_processor"] = mock_doc_proc.return_value
            mocks["vector_store"] = mock_vector_store.return_value
            mocks["ai_generator"] = mock_ai_gen.return_value
            mocks["session_manager"] = mock_session_mgr.return_value
            mocks["tool_manager"] = mock_tool_mgr.return_value
            mocks["search_tool"] = mock_search_tool.return_value
            mocks["outline_tool"] = mock_outline_tool.return_value

            yield mocks

    @pytest.fixture
    def rag_system(self, mock_config, mock_dependencies):
        """Create RAGSystem instance with mocked dependencies"""
        return RAGSystem(mock_config)

    def test_rag_system_initialization(self, mock_config, mock_dependencies):
        """Test RAGSystem initializes all components correctly"""
        rag = RAGSystem(mock_config)

        # Verify all components were initialized
        assert hasattr(rag, "document_processor")
        assert hasattr(rag, "vector_store")
        assert hasattr(rag, "ai_generator")
        assert hasattr(rag, "session_manager")
        assert hasattr(rag, "tool_manager")
        assert hasattr(rag, "search_tool")
        assert hasattr(rag, "outline_tool")

        # Verify tools were registered
        mock_dependencies["tool_manager"].register_tool.assert_any_call(
            mock_dependencies["search_tool"]
        )
        mock_dependencies["tool_manager"].register_tool.assert_any_call(
            mock_dependencies["outline_tool"]
        )

    def test_query_without_session_id(self, rag_system, mock_dependencies):
        """Test query method without session ID"""
        # Setup mocks
        mock_dependencies["ai_generator"].generate_response.return_value = (
            "Test AI response"
        )
        mock_dependencies["tool_manager"].get_tool_definitions.return_value = [
            {"name": "test_tool"}
        ]
        mock_dependencies["tool_manager"].get_last_sources.return_value = [
            {"text": "Source 1", "link": "http://example.com"}
        ]

        result, sources = rag_system.query("What is machine learning?")

        # Verify AI generator was called correctly
        mock_dependencies["ai_generator"].generate_response.assert_called_once_with(
            query="Answer this question about course materials: What is machine learning?",
            conversation_history=None,
            tools=[{"name": "test_tool"}],
            tool_manager=mock_dependencies["tool_manager"],
        )

        # Verify sources were retrieved and reset
        mock_dependencies["tool_manager"].get_last_sources.assert_called_once()
        mock_dependencies["tool_manager"].reset_sources.assert_called_once()

        # Verify session manager was not called
        mock_dependencies[
            "session_manager"
        ].get_conversation_history.assert_not_called()
        mock_dependencies["session_manager"].add_exchange.assert_not_called()

        assert result == "Test AI response"
        assert sources == [{"text": "Source 1", "link": "http://example.com"}]

    def test_query_with_session_id(self, rag_system, mock_dependencies):
        """Test query method with session ID for conversation context"""
        # Setup mocks
        mock_dependencies["session_manager"].get_conversation_history.return_value = (
            "Previous conversation context"
        )
        mock_dependencies["ai_generator"].generate_response.return_value = (
            "Contextual AI response"
        )
        mock_dependencies["tool_manager"].get_tool_definitions.return_value = []
        mock_dependencies["tool_manager"].get_last_sources.return_value = []

        result, sources = rag_system.query(
            "Follow up question", session_id="session123"
        )

        # Verify conversation history was retrieved
        mock_dependencies[
            "session_manager"
        ].get_conversation_history.assert_called_once_with("session123")

        # Verify AI generator received the history
        mock_dependencies["ai_generator"].generate_response.assert_called_once_with(
            query="Answer this question about course materials: Follow up question",
            conversation_history="Previous conversation context",
            tools=[],
            tool_manager=mock_dependencies["tool_manager"],
        )

        # Verify conversation was updated
        mock_dependencies["session_manager"].add_exchange.assert_called_once_with(
            "session123", "Follow up question", "Contextual AI response"
        )

        assert result == "Contextual AI response"

    def test_query_tool_usage_flow(self, rag_system, mock_dependencies):
        """Test full query flow when AI uses tools"""
        # Setup tool definitions
        tool_definitions = [
            {"name": "search_course_content", "description": "Search courses"},
            {"name": "get_course_outline", "description": "Get outline"},
        ]

        mock_dependencies["tool_manager"].get_tool_definitions.return_value = (
            tool_definitions
        )
        mock_dependencies["ai_generator"].generate_response.return_value = (
            "Response based on search results"
        )
        mock_dependencies["tool_manager"].get_last_sources.return_value = [
            {"text": "ML Course - Lesson 1", "link": "http://example.com/ml/lesson1"},
            {"text": "ML Course - Lesson 2", "link": "http://example.com/ml/lesson2"},
        ]

        result, sources = rag_system.query("Explain supervised learning")

        # Verify tools were provided to AI
        mock_dependencies["ai_generator"].generate_response.assert_called_once_with(
            query="Answer this question about course materials: Explain supervised learning",
            conversation_history=None,
            tools=tool_definitions,
            tool_manager=mock_dependencies["tool_manager"],
        )

        assert result == "Response based on search results"
        assert len(sources) == 2
        assert sources[0]["text"] == "ML Course - Lesson 1"

    def test_add_course_document_success(
        self, rag_system, mock_dependencies, sample_course, sample_course_chunks
    ):
        """Test adding a single course document successfully"""
        # Setup mocks
        mock_dependencies["document_processor"].process_course_document.return_value = (
            sample_course,
            sample_course_chunks,
        )

        course, chunk_count = rag_system.add_course_document("/path/to/course.pdf")

        # Verify document processing
        mock_dependencies[
            "document_processor"
        ].process_course_document.assert_called_once_with("/path/to/course.pdf")

        # Verify vector store operations
        mock_dependencies["vector_store"].add_course_metadata.assert_called_once_with(
            sample_course
        )
        mock_dependencies["vector_store"].add_course_content.assert_called_once_with(
            sample_course_chunks
        )

        assert course == sample_course
        assert chunk_count == len(sample_course_chunks)

    def test_add_course_document_error(self, rag_system, mock_dependencies):
        """Test error handling when adding course document fails"""
        # Setup mock to raise exception
        mock_dependencies["document_processor"].process_course_document.side_effect = (
            Exception("Processing failed")
        )

        course, chunk_count = rag_system.add_course_document("/path/to/invalid.pdf")

        # Should return None and 0 on error
        assert course is None
        assert chunk_count == 0

        # Vector store should not be called
        mock_dependencies["vector_store"].add_course_metadata.assert_not_called()
        mock_dependencies["vector_store"].add_course_content.assert_not_called()

    def test_add_course_folder_with_clear_existing(
        self, rag_system, mock_dependencies, sample_course, sample_course_chunks
    ):
        """Test adding course folder with clear_existing=True"""
        with (
            patch("rag_system.os.path.exists", return_value=True),
            patch(
                "rag_system.os.listdir",
                return_value=["course1.pdf", "course2.txt", "ignored.doc"],
            ),
        ):

            # Setup mocks
            mock_dependencies[
                "vector_store"
            ].get_existing_course_titles.return_value = []
            mock_dependencies[
                "document_processor"
            ].process_course_document.return_value = (
                sample_course,
                sample_course_chunks,
            )

            courses_added, chunks_added = rag_system.add_course_folder(
                "/docs", clear_existing=True
            )

            # Verify clear was called
            mock_dependencies["vector_store"].clear_all_data.assert_called_once()

            # Verify processing of valid files (2 files: .pdf and .txt)
            assert (
                mock_dependencies[
                    "document_processor"
                ].process_course_document.call_count
                == 2
            )
            assert courses_added == 2
            assert chunks_added == len(sample_course_chunks) * 2

    def test_add_course_folder_skip_existing(
        self, rag_system, mock_dependencies, sample_course, sample_course_chunks
    ):
        """Test adding course folder skips existing courses"""
        with (
            patch("rag_system.os.path.exists", return_value=True),
            patch("rag_system.os.listdir", return_value=["course1.pdf"]),
        ):

            # Setup mocks - course already exists
            mock_dependencies[
                "vector_store"
            ].get_existing_course_titles.return_value = [sample_course.title]
            mock_dependencies[
                "document_processor"
            ].process_course_document.return_value = (
                sample_course,
                sample_course_chunks,
            )

            courses_added, chunks_added = rag_system.add_course_folder("/docs")

            # Should process but not add existing course
            mock_dependencies[
                "document_processor"
            ].process_course_document.assert_called_once()
            mock_dependencies["vector_store"].add_course_metadata.assert_not_called()
            mock_dependencies["vector_store"].add_course_content.assert_not_called()

            assert courses_added == 0
            assert chunks_added == 0

    def test_add_course_folder_nonexistent_directory(
        self, rag_system, mock_dependencies
    ):
        """Test adding course folder when directory doesn't exist"""
        with patch("rag_system.os.path.exists", return_value=False):

            courses_added, chunks_added = rag_system.add_course_folder("/nonexistent")

            assert courses_added == 0
            assert chunks_added == 0

            # No processing should occur
            mock_dependencies[
                "document_processor"
            ].process_course_document.assert_not_called()

    def test_get_course_analytics(self, rag_system, mock_dependencies):
        """Test course analytics retrieval"""
        mock_dependencies["vector_store"].get_course_count.return_value = 5
        mock_dependencies["vector_store"].get_existing_course_titles.return_value = [
            "Course A",
            "Course B",
            "Course C",
        ]

        analytics = rag_system.get_course_analytics()

        assert analytics["total_courses"] == 5
        assert analytics["course_titles"] == ["Course A", "Course B", "Course C"]

    def test_query_prompt_formatting(self, rag_system, mock_dependencies):
        """Test that query is properly formatted for AI"""
        mock_dependencies["ai_generator"].generate_response.return_value = (
            "Test response"
        )
        mock_dependencies["tool_manager"].get_tool_definitions.return_value = []
        mock_dependencies["tool_manager"].get_last_sources.return_value = []

        rag_system.query("What is the capital of France?")

        # Verify the query was wrapped with the instruction
        call_args = mock_dependencies["ai_generator"].generate_response.call_args[1]
        expected_query = "Answer this question about course materials: What is the capital of France?"
        assert call_args["query"] == expected_query

    def test_sources_lifecycle(self, rag_system, mock_dependencies):
        """Test that sources are properly retrieved and reset"""
        test_sources = [{"text": "Source 1", "link": "link1"}]
        mock_dependencies["tool_manager"].get_last_sources.return_value = test_sources
        mock_dependencies["ai_generator"].generate_response.return_value = "Response"
        mock_dependencies["tool_manager"].get_tool_definitions.return_value = []

        result, sources = rag_system.query("Test query")

        # Verify sources were retrieved before reset
        mock_dependencies["tool_manager"].get_last_sources.assert_called_once()
        mock_dependencies["tool_manager"].reset_sources.assert_called_once()

        # Verify reset was called after get_last_sources
        calls = [call[0] for call in mock_dependencies["tool_manager"].method_calls]
        get_sources_index = calls.index("get_last_sources")
        reset_sources_index = calls.index("reset_sources")
        assert reset_sources_index > get_sources_index

        assert sources == test_sources
