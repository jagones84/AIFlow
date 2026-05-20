# Principal Stress Test Report

## Summary
Total Tests: 16
Passed: 8
Failed: 8

## Details
### ✅ PASS: Node Block - SET
**Details:** Successfully set fields.

### ❌ FAIL: Node Block - CODE
**Details:** assert False
 +  where False = ExecutionResult(output="Error: 'builtin_function_or_method' object is not iterable", success=False, outputItems=[], sh...e, iteratorBatches=None, loopBatches=None, doneItems=None, updatedNode=None, subWorkflowId=None, subWorkflowInput=None).success

### ✅ PASS: Node Block - ROUTER
**Details:** Router processed inputs.

### ✅ PASS: Node Block - HTTP_REQUEST
**Details:** HTTP GET request succeeded.

### ❌ FAIL: MCP Server - filesystem
**Details:** Failed to retrieve tools or server is not running properly.

### ❌ FAIL: MCP Server - simple-datetime-server
**Details:** Failed to retrieve tools or server is not running properly.

### ✅ PASS: MCP Server - Brave Search
**Details:** Server running with 2 tools: ['brave_web_search', 'brave_local_search']

### ✅ PASS: MCP Server - Docker
**Details:** Server running with 4 tools: ['create-container', 'deploy-compose', 'get-logs', 'list-containers']

### ✅ PASS: MCP Server - Fetch
**Details:** Server running with 1 tools: ['fetch']

### ❌ FAIL: MCP Server - mcp-reasoner
**Details:** Failed to retrieve tools or server is not running properly.

### ✅ PASS: MCP Server - Memory
**Details:** Server running with 9 tools: ['create_entities', 'create_relations', 'add_observations', 'delete_entities', 'delete_observations', 'delete_relations', 'read_graph', 'search_nodes', 'open_nodes']

### ❌ FAIL: MCP Server - Multi-Fetch
**Details:** Failed to retrieve tools or server is not running properly.

### ✅ PASS: MCP Server - python-local
**Details:** Server running with 1 tools: ['run_python']

### ❌ FAIL: MCP Server - ucpf
**Details:** Failed to retrieve tools or server is not running properly.

### ❌ FAIL: MCP Server - yt-whisper
**Details:** Failed to retrieve tools or server is not running properly.

### ❌ FAIL: MCP Server - GitKraken
**Details:** Failed to retrieve tools or server is not running properly.
