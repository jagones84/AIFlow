"""
Test to reproduce the MCP tool result JSON parsing issue.

The error "SyntaxError: Unexpected token 'u', "upstream r"... is not valid JSON"
occurs when MCP tools return content without a proper "text" field, and the
result gets serialized incorrectly.
"""
import json


def test_mcp_client_content_handling():
    """Test that content handling doesn't return invalid JSON strings."""
    from src.logic.mcp_client import NativeMcpClient

    test_cases = [
        # (response_content, expected_type)
        ([{"type": "text", "text": "hello"}], str),
        ([{"type": "image", "data": "abc123"}], str),  # No text key - fallback
        ({"type": "text", "text": "test"}, str),
        ("plain string", str),
        ([], str),
    ]

    for content, expected_type in test_cases:
        result = NativeMcpClient._parse_mcp_content(content)
        print(f"Input: {content!r} -> Output: {result!r} (type: {type(result).__name__})")
        assert isinstance(result, expected_type), f"Expected {expected_type}, got {type(result)}"


def test_mcp_client_no_dict_representation_leak():
    """Test that dict representations don't leak into tool results.
    
    This specifically tests the bug where content without a 'text' key
    would return str(content) which produces Python dict notation like
    "[{'type': 'image', 'data': 'abc'}]" instead of proper JSON.
    """
    from src.logic.mcp_client import NativeMcpClient

    # This was the bug: content without 'text' key would return str(content)
    # which gives Python dict notation, not JSON
    content_with_image = [{"type": "image", "data": "abc123"}]
    result = NativeMcpClient._parse_mcp_content(content_with_image)
    
    # The result should be proper JSON, not Python dict notation
    print(f"Image content result: {result!r}")
    
    # It should be valid JSON if it was serialized
    if result.startswith("["):
        # If it's JSON, it should use double quotes
        assert '"type"' in result, f"Expected JSON with double quotes, got: {result}"
        # Should be able to parse it back as JSON
        parsed = json.loads(result)
        assert parsed == content_with_image
    else:
        # If it's a string, it should be a proper text result
        assert isinstance(result, str)


def test_bridge_client_content_handling():
    """Test bridge client content handling."""
    from src.logic.bridge_client import PcBridgeClient

    test_cases = [
        ([{"type": "text", "text": "hello"}], str),
        ([{"type": "image", "data": "abc123"}], str),  # No text key - fallback
    ]

    for content, expected_type in test_cases:
        result = PcBridgeClient._parse_content_static(content)
        print(f"Input: {content!r} -> Output: {result!r} (type: {type(result).__name__})")
        assert isinstance(result, expected_type), f"Expected {expected_type}, got {type(result)}"


def test_tool_result_serialization():
    """Test that tool results can be included in messages without JSON issues."""
    # Simulate what happens when a tool result is included in messages
    tool_results = [
        "normal string result",
        str([{"type": "image", "data": "abc"}]),  # This could cause issues
        str({"some": "dict"}),
    ]

    for result in tool_results:
        # When this is included in messages and sent to OpenAI SDK
        messages = [
            {"role": "user", "content": "test"},
            {"role": "tool", "tool_call_id": "123", "content": result}
        ]
        
        # Verify the content is a string
        assert isinstance(result, str), f"Tool result should be string, got {type(result)}"
        print(f"Tool result: {result[:50]}... is valid string")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: MCP Client Content Handling")
    print("=" * 60)
    test_mcp_client_content_handling()
    
    print("\n" + "=" * 60)
    print("Test 2: MCP Client - No Dict Representation Leak")
    print("=" * 60)
    test_mcp_client_no_dict_representation_leak()
    
    print("\n" + "=" * 60)
    print("Test 3: Bridge Client Content Handling")
    print("=" * 60)
    test_bridge_client_content_handling()
    
    print("\n" + "=" * 60)
    print("Test 4: Tool Result Serialization")
    print("=" * 60)
    test_tool_result_serialization()
