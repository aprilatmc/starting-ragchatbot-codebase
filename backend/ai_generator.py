from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to search tools for course information.

Tool Usage Guidelines:
- **Content search**: Use 'search_course_content' for questions about specific course content or detailed educational materials
- **Course outlines**: Use 'get_course_outline' for questions about course structure, lessons, or overviews
- **Sequential tool usage**: You can use tools across multiple rounds (up to 2 rounds maximum) to build comprehensive answers
- **Multi-step queries**: For complex questions requiring multiple searches, use tools strategically across rounds
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Sequential Tool Strategy:
- **Round 1**: Use initial tools to gather foundational information (e.g., course outlines, broad searches)
- **Round 2**: Use follow-up tools to refine, expand, or compare information from Round 1 results
- **Build context**: Each round should build upon previous tool results for comprehensive answers
- **Avoid repetition**: Don't repeat identical tool calls; use different parameters or approaches
- **Complex queries**: Break down multi-part questions across rounds (outline → specific content, compare courses, etc.)

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **Comparison questions**: Use multiple rounds to gather information about each subject
- **Course outline requests**: Use outline tool and present complete information including:
  - Course title
  - Course link (if available)  
  - Number of lessons
  - Lesson titles with numbers
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or describe your search process
 - Focus on the final synthesized answer from all rounds

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
5. **Comprehensive** - Use multiple tool rounds when beneficial for complete answers
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(
        self,
        initial_response,
        base_params: Dict[str, Any],
        tool_manager,
        max_rounds: int = 2,
    ):
        """
        Handle execution of tool calls with support for sequential rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool execution rounds (default 2)

        Returns:
            Final response text after all tool execution rounds
        """
        # Initialize state for iterative tool calling
        messages = base_params["messages"].copy()
        current_response = initial_response
        round_count = 0

        # Iterative tool execution loop
        while round_count < max_rounds and current_response.stop_reason == "tool_use":
            round_count += 1

            # Add AI's tool use response to conversation
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls in this round
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name, **content_block.input
                        )
                    except Exception as e:
                        # Handle tool execution errors gracefully
                        tool_result = f"Error executing tool: {str(e)}"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add tool results to conversation
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Prepare parameters for next round (keep tools available)
            round_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }

            # Only add tools if we haven't reached max rounds
            if round_count < max_rounds:
                round_params["tools"] = base_params.get("tools", [])
                round_params["tool_choice"] = {"type": "auto"}

            # Get response for this round
            current_response = self.client.messages.create(**round_params)

            # If no more tool use, break early
            if current_response.stop_reason != "tool_use":
                break

        # Return final response text
        return current_response.content[0].text
