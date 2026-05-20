# Comprehensive Node & MCP Stress Test Report

## Summary
Total Tests: 27
Passed: 20
Failed: 7

## Details
### ✅ PASS: Node - SET
**Details:** Successfully set string and number fields.

### ✅ PASS: Node - CODE
**Details:** Successfully executed python code.

### ✅ PASS: Node - ROUTER
**Details:** Router processed inputs successfully.

### ✅ PASS: Node - SWITCH
**Details:** Switch processed multiple routes.

### ✅ PASS: Node - HTTP_REQUEST
**Details:** HTTP GET request succeeded.

### ✅ PASS: Node - JSON_PARSER
**Details:** Successfully parsed JSON text.

### ✅ PASS: Node - JSON_FIELD_EXTRACT
**Details:** Extracted nested JSON field.

### ✅ PASS: Node - WAIT
**Details:** Successfully waited specified time.

### ✅ PASS: Node - VARIABLE_STORE
**Details:** Write and Read operations successful.

### ✅ PASS: Node - STOP_AND_ERROR
**Details:** Successfully stopped flow and raised error.

### ✅ PASS: Node - FILTER
**Details:** Successfully filtered items.

### ✅ PASS: Node - LIMIT
**Details:** Successfully limited items.

### ✅ PASS: Node - FILE_SAVE
**Details:** Successfully saved to file.

### ✅ PASS: Node - LOOP_OVER_ITEMS
**Details:** Successfully batched items.

### ✅ PASS: Node - MERGE
**Details:** Successfully appended multiple pins.

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
