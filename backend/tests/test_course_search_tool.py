import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add backend directory to Python path
backend_path = os.path.dirname(os.path.abspath(__file__)).replace('/tests', '')
sys.path.insert(0, backend_path)

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    def test_get_tool_definition(self, mock_vector_store):
        """Test that tool definition is returned correctly"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()
        
        assert definition["name"] == "search_course_content"
        assert definition["description"] == "Search course materials with smart course name matching and lesson filtering"
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]

    def test_execute_query_only_success(self, mock_vector_store, sample_search_results):
        """Test execute with query only - successful search"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("machine learning basics")
        
        # Verify search was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="machine learning basics",
            course_name=None,
            lesson_number=None
        )
        
        # Verify result formatting
        assert "[Introduction to Machine Learning - Lesson 1]" in result
        assert "Machine learning is a method of data analysis" in result
        assert "It is a branch of artificial intelligence" in result
        
        # Verify sources were tracked
        assert len(tool.last_sources) == 2
        assert tool.last_sources[0]["text"] == "Introduction to Machine Learning - Lesson 1"
        assert tool.last_sources[0]["link"] == "https://example.com/lesson1"

    def test_execute_with_course_name(self, mock_vector_store, sample_search_results):
        """Test execute with course name filter"""
        mock_vector_store.search.return_value = sample_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("regression", course_name="Machine Learning")
        
        mock_vector_store.search.assert_called_once_with(
            query="regression",
            course_name="Machine Learning",
            lesson_number=None
        )
        
        assert "Introduction to Machine Learning - Lesson 1" in result

    def test_execute_with_lesson_number(self, mock_vector_store, sample_search_results):
        """Test execute with lesson number filter"""
        mock_vector_store.search.return_value = sample_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("regression", lesson_number=2)
        
        mock_vector_store.search.assert_called_once_with(
            query="regression",
            course_name=None,
            lesson_number=2
        )

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Test execute with both course name and lesson number filters"""
        mock_vector_store.search.return_value = sample_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("regression", course_name="ML Course", lesson_number=3)
        
        mock_vector_store.search.assert_called_once_with(
            query="regression",
            course_name="ML Course",
            lesson_number=3
        )

    def test_execute_empty_results(self, mock_vector_store, empty_search_results):
        """Test execute when search returns no results"""
        mock_vector_store.search.return_value = empty_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("nonexistent topic")
        
        assert result == "No relevant content found."
        assert len(tool.last_sources) == 0

    def test_execute_empty_results_with_filters(self, mock_vector_store, empty_search_results):
        """Test execute when search returns no results with filters applied"""
        mock_vector_store.search.return_value = empty_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("topic", course_name="Test Course", lesson_number=5)
        
        expected = "No relevant content found in course 'Test Course' in lesson 5."
        assert result == expected

    def test_execute_search_error(self, mock_vector_store, error_search_results):
        """Test execute when search returns an error"""
        mock_vector_store.search.return_value = error_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query")
        
        assert result == "Search error occurred"

    def test_execute_with_missing_metadata(self, mock_vector_store):
        """Test execute with incomplete metadata"""
        # Create search results with missing metadata
        incomplete_results = SearchResults(
            documents=["Some content"],
            metadata=[{}],  # Empty metadata
            distances=[0.1]
        )
        mock_vector_store.search.return_value = incomplete_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query")
        
        assert "[unknown]" in result
        assert "Some content" in result

    def test_format_results_no_lesson_link(self, mock_vector_store, sample_search_results):
        """Test formatting when lesson link is not available but course link is"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = None
        mock_vector_store.get_course_link.return_value = "https://example.com/course"
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query")
        
        # Should use course link when lesson link unavailable
        assert tool.last_sources[0]["link"] == "https://example.com/course"

    def test_format_results_no_links(self, mock_vector_store, sample_search_results):
        """Test formatting when no links are available"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = None
        mock_vector_store.get_course_link.return_value = None
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query")
        
        # Should have None link when no links available
        assert tool.last_sources[0]["link"] is None

    def test_execute_with_none_parameters(self, mock_vector_store, sample_search_results):
        """Test execute with explicitly None parameters"""
        mock_vector_store.search.return_value = sample_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query", course_name=None, lesson_number=None)
        
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name=None,
            lesson_number=None
        )

    def test_execute_with_empty_string_course_name(self, mock_vector_store, sample_search_results):
        """Test execute with empty string course name"""
        mock_vector_store.search.return_value = sample_search_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query", course_name="", lesson_number=None)
        
        # Empty string should be passed as-is to vector store
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="",
            lesson_number=None
        )

    def test_last_sources_reset_on_new_search(self, mock_vector_store, sample_search_results):
        """Test that last_sources is reset on each new search"""
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        tool = CourseSearchTool(mock_vector_store)
        
        # First search
        tool.execute("first query")
        first_sources = tool.last_sources.copy()
        assert len(first_sources) == 2
        
        # Second search
        single_result = SearchResults(
            documents=["Single result"],
            metadata=[{"course_title": "Another Course", "lesson_number": 5}],
            distances=[0.1]
        )
        mock_vector_store.search.return_value = single_result
        tool.execute("second query")
        
        # Should have only sources from second search
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Another Course - Lesson 5"