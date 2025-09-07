import pytest
import json
from unittest.mock import Mock
from fastapi import HTTPException
from httpx import AsyncClient


@pytest.mark.api
class TestQueryEndpoint:
    """Test cases for the /api/query endpoint"""

    def test_query_endpoint_success(self, test_client, mock_rag_system, sample_query_request, sample_query_response):
        """Test successful query endpoint request"""
        # Setup mock response
        mock_rag_system.query.return_value = (
            sample_query_response["answer"],
            sample_query_response["sources"]
        )
        
        response = test_client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["answer"] == sample_query_response["answer"]
        assert data["sources"] == sample_query_response["sources"]
        assert data["session_id"] == sample_query_request["session_id"]
        
        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with(
            sample_query_request["query"],
            sample_query_request["session_id"]
        )

    def test_query_endpoint_without_session_id(self, test_client, mock_rag_system):
        """Test query endpoint without session_id creates new session"""
        # Setup mock
        mock_rag_system.query.return_value = ("Test answer", [])
        
        request_data = {"query": "What is Python?"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["answer"] == "Test answer"
        assert data["session_id"] == "test_session"  # Default session from mock
        
        # Verify RAG system was called with default session
        mock_rag_system.query.assert_called_once_with("What is Python?", "test_session")

    def test_query_endpoint_empty_query(self, test_client, mock_rag_system):
        """Test query endpoint with empty query string"""
        mock_rag_system.query.return_value = ("Please provide a question", [])
        
        request_data = {"query": ""}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with("", "test_session")

    def test_query_endpoint_missing_query_field(self, test_client):
        """Test query endpoint with missing query field"""
        request_data = {"session_id": "test"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_query_endpoint_rag_system_exception(self, test_client, mock_rag_system):
        """Test query endpoint when RAG system raises exception"""
        # Setup mock to raise exception
        mock_rag_system.query.side_effect = Exception("Database connection error")
        
        request_data = {"query": "test query"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Database connection error" in data["detail"]

    def test_query_endpoint_long_query(self, test_client, mock_rag_system):
        """Test query endpoint with very long query string"""
        long_query = "What is " + "machine learning " * 100 + "?"
        mock_rag_system.query.return_value = ("Long answer", [])
        
        request_data = {"query": long_query}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with(long_query, "test_session")

    def test_query_endpoint_special_characters(self, test_client, mock_rag_system):
        """Test query endpoint with special characters and unicode"""
        special_query = "What is machine learning? 🤖 Explain with émojis & symbols!"
        mock_rag_system.query.return_value = ("Answer with special chars", [])
        
        request_data = {"query": special_query}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with(special_query, "test_session")


@pytest.mark.api
class TestCoursesEndpoint:
    """Test cases for the /api/courses endpoint"""

    def test_courses_endpoint_success(self, test_client, mock_rag_system, sample_course_analytics):
        """Test successful courses endpoint request"""
        # Setup mock response
        mock_rag_system.get_course_analytics.return_value = sample_course_analytics
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_courses"] == sample_course_analytics["total_courses"]
        assert data["course_titles"] == sample_course_analytics["course_titles"]
        
        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_endpoint_empty_courses(self, test_client, mock_rag_system):
        """Test courses endpoint with no courses"""
        # Setup mock for empty state
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_rag_system_exception(self, test_client, mock_rag_system):
        """Test courses endpoint when RAG system raises exception"""
        # Setup mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store error")
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 500
        data = response.json()
        assert "Vector store error" in data["detail"]

    def test_courses_endpoint_large_dataset(self, test_client, mock_rag_system):
        """Test courses endpoint with large number of courses"""
        # Create mock data for many courses
        many_courses = {
            "total_courses": 100,
            "course_titles": [f"Course {i}" for i in range(100)]
        }
        mock_rag_system.get_course_analytics.return_value = many_courses
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 100
        assert len(data["course_titles"]) == 100

    def test_courses_endpoint_unicode_titles(self, test_client, mock_rag_system):
        """Test courses endpoint with unicode course titles"""
        unicode_courses = {
            "total_courses": 3,
            "course_titles": [
                "機械学習入門 (ML Introduction)",
                "Introducción a Python 🐍", 
                "数据结构与算法"
            ]
        }
        mock_rag_system.get_course_analytics.return_value = unicode_courses
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 3
        assert all(title in data["course_titles"] for title in unicode_courses["course_titles"])


@pytest.mark.api
class TestRootEndpoint:
    """Test cases for the root / endpoint"""

    def test_root_endpoint_success(self, test_client):
        """Test successful root endpoint request"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "RAG System API"

    def test_root_endpoint_head_request(self, test_client):
        """Test HEAD request to root endpoint"""
        response = test_client.head("/")
        
        # HEAD method returns 405 for this endpoint since only GET is defined
        assert response.status_code == 405

    def test_root_endpoint_options_request(self, test_client):
        """Test OPTIONS request to root endpoint (CORS)"""
        response = test_client.options("/")
        
        # Should be handled by CORS middleware
        assert response.status_code in [200, 405]


@pytest.mark.api
@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test cases using async client for more realistic testing"""

    async def test_async_query_endpoint(self, async_test_client, mock_rag_system):
        """Test query endpoint using async client"""
        mock_rag_system.query.return_value = ("Async response", [])
        
        response = await async_test_client.post(
            "/api/query",
            json={"query": "async test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Async response"

    async def test_async_courses_endpoint(self, async_test_client, mock_rag_system):
        """Test courses endpoint using async client"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["Async Course 1", "Async Course 2"]
        }
        
        response = await async_test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5

    async def test_async_concurrent_requests(self, async_test_client, mock_rag_system):
        """Test handling multiple concurrent requests"""
        import asyncio
        
        # Setup different responses for different queries
        def mock_query_side_effect(query, session_id):
            if "query1" in query:
                return ("Answer 1", [])
            elif "query2" in query:
                return ("Answer 2", [])
            else:
                return ("Default answer", [])
        
        mock_rag_system.query.side_effect = mock_query_side_effect
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Test Course"]
        }
        
        # Send concurrent requests
        tasks = [
            async_test_client.post("/api/query", json={"query": "query1"}),
            async_test_client.post("/api/query", json={"query": "query2"}),
            async_test_client.get("/api/courses")
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Check status codes individually for better debugging
        for i, response in enumerate(responses):
            if response.status_code != 200:
                print(f"Response {i} failed with status {response.status_code}: {response.text}")
        
        # Verify all requests succeeded
        assert all(r.status_code == 200 for r in responses)
        
        # Verify correct responses
        assert responses[0].json()["answer"] == "Answer 1"
        assert responses[1].json()["answer"] == "Answer 2"
        assert responses[2].json()["total_courses"] == 1


@pytest.mark.api
class TestErrorHandling:
    """Test error handling across all endpoints"""

    def test_404_nonexistent_endpoint(self, test_client):
        """Test 404 for non-existent endpoints"""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, test_client):
        """Test method not allowed errors"""
        # Try GET on POST endpoint
        response = test_client.get("/api/query")
        assert response.status_code == 405
        
        # Try POST on GET endpoint
        response = test_client.post("/api/courses")
        assert response.status_code == 405

    def test_malformed_content_type(self, test_client):
        """Test requests with malformed content type"""
        response = test_client.post(
            "/api/query",
            data="not json",
            headers={"content-type": "text/plain"}
        )
        
        assert response.status_code == 422


@pytest.mark.api 
class TestResponseFormats:
    """Test response format validation"""

    def test_query_response_format(self, test_client, mock_rag_system):
        """Test that query responses match expected format"""
        mock_rag_system.query.return_value = (
            "Test answer",
            [{"text": "Source 1", "link": "http://example.com"}]
        )
        
        response = test_client.post("/api/query", json={"query": "test"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        required_fields = {"answer", "sources", "session_id"}
        assert set(data.keys()) == required_fields
        
        # Verify field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_courses_response_format(self, test_client, mock_rag_system):
        """Test that courses responses match expected format"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course A", "Course B"]
        }
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        required_fields = {"total_courses", "course_titles"}
        assert set(data.keys()) == required_fields
        
        # Verify field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])