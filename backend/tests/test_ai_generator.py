import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend directory to Python path
backend_path = os.path.dirname(os.path.abspath(__file__)).replace("/tests", "")
sys.path.insert(0, backend_path)

from ai_generator import AIGenerator


class TestAIGenerator:
    """Test suite for AIGenerator tool calling functionality"""

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create AIGenerator instance with mocked client"""
        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client
        ):
            generator = AIGenerator("test_key", "claude-sonnet-4-20250514")
            generator.client = mock_anthropic_client
            return generator

    def test_init_parameters(self):
        """Test AIGenerator initialization with correct parameters"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            generator = AIGenerator("test_api_key", "test_model")

            mock_anthropic.assert_called_once_with(api_key="test_api_key")
            assert generator.model == "test_model"
            assert generator.base_params["model"] == "test_model"
            assert generator.base_params["temperature"] == 0
            assert generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(self, ai_generator, mock_anthropic_client):
        """Test generate_response without tools - direct response"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct response without tools")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        result = ai_generator.generate_response("What is machine learning?")

        # Verify API call parameters
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-sonnet-4-20250514"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert call_args["messages"] == [
            {"role": "user", "content": "What is machine learning?"}
        ]
        assert "tools" not in call_args

        assert result == "Direct response without tools"

    def test_generate_response_with_conversation_history(
        self, ai_generator, mock_anthropic_client
    ):
        """Test generate_response includes conversation history in system prompt"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with history")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        history = "Previous conversation context here"
        result = ai_generator.generate_response(
            "Follow up question", conversation_history=history
        )

        # Verify system prompt includes history
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert history in call_args["system"]
        assert "Previous conversation:" in call_args["system"]

    def test_generate_response_with_tools_no_tool_use(
        self, ai_generator, mock_anthropic_client
    ):
        """Test generate_response with tools provided but AI doesn't use them"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct response, no tools needed")]
        mock_response.stop_reason = "end_turn"
        mock_anthropic_client.messages.create.return_value = mock_response

        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()

        result = ai_generator.generate_response(
            "General question", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tools were provided to API
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}

        # Tool manager should not be called
        mock_tool_manager.execute_tool.assert_not_called()

        assert result == "Direct response, no tools needed"

    def test_generate_response_with_tool_use(
        self,
        ai_generator,
        mock_anthropic_client,
        mock_tool_use_response,
        mock_final_response,
    ):
        """Test generate_response when AI uses tools"""
        # First call returns tool use, second call returns final response
        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_final_response,
        ]

        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search results content"

        result = ai_generator.generate_response(
            "Search for machine learning", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test query"
        )

        # Verify two API calls were made
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify final response
        assert result == "Here's what I found about test query..."

    def test_handle_tool_execution_single_tool(
        self,
        ai_generator,
        mock_anthropic_client,
        mock_tool_use_response,
        mock_final_response,
    ):
        """Test _handle_tool_execution with single tool call"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt",
            "model": "test_model",
            "temperature": 0,
            "max_tokens": 800,
        }

        mock_anthropic_client.messages.create.return_value = mock_final_response

        result = ai_generator._handle_tool_execution(
            mock_tool_use_response, base_params, mock_tool_manager
        )

        # Verify tool execution
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test query"
        )

        # Verify final API call structure
        final_call_args = mock_anthropic_client.messages.create.call_args[1]
        assert (
            len(final_call_args["messages"]) == 3
        )  # original + assistant + tool results

        # Check message structure
        messages = final_call_args["messages"]
        assert messages[0] == {"role": "user", "content": "Test query"}
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"
        assert messages[2]["content"][0]["content"] == "Tool execution result"

        assert result == "Here's what I found about test query..."

    def test_handle_tool_execution_multiple_tools(
        self, ai_generator, mock_anthropic_client, mock_final_response
    ):
        """Test _handle_tool_execution with multiple tool calls"""
        # Create response with multiple tool uses
        mock_tool_block_1 = Mock()
        mock_tool_block_1.type = "tool_use"
        mock_tool_block_1.name = "search_course_content"
        mock_tool_block_1.input = {"query": "test query 1"}
        mock_tool_block_1.id = "tool_use_123"

        mock_tool_block_2 = Mock()
        mock_tool_block_2.type = "tool_use"
        mock_tool_block_2.name = "get_course_outline"
        mock_tool_block_2.input = {"course_name": "Test Course"}
        mock_tool_block_2.id = "tool_use_456"

        mock_response = Mock()
        mock_response.stop_reason = "tool_use"  # Add missing stop_reason
        mock_response.content = [mock_tool_block_1, mock_tool_block_2]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt",
            "model": "test_model",
            "temperature": 0,
            "max_tokens": 800,
            "tools": [{"name": "search_course_content"}],  # Add tools to base_params
        }

        mock_anthropic_client.messages.create.return_value = mock_final_response

        result = ai_generator._handle_tool_execution(
            mock_response, base_params, mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="test query 1"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_name="Test Course"
        )

        # Verify tool results structure
        final_call_args = mock_anthropic_client.messages.create.call_args[1]
        tool_results = final_call_args["messages"][2]["content"]
        assert len(tool_results) == 2
        assert tool_results[0]["content"] == "Result 1"
        assert tool_results[1]["content"] == "Result 2"

    def test_handle_tool_execution_no_tool_blocks(
        self, ai_generator, mock_anthropic_client, mock_final_response
    ):
        """Test _handle_tool_execution when response has no tool_use blocks"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"  # No tool use
        mock_text_content = Mock()
        mock_text_content.type = "text"
        mock_text_content.text = "No tools here"
        mock_response.content = [mock_text_content]

        mock_tool_manager = Mock()
        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt",
            "model": "test_model",
            "temperature": 0,
            "max_tokens": 800,
        }

        # Should not make any API calls since there are no tools to execute
        result = ai_generator._handle_tool_execution(
            mock_response, base_params, mock_tool_manager
        )

        # No tools should be executed
        mock_tool_manager.execute_tool.assert_not_called()

        # Should not make any API calls since stop_reason != "tool_use"
        mock_anthropic_client.messages.create.assert_not_called()

        # Should return the response text directly
        assert result == "No tools here"

    def test_generate_response_tool_execution_error_handling(
        self,
        ai_generator,
        mock_anthropic_client,
        mock_tool_use_response,
        mock_final_response,
    ):
        """Test error handling during tool execution"""
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_final_response,
        ]

        # This should not crash, but handle the exception gracefully
        result = ai_generator.generate_response(
            "Search query", tools=tools, tool_manager=mock_tool_manager
        )

        # Should still attempt to make final call even if tool execution fails
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify error message was included in tool results
        call_args = mock_anthropic_client.messages.create.call_args_list[1][1]
        tool_result_content = call_args["messages"][-1]["content"][0]["content"]
        assert "Error executing tool: Tool execution failed" in tool_result_content

    def test_sequential_tool_calling_two_rounds(
        self, ai_generator, mock_anthropic_client
    ):
        """Test sequential tool calling across 2 rounds"""
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Round 1 result",
            "Round 2 result",
        ]

        # First call: tool use response
        mock_tool_response_1 = Mock()
        mock_tool_response_1.stop_reason = "tool_use"
        mock_tool_block_1 = Mock()
        mock_tool_block_1.type = "tool_use"
        mock_tool_block_1.name = "search_course_content"
        mock_tool_block_1.input = {"query": "first search"}
        mock_tool_block_1.id = "tool_1"
        mock_tool_response_1.content = [mock_tool_block_1]

        # Second call: another tool use response
        mock_tool_response_2 = Mock()
        mock_tool_response_2.stop_reason = "tool_use"
        mock_tool_block_2 = Mock()
        mock_tool_block_2.type = "tool_use"
        mock_tool_block_2.name = "search_course_content"
        mock_tool_block_2.input = {"query": "second search"}
        mock_tool_block_2.id = "tool_2"
        mock_tool_response_2.content = [mock_tool_block_2]

        # Third call: final response
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [Mock(text="Final synthesized answer")]

        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_response_1,
            mock_tool_response_2,
            mock_final_response,
        ]

        result = ai_generator.generate_response(
            "Complex query", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify 3 API calls were made (initial + 2 rounds)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="first search"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="second search"
        )

        # Verify final result
        assert result == "Final synthesized answer"

    def test_sequential_tool_calling_early_termination(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that sequential tool calling terminates early when no more tools needed"""
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search result"

        # First call: tool use response
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "search"}
        mock_tool_block.id = "tool_1"
        mock_tool_response.content = [mock_tool_block]

        # Second call: final response (no more tools)
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [Mock(text="Complete answer")]

        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        result = ai_generator.generate_response(
            "Simple query", tools=tools, tool_manager=mock_tool_manager
        )

        # Should only make 2 API calls (not 3)
        assert mock_anthropic_client.messages.create.call_count == 2

        # Should only execute 1 tool
        assert mock_tool_manager.execute_tool.call_count == 1

        assert result == "Complete answer"

    def test_sequential_tool_calling_max_rounds_limit(
        self, ai_generator, mock_anthropic_client
    ):
        """Test that sequential tool calling respects max rounds limit"""
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search result"

        # Create tool use responses for 3 potential rounds (should stop at 2)
        def create_tool_response(tool_id):
            mock_response = Mock()
            mock_response.stop_reason = "tool_use"
            mock_tool_block = Mock()
            mock_tool_block.type = "tool_use"
            mock_tool_block.name = "search_course_content"
            mock_tool_block.input = {"query": f"search {tool_id}"}
            mock_tool_block.id = tool_id
            mock_response.content = [mock_tool_block]
            return mock_response

        # Final response without tools
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [Mock(text="Final answer")]

        mock_anthropic_client.messages.create.side_effect = [
            create_tool_response("tool_1"),
            create_tool_response("tool_2"),
            mock_final_response,  # This should be the final call
        ]

        result = ai_generator.generate_response(
            "Complex multi-step query", tools=tools, tool_manager=mock_tool_manager
        )

        # Should make exactly 3 API calls (initial + 2 tool rounds)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Should execute exactly 2 tools (max rounds limit)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify final call doesn't include tools (reached max rounds)
        final_call_args = mock_anthropic_client.messages.create.call_args_list[2][1]
        assert "tools" not in final_call_args

        assert result == "Final answer"

    def test_handle_tool_execution_with_max_rounds_parameter(
        self, ai_generator, mock_anthropic_client
    ):
        """Test _handle_tool_execution with custom max_rounds parameter"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Tool use response
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_1"
        mock_tool_response.content = [mock_tool_block]

        # Final response
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [Mock(text="Final answer")]

        mock_anthropic_client.messages.create.side_effect = [mock_final_response]

        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt",
            "tools": [{"name": "search_course_content"}],
        }

        # Test with max_rounds=1
        result = ai_generator._handle_tool_execution(
            mock_tool_response, base_params, mock_tool_manager, max_rounds=1
        )

        # Should execute tool once and make final call
        mock_tool_manager.execute_tool.assert_called_once()
        assert mock_anthropic_client.messages.create.call_count == 1
        assert result == "Final answer"

    def test_backwards_compatibility_single_round(
        self,
        ai_generator,
        mock_anthropic_client,
        mock_tool_use_response,
        mock_final_response,
    ):
        """Test that existing single-round behavior is preserved"""
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search result"

        # Set up single tool use followed by final response (original behavior)
        mock_anthropic_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_final_response,
        ]

        result = ai_generator.generate_response(
            "Simple query", tools=tools, tool_manager=mock_tool_manager
        )

        # Should make 2 API calls (same as original)
        assert mock_anthropic_client.messages.create.call_count == 2

        # Should execute 1 tool (same as original)
        mock_tool_manager.execute_tool.assert_called_once()

        # Should return expected result
        assert result == "Here's what I found about test query..."

    def test_system_prompt_content(self, ai_generator):
        """Test that system prompt contains expected content"""
        system_prompt = ai_generator.SYSTEM_PROMPT

        # Check for key instruction elements
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        assert "Sequential tool usage" in system_prompt
        assert "up to 2 rounds maximum" in system_prompt
        assert "Round 1" in system_prompt
        assert "Round 2" in system_prompt
        assert "Build context" in system_prompt
        assert "Brief, Concise and focused" in system_prompt
        assert "Educational" in system_prompt
        assert "Comprehensive" in system_prompt

    def test_base_params_structure(self, ai_generator):
        """Test that base_params are structured correctly"""
        base_params = ai_generator.base_params

        assert base_params["model"] == "claude-sonnet-4-20250514"
        assert base_params["temperature"] == 0
        assert base_params["max_tokens"] == 800
