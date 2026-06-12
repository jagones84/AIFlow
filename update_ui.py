import re

file_path = r'f:\REPOSITORIES\AI_flow\src\web\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find start of FORM_SCHEMA
start_idx = content.find('const FORM_SCHEMA = {')
# Find end of saveProps()
end_idx = content.find('function openSettings() {')

if start_idx == -1 or end_idx == -1:
    print("Could not find boundaries")
    exit(1)

new_js = """const FORM_SCHEMA = {
            'TRIGGER': [
                { id: 'triggerType', label: 'Trigger Type', type: 'select', options: ['MANUAL', 'SCHEDULE', 'WEBHOOK'], default: 'MANUAL' },
                { id: 'triggerIntervalMinutes', label: 'Interval (Mins)', type: 'number', default: 15 },
                { id: 'triggerTime', label: 'Trigger Time', type: 'text', default: '' },
                { id: 'webhookPath', label: 'Webhook Path', type: 'text', default: 'my-hook' }
            ],
            'AI_AGENT': [
                { id: 'modelId', label: 'Model ID', type: 'text', default: 'qwen/qwen3.6-35b-a3b' },
                { id: 'systemPrompt', label: 'System Prompt', type: 'textarea', default: 'You are a helpful assistant.' },
                { id: 'allowedTools', label: 'Allowed Tools', type: 'multiselect', options: [], default: ['fetch_url', 'mcp__Brave Search', 'mcp__Multi-Fetch'] }
            ],
            'TOOL_EXECUTION': [
                { id: 'selectedToolName', label: 'Tool Name', type: 'select', options: ['fetch_url', 'web_search', 'calculator', 'get_current_time'], default: 'fetch_url' },
                { id: 'mcpToolName', label: 'MCP Specific Tool (if MCP Server)', type: 'text', default: '' },
                { id: 'mcpToolArgs', label: 'MCP Args (JSON)', type: 'textarea', default: '{"query": "{{ $json.text }}"}' }
            ],
            'ROUTER': [
                { id: 'routerMode', label: 'Mode', type: 'select', options: ['SIMPLE_RULE', 'AI_LLM'], default: 'SIMPLE_RULE' },
                { id: 'ruleCondition', label: 'Condition', type: 'text', default: 'expr: {{ $json.success }} == true' }
            ],
            'SWITCH': [
                { id: 'routerMode', label: 'Mode', type: 'select', options: ['SIMPLE_RULE', 'AI_LLM'], default: 'SIMPLE_RULE' },
                { id: 'switchRoutes', label: 'Routes', type: 'dynamicList', schema: [
                    { id: 'name', label: 'Route Name', type: 'text', default: 'Route' },
                    { id: 'condition', label: 'Condition', type: 'text', default: '' }
                ], default: [] }
            ],
            'PROMPT_INPUT': [
                { id: 'promptText', label: 'Prompt Text', type: 'textarea', default: 'latest soccer italian match with result, search for it' },
                { id: 'isInteractive', label: 'Interactive', type: 'checkbox', default: false }
            ],
            'JSON_PARSER': [
                { id: 'jsonSchema', label: 'Target Schema', type: 'textarea', default: '{"key": "string"}' }
            ],
            'JSON_FIELD_EXTRACT': [
                { id: 'ruleCondition', label: 'JSON Path', type: 'text', default: 'data.items[0]' }
            ],
            'MERGE': [
                { id: 'mergeMode', label: 'Mode', type: 'select', options: ['APPEND', 'WAIT', 'CHOOSE_BRANCH', 'COMBINE_BY_POSITION', 'COMBINE_BY_FIELDS', 'MULTIPLEX'], default: 'APPEND' },
                { id: 'mergeJoinType', label: 'Join Type', type: 'select', options: ['KEEP_MATCHES', 'KEEP_NON_MATCHES', 'KEEP_EVERYTHING', 'ENRICH_INPUT_1', 'ENRICH_INPUT_2'], default: 'KEEP_MATCHES' },
                { id: 'mergeInput1Field', label: 'Input 1 Match Field', type: 'text', default: '' },
                { id: 'mergeInput2Field', label: 'Input 2 Match Field', type: 'text', default: '' },
                { id: 'mergeOutputIndex', label: 'Choose Branch Index', type: 'number', default: 0 }
            ],
            'LOOP_OVER_ITEMS': [
                { id: 'batchSize', label: 'Batch Size', type: 'number', default: 1 }
            ],
            'VARIABLE_STORE': [
                { id: 'variableKey', label: 'Key', type: 'text', default: 'my_var' },
                { id: 'variableOperation', label: 'Operation', type: 'select', options: ['READ', 'WRITE', 'APPEND'], default: 'READ' }
            ],
            'HTTP_REQUEST': [
                { id: 'httpUrl', label: 'URL', type: 'text', default: 'https://api.example.com' },
                { id: 'httpMethod', label: 'Method', type: 'select', options: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], default: 'GET' },
                { id: 'httpHeaders', label: 'Headers', type: 'keyValue', default: {} },
                { id: 'httpBody', label: 'Body (JSON)', type: 'textarea', default: '' },
                { id: 'credentialId', label: 'Credential ID', type: 'text', default: '' }
            ],
            'WAIT': [
                { id: 'waitTimeMs', label: 'Wait Time (ms)', type: 'number', default: 1000 }
            ],
            'CODE': [
                { id: 'codeLanguage', label: 'Language', type: 'select', options: ['python', 'javascript'], default: 'python' },
                { id: 'codeBody', label: 'Code', type: 'textarea', default: 'output = "Hello from code"' }
            ],
            'SET': [
                { id: 'keepOnlySetFields', label: 'Keep Only Set Fields', type: 'checkbox', default: false },
                { id: 'setFields', label: 'Fields to Set', type: 'dynamicList', schema: [
                    { id: 'name', label: 'Name', type: 'text', default: 'field_name' },
                    { id: 'value', label: 'Value', type: 'text', default: '' },
                    { id: 'type', label: 'Type', type: 'select', options: ['string', 'number', 'boolean', 'object'], default: 'string' }
                ], default: [] }
            ],
            'EXECUTE_WORKFLOW': [
                { id: 'subWorkflowId', label: 'Sub-Workflow ID', type: 'text', default: '' },
                { id: 'subWorkflowMode', label: 'Mode', type: 'select', options: ['runOnceForAllItems', 'runOnceForEachItem'], default: 'runOnceForAllItems' },
                { id: 'waitForSubWorkflowCompletion', label: 'Wait for Completion', type: 'checkbox', default: true }
            ],
            'FILTER': [
                { id: 'ruleCondition', label: 'Condition', type: 'text', default: 'contains:error' }
            ],
            'SORT': [
                { id: 'sortFieldName', label: 'Field Name', type: 'text', default: 'id' },
                { id: 'sortOrder', label: 'Order', type: 'select', options: ['asc', 'desc'], default: 'asc' },
                { id: 'sortType', label: 'Type', type: 'select', options: ['string', 'number', 'date'], default: 'string' }
            ],
            'LIMIT': [
                { id: 'limitCount', label: 'Count', type: 'number', default: 10 },
                { id: 'limitOffset', label: 'Offset', type: 'number', default: 0 }
            ],
            'AGGREGATE': [
                { id: 'aggregateMode', label: 'Mode', type: 'select', options: ['allItemData', 'individualFields'], default: 'allItemData' },
                { id: 'aggregateInputField', label: 'Input Field (if individual)', type: 'text', default: '' },
                { id: 'aggregateOutputField', label: 'Output Field', type: 'text', default: 'data' },
                { id: 'aggregateMergeLists', label: 'Merge Lists', type: 'checkbox', default: false },
                { id: 'aggregateKeepMissing', label: 'Keep Missing', type: 'checkbox', default: false }
            ],
            'REMOVE_DUPLICATES': [
                { id: 'dedupeCompareAllFields', label: 'Compare All Fields', type: 'checkbox', default: true },
                { id: 'dedupeFields', label: 'Fields to Compare', type: 'stringList', default: [] }
            ],
            'SPLIT_OUT': [
                { id: 'splitOutField', label: 'Field to Split', type: 'text', default: '' }
            ],
            'SUMMARIZE': [
                { id: 'summarizeOutputFormat', label: 'Output Format', type: 'select', options: ['separateItems', 'singleItem'], default: 'separateItems' },
                { id: 'summarizeSplitBy', label: 'Split By Fields', type: 'stringList', default: [] },
                { id: 'summarizeFields', label: 'Fields to Summarize', type: 'dynamicList', schema: [
                    { id: 'field', label: 'Field', type: 'text', default: '' },
                    { id: 'aggregation', label: 'Aggregation', type: 'select', options: ['sum', 'average', 'count', 'max', 'min', 'append', 'concatenate'], default: 'sum' },
                    { id: 'includeEmpty', label: 'Include Empty', type: 'checkbox', default: false },
                    { id: 'separator', label: 'Separator', type: 'text', default: ', ' }
                ], default: [] }
            ],
            'HTML': [
                { id: 'htmlOperation', label: 'Operation', type: 'select', options: ['extract', 'generate', 'table'], default: 'extract' },
                { id: 'htmlSourceData', label: 'Source Data', type: 'select', options: ['json', 'binary'], default: 'json' },
                { id: 'htmlProperty', label: 'Property', type: 'text', default: 'data' },
                { id: 'htmlTemplate', label: 'HTML Template', type: 'textarea', default: '' },
                { id: 'htmlExtractionValues', label: 'Extraction Values', type: 'dynamicList', schema: [
                    { id: 'key', label: 'Key', type: 'text', default: '' },
                    { id: 'cssSelector', label: 'CSS Selector', type: 'text', default: '' },
                    { id: 'returnValue', label: 'Return Value', type: 'select', options: ['text', 'html', 'attribute', 'value'], default: 'text' },
                    { id: 'attribute', label: 'Attribute (if needed)', type: 'text', default: '' },
                    { id: 'returnArray', label: 'Return Array', type: 'checkbox', default: false }
                ], default: [] }
            ],
            'STOP_AND_ERROR': [
                { id: 'errorMessage', label: 'Error Message', type: 'text', default: '' },
                { id: 'stopAndErrorType', label: 'Error Type', type: 'select', options: ['message', 'object'], default: 'message' },
                { id: 'stopAndErrorObject', label: 'Error Object (JSON)', type: 'textarea', default: '' }
            ]
        };

        // Common fields for all nodes
        const COMMON_SCHEMA = [
            { id: 'continueOnError', label: 'Continue On Error', type: 'checkbox', default: false },
            { id: 'maxIterations', label: 'Max Iterations', type: 'number', default: 3 },
            { id: 'waitForAllInputs', label: 'Wait For All Inputs', type: 'checkbox', default: false },
            { id: 'executeOnce', label: 'Execute Once', type: 'checkbox', default: false },
            { id: 'alwaysOutputAtLeastOneItem', label: 'Always Output at Least One Item', type: 'checkbox', default: false },
            { id: 'notes', label: 'Notes', type: 'textarea', default: '' }
        ];

        // UI Event Listeners
        window.lastExecutionResults = {};
        let currentSelectedId = null;
        let currentFormState = {}; // Used to keep track of dynamic lists/objects

        function renderFormFields(schema, config, parentElement, pathPrefix = '') {
            schema.forEach(field => {
                const div = document.createElement('div');
                div.className = 'form-group';
                const fieldId = pathPrefix ? `${pathPrefix}_${field.id}` : `prop_${field.id}`;
                const val = config[field.id] !== undefined ? config[field.id] : field.default;
                
                if (field.type === 'checkbox') {
                    div.className = 'form-group checkbox-group';
                    div.innerHTML = `
                        <input type="checkbox" id="${fieldId}" ${val ? 'checked' : ''}>
                        <label for="${fieldId}" style="margin:0;">${field.label}</label>
                    `;
                } else if (field.type === 'select') {
                    let opts = field.options.map(o => `<option value="${o}" ${o===val ? 'selected' : ''}>${o}</option>`).join('');
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <select id="${fieldId}">${opts}</select>
                    `;
                } else if (field.type === 'multiselect') {
                    let checks = field.options.map(o => {
                        const isChecked = (val || []).includes(o) ? 'checked' : '';
                        return `<div><input type="checkbox" value="${o}" class="multi-check-${fieldId}" ${isChecked}> <span style="font-size:11px;">${o}</span></div>`;
                    }).join('');
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <div style="max-height: 100px; overflow-y: auto; border: 1px solid #ccc; padding: 5px; border-radius: 4px; background: #fff;">
                            ${checks}
                        </div>
                    `;
                } else if (field.type === 'textarea') {
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <textarea id="${fieldId}">${val}</textarea>
                    `;
                } else if (field.type === 'dynamicList') {
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <div id="${fieldId}_container" style="border: 1px solid #ddd; padding: 5px; background: #f9f9f9; border-radius: 4px;"></div>
                        <button type="button" onclick="addDynamicListItem('${fieldId}', ${JSON.stringify(field.schema).replace(/"/g, '&quot;')})" style="margin-top: 5px; font-size: 11px; padding: 4px;">+ Add Item</button>
                    `;
                    currentFormState[fieldId] = val || [];
                    parentElement.appendChild(div);
                    renderDynamicList(fieldId, field.schema);
                    return; // Skip normal append
                } else if (field.type === 'stringList') {
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <div id="${fieldId}_container" style="border: 1px solid #ddd; padding: 5px; background: #f9f9f9; border-radius: 4px;"></div>
                        <button type="button" onclick="addStringListItem('${fieldId}')" style="margin-top: 5px; font-size: 11px; padding: 4px;">+ Add Item</button>
                    `;
                    currentFormState[fieldId] = val || [];
                    parentElement.appendChild(div);
                    renderStringList(fieldId);
                    return; // Skip normal append
                } else if (field.type === 'keyValue') {
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <div id="${fieldId}_container" style="border: 1px solid #ddd; padding: 5px; background: #f9f9f9; border-radius: 4px;"></div>
                        <button type="button" onclick="addKeyValueItem('${fieldId}')" style="margin-top: 5px; font-size: 11px; padding: 4px;">+ Add Header</button>
                    `;
                    currentFormState[fieldId] = val || {};
                    parentElement.appendChild(div);
                    renderKeyValueList(fieldId);
                    return; // Skip normal append
                } else {
                    div.innerHTML = `
                        <label>${field.label}</label>
                        <input type="${field.type}" id="${fieldId}" value="${val}">
                    `;
                }
                parentElement.appendChild(div);
            });
        }

        function renderDynamicList(fieldId, schema) {
            const container = document.getElementById(fieldId + '_container');
            container.innerHTML = '';
            const items = currentFormState[fieldId] || [];
            
            items.forEach((item, index) => {
                const itemDiv = document.createElement('div');
                itemDiv.style.border = '1px solid #ccc';
                itemDiv.style.padding = '5px';
                itemDiv.style.marginBottom = '5px';
                itemDiv.style.background = '#fff';
                itemDiv.style.position = 'relative';
                
                const deleteBtn = document.createElement('button');
                deleteBtn.innerHTML = '✖';
                deleteBtn.style.position = 'absolute';
                deleteBtn.style.right = '5px';
                deleteBtn.style.top = '5px';
                deleteBtn.style.background = 'none';
                deleteBtn.style.border = 'none';
                deleteBtn.style.color = '#e74c3c';
                deleteBtn.style.cursor = 'pointer';
                deleteBtn.onclick = () => {
                    saveDynamicListState(fieldId, schema);
                    currentFormState[fieldId].splice(index, 1);
                    renderDynamicList(fieldId, schema);
                };
                itemDiv.appendChild(deleteBtn);
                
                renderFormFields(schema, item, itemDiv, `${fieldId}_${index}`);
                container.appendChild(itemDiv);
            });
        }

        function addDynamicListItem(fieldId, schema) {
            saveDynamicListState(fieldId, schema);
            const newItem = {};
            schema.forEach(f => newItem[f.id] = f.default);
            currentFormState[fieldId].push(newItem);
            renderDynamicList(fieldId, schema);
        }

        function saveDynamicListState(fieldId, schema) {
            const items = currentFormState[fieldId] || [];
            items.forEach((item, index) => {
                schema.forEach(f => {
                    const elId = `${fieldId}_${index}_${f.id}`;
                    const el = document.getElementById(elId);
                    if (el) {
                        if (f.type === 'checkbox') item[f.id] = el.checked;
                        else if (f.type === 'number') item[f.id] = Number(el.value);
                        else item[f.id] = el.value;
                    }
                });
            });
        }

        function renderStringList(fieldId) {
            const container = document.getElementById(fieldId + '_container');
            container.innerHTML = '';
            const items = currentFormState[fieldId] || [];
            
            items.forEach((item, index) => {
                const itemDiv = document.createElement('div');
                itemDiv.style.display = 'flex';
                itemDiv.style.marginBottom = '5px';
                
                const input = document.createElement('input');
                input.type = 'text';
                input.id = `${fieldId}_${index}`;
                input.value = item;
                input.style.flex = '1';
                
                const deleteBtn = document.createElement('button');
                deleteBtn.innerHTML = '✖';
                deleteBtn.style.background = 'none';
                deleteBtn.style.border = 'none';
                deleteBtn.style.color = '#e74c3c';
                deleteBtn.style.cursor = 'pointer';
                deleteBtn.onclick = () => {
                    saveStringListState(fieldId);
                    currentFormState[fieldId].splice(index, 1);
                    renderStringList(fieldId);
                };
                
                itemDiv.appendChild(input);
                itemDiv.appendChild(deleteBtn);
                container.appendChild(itemDiv);
            });
        }

        function addStringListItem(fieldId) {
            saveStringListState(fieldId);
            currentFormState[fieldId].push('');
            renderStringList(fieldId);
        }

        function saveStringListState(fieldId) {
            const items = currentFormState[fieldId] || [];
            items.forEach((item, index) => {
                const el = document.getElementById(`${fieldId}_${index}`);
                if (el) {
                    currentFormState[fieldId][index] = el.value;
                }
            });
        }

        function renderKeyValueList(fieldId) {
            const container = document.getElementById(fieldId + '_container');
            container.innerHTML = '';
            const dict = currentFormState[fieldId] || {};
            const keys = Object.keys(dict);
            
            keys.forEach((key, index) => {
                const itemDiv = document.createElement('div');
                itemDiv.style.display = 'flex';
                itemDiv.style.marginBottom = '5px';
                itemDiv.style.gap = '5px';
                
                const inputKey = document.createElement('input');
                inputKey.type = 'text';
                inputKey.id = `${fieldId}_key_${index}`;
                inputKey.value = key;
                inputKey.placeholder = 'Key';
                inputKey.style.width = '40%';
                
                const inputVal = document.createElement('input');
                inputVal.type = 'text';
                inputVal.id = `${fieldId}_val_${index}`;
                inputVal.value = dict[key];
                inputVal.placeholder = 'Value';
                inputVal.style.flex = '1';
                
                const deleteBtn = document.createElement('button');
                deleteBtn.innerHTML = '✖';
                deleteBtn.style.background = 'none';
                deleteBtn.style.border = 'none';
                deleteBtn.style.color = '#e74c3c';
                deleteBtn.style.cursor = 'pointer';
                deleteBtn.onclick = () => {
                    saveKeyValueState(fieldId);
                    const currentKeys = Object.keys(currentFormState[fieldId]);
                    delete currentFormState[fieldId][currentKeys[index]];
                    renderKeyValueList(fieldId);
                };
                
                itemDiv.appendChild(inputKey);
                itemDiv.appendChild(inputVal);
                itemDiv.appendChild(deleteBtn);
                container.appendChild(itemDiv);
            });
        }

        function addKeyValueItem(fieldId) {
            saveKeyValueState(fieldId);
            let newKey = 'New_Key';
            let counter = 1;
            while(currentFormState[fieldId].hasOwnProperty(newKey)) {
                newKey = 'New_Key_' + counter;
                counter++;
            }
            currentFormState[fieldId][newKey] = '';
            renderKeyValueList(fieldId);
        }

        function saveKeyValueState(fieldId) {
            const dict = currentFormState[fieldId] || {};
            const keys = Object.keys(dict);
            const newDict = {};
            keys.forEach((key, index) => {
                const elKey = document.getElementById(`${fieldId}_key_${index}`);
                const elVal = document.getElementById(`${fieldId}_val_${index}`);
                if (elKey && elVal) {
                    const k = elKey.value.trim() || 'Empty_Key_' + index;
                    newDict[k] = elVal.value;
                }
            });
            currentFormState[fieldId] = newDict;
        }

        editor.on('nodeSelected', function(id) {
            if (currentSelectedId === id) return;
            currentSelectedId = id;
            
            const node = editor.getNodeFromId(id);
            const type = node.data.type;
            const config = node.data.config || {};
            
            document.getElementById('props-id').value = id;
            document.getElementById('props-panel').style.display = 'block';
            
            const form = document.getElementById('dynamic-form');
            form.innerHTML = '';
            currentFormState = {};
            
            const schema = (FORM_SCHEMA[type] || []).concat(COMMON_SCHEMA);
            renderFormFields(schema, config, form);

            // Populate I/O Panel
            const ioPanel = document.getElementById('node-io-panel');
            const res = window.lastExecutionResults[id];
            if (res) {
                ioPanel.innerHTML = `
                    <div style="background: #eaf2f8; padding: 5px; border-radius: 4px; margin-bottom: 10px; border-left: 3px solid #3498db;">
                        <strong style="font-size: 11px; color: #2c3e50;">Iteration: ${res.executionCount || 0} | Status: ${res.status || 'UNKNOWN'}</strong>
                    </div>
                    <h5 style="margin:0 0 5px 0; color: #2c3e50;">Last Input</h5>
                    <pre style="font-size:11px; max-height:200px; overflow-y:auto; background:#f8f9fa; padding:8px; border: 1px solid #ddd; border-radius: 4px; margin:0 0 10px 0; white-space:pre-wrap; word-wrap:break-word;">${JSON.stringify(res.lastInputItems, null, 2)}</pre>
                    <h5 style="margin:0 0 5px 0; color: #2c3e50;">Last Output</h5>
                    <pre style="font-size:11px; max-height:200px; overflow-y:auto; background:#f8f9fa; padding:8px; border: 1px solid #ddd; border-radius: 4px; margin:0; white-space:pre-wrap; word-wrap:break-word;">${JSON.stringify(res.lastOutputItems, null, 2)}</pre>
                `;
            } else {
                ioPanel.innerHTML = '<em style="font-size:11px; color:#7f8c8d;">No execution data yet. Run the workflow first.</em>';
            }
        });

        editor.on('nodeUnselected', function() {
            currentSelectedId = null;
            document.getElementById('props-panel').style.display = 'none';
        });

        function extractFieldValues(schema, configObj, pathPrefix = '') {
            schema.forEach(field => {
                const fieldId = pathPrefix ? `${pathPrefix}_${field.id}` : `prop_${field.id}`;
                
                if (field.type === 'dynamicList') {
                    saveDynamicListState(fieldId, field.schema);
                    configObj[field.id] = currentFormState[fieldId];
                } else if (field.type === 'stringList') {
                    saveStringListState(fieldId);
                    configObj[field.id] = currentFormState[fieldId];
                } else if (field.type === 'keyValue') {
                    saveKeyValueState(fieldId);
                    configObj[field.id] = currentFormState[fieldId];
                } else if (field.type === 'multiselect') {
                    const checkboxes = document.querySelectorAll(`.multi-check-${fieldId}:checked`);
                    configObj[field.id] = Array.from(checkboxes).map(c => c.value);
                } else {
                    const el = document.getElementById(fieldId);
                    if (el) {
                        if (field.type === 'checkbox') {
                            configObj[field.id] = el.checked;
                        } else if (field.type === 'number') {
                            configObj[field.id] = Number(el.value);
                        } else {
                            configObj[field.id] = el.value;
                        }
                    }
                }
            });
        }

        function saveProps() {
            const id = document.getElementById('props-id').value;
            if(!id) return;
            
            const node = editor.getNodeFromId(id);
            const type = node.data.type;
            const schema = (FORM_SCHEMA[type] || []).concat(COMMON_SCHEMA);
            
            const newConfig = {};
            extractFieldValues(schema, newConfig);
            
            node.data.config = newConfig;
            
            // CRITICAL: Sync config fields to top-level node.data for backend compatibility
            Object.assign(node.data, newConfig);
            
            editor.updateNodeDataFromId(id, node.data);
            
            // Visual feedback
            const btn = document.querySelector('.save-btn');
            const oldText = btn.innerText;
            btn.innerText = "✅ Saved!";
            setTimeout(() => btn.innerText = oldText, 1000);
            
            // Update node UI if needed (like changing outputs count for SWITCH)
            if (type === 'SWITCH') {
                updateSwitchNodeOutputs(id, newConfig.switchRoutes || []);
            }
        }
        
        function updateSwitchNodeOutputs(nodeId, routes) {
            const node = editor.getNodeFromId(nodeId);
            if (!node) return;
            // Drawflow logic: node.outputs contains {"output_1": {connections: []}, "output_2": ...}
            // By default SWITCH has 3 outputs. If we want dynamic outputs, we'd need to modify drawflow node HTML and outputs.
            // Currently Drawflow doesn't easily support adding/removing outputs dynamically without removing/re-adding the node,
            // but we can try using editor.addNodeOutput and editor.removeNodeOutput.
            
            const currentOutputCount = Object.keys(node.outputs).length;
            const targetOutputCount = routes.length + 1; // Routes + default branch
            
            if (currentOutputCount < targetOutputCount) {
                for (let i = currentOutputCount + 1; i <= targetOutputCount; i++) {
                    editor.addNodeOutput(nodeId);
                }
            } else if (currentOutputCount > targetOutputCount) {
                // Be careful not to remove outputs that have connections
                for (let i = currentOutputCount; i > targetOutputCount; i--) {
                    const outputClass = "output_" + i;
                    if (node.outputs[outputClass] && node.outputs[outputClass].connections.length > 0) {
                        alert("Cannot remove route because it has connections. Remove connections first.");
                        break; // Stop removing
                    }
                    editor.removeNodeOutput(nodeId, outputClass);
                }
            }
        }
"""

content = content[:start_idx] + new_js + "\n        " + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated index.html successfully")
