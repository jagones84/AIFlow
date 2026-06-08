# Comprehensive Node & MCP Stress Test Report

## Summary
Total Tests: 27
Passed: 26
Failed: 1

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

### ❌ FAIL: Node - MERGE
**Details:** assert 1 == 2
 +  where 1 = len([FlowItem(json_data={'text': '### Unknown Source\n\n\nA\n\nB', 'parts': [{'source': 'Unknown Source', 'count': 2}]}, binary={})])
 +    where [FlowItem(json_data={'text': '### Unknown Source\n\n\nA\n\nB', 'parts': [{'source': 'Unknown Source', 'count': 2}]}, binary={})] = ExecutionResult(output='### Unknown Source\n\n\nA\n\nB', success=True, outputItems=[FlowItem(json_data={'text': '### U...e, iteratorBatches=None, loopBatches=None, doneItems=None, updatedNode=None, subWorkflowId=None, subWorkflowInput=None).outputItems

### ✅ PASS: MCP Server - filesystem
**Details:** Server running with 14 tools: ['read_file', 'read_text_file', 'read_media_file', 'read_multiple_files', 'write_file', 'edit_file', 'create_directory', 'list_directory', 'list_directory_with_sizes', 'directory_tree', 'move_file', 'search_files', 'get_file_info', 'list_allowed_directories']

### ✅ PASS: MCP Server - simple-datetime-server
**Details:** Server running with 1 tools: ['get_current_datetime']

### ✅ PASS: MCP Server - Brave Search
**Details:** Server running with 2 tools: ['brave_web_search', 'brave_local_search']

### ✅ PASS: MCP Server - Docker
**Details:** Server running with 4 tools: ['create-container', 'deploy-compose', 'get-logs', 'list-containers']

### ✅ PASS: MCP Server - Fetch
**Details:** Server running with 1 tools: ['fetch']

### ✅ PASS: MCP Server - mcp-reasoner
**Details:** Server running with 1 tools: ['mcp-reasoner']

### ✅ PASS: MCP Server - Memory
**Details:** Server running with 9 tools: ['create_entities', 'create_relations', 'add_observations', 'delete_entities', 'delete_observations', 'delete_relations', 'read_graph', 'search_nodes', 'open_nodes']

### ✅ PASS: MCP Server - Multi-Fetch
**Details:** Server running with 5 tools: ['fetch_html', 'fetch_json', 'fetch_txt', 'fetch_markdown', 'fetch_plaintext']

### ✅ PASS: MCP Server - python-local
**Details:** Server running with 3 tools: ['run_python_code', 'run_python_file', 'install_python_package']

### ✅ PASS: MCP Server - ucpf
**Details:** Server running with 3 tools: ['analyze_problem', 'creative_exploration', 'manage_state']

### ✅ PASS: MCP Server - yt-whisper
**Details:** Server running with 1 tools: ['transcribe_youtube_video']

### ✅ PASS: MCP Server - GitKraken
**Details:** Server running with 29 tools: ['app_tool_box', 'app_update_user_preferences', 'git_add_or_commit', 'git_blame', 'git_branch', 'git_checkout', 'git_fetch', 'git_graph', 'git_log_or_diff', 'git_pull', 'git_push', 'git_stash', 'git_status', 'git_worktree', 'gitkraken_workspace_list', 'gitlens_commit_composer', 'gitlens_launchpad', 'gitlens_start_review', 'gitlens_start_work', 'issues_add_comment', 'issues_assigned_to_me', 'issues_create', 'issues_get_detail', 'pull_request_assigned_to_me', 'pull_request_create', 'pull_request_create_review', 'pull_request_get_comments', 'pull_request_get_detail', 'repository_get_file_content']
