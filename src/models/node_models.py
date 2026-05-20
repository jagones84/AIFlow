from enum import Enum
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict

class NodeType(str, Enum):
    TRIGGER = "TRIGGER"
    ERROR_TRIGGER = "ERROR_TRIGGER"
    AI_AGENT = "AI_AGENT"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    ROUTER = "ROUTER"
    SWITCH = "SWITCH"
    USER_INPUT = "USER_INPUT"
    PROMPT_INPUT = "PROMPT_INPUT"
    KNOWLEDGE = "KNOWLEDGE"
    OUTPUT_DISPLAY = "OUTPUT_DISPLAY"
    JSON_PARSER = "JSON_PARSER"
    JSON_FIELD_EXTRACT = "JSON_FIELD_EXTRACT"
    MERGE = "MERGE"
    LOOP_OVER_ITEMS = "LOOP_OVER_ITEMS"
    VARIABLE_STORE = "VARIABLE_STORE"
    FILE_SAVE = "FILE_SAVE"
    STOP_AND_ERROR = "STOP_AND_ERROR"
    HTTP_REQUEST = "HTTP_REQUEST"
    WAIT = "WAIT"
    CODE = "CODE"
    SET = "SET"
    EXECUTE_WORKFLOW = "EXECUTE_WORKFLOW"
    FILTER = "FILTER"
    SORT = "SORT"
    LIMIT = "LIMIT"
    AGGREGATE = "AGGREGATE"
    REMOVE_DUPLICATES = "REMOVE_DUPLICATES"
    SPLIT_OUT = "SPLIT_OUT"
    SUMMARIZE = "SUMMARIZE"
    HTML = "HTML"

class TriggerType(str, Enum):
    MANUAL = "MANUAL"
    SCHEDULE = "SCHEDULE"
    WEBHOOK = "WEBHOOK"

class NodeStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    SKIPPED = "SKIPPED"

class RouterMode(str, Enum):
    AI_LLM = "AI_LLM"
    SIMPLE_RULE = "SIMPLE_RULE"

class VariableOperation(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    APPEND = "APPEND"

class MergeMode(str, Enum):
    APPEND = "APPEND"
    COMBINE_BY_POSITION = "COMBINE_BY_POSITION"
    COMBINE_BY_FIELDS = "COMBINE_BY_FIELDS"
    MULTIPLEX = "MULTIPLEX"
    CHOOSE_BRANCH = "CHOOSE_BRANCH"
    WAIT = "WAIT"

class MergeJoinType(str, Enum):
    KEEP_MATCHES = "KEEP_MATCHES"
    KEEP_NON_MATCHES = "KEEP_NON_MATCHES"
    KEEP_EVERYTHING = "KEEP_EVERYTHING"
    ENRICH_INPUT_1 = "ENRICH_INPUT_1"
    ENRICH_INPUT_2 = "ENRICH_INPUT_2"

class RouteDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    condition: str

class SetFieldDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    value: str
    type: str = "string"

class SummarizeFieldDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    field: str
    aggregation: str = "sum"
    includeEmpty: bool = False
    separator: str = ", "

class HtmlExtractionValue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str
    cssSelector: str
    returnValue: str = "text"
    attribute: Optional[str] = None
    returnArray: bool = False

class Pin(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    parentNodeId: str = ""

class FlowBinary(BaseModel):
    dataBase64: str
    mimeType: Optional[str] = None
    fileName: Optional[str] = None

class FlowItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    json_data: Dict[str, Any] = Field(default_factory=dict, alias="json")
    binary: Dict[str, FlowBinary] = Field(default_factory=dict)

class FlowPayload(BaseModel):
    itemsByPinId: Dict[str, List[FlowItem]] = Field(default_factory=dict)

    def all_items(self) -> List[FlowItem]:
        items = []
        for v in self.itemsByPinId.values():
            items.extend(v)
        return items

    def merged_with(self, other: "FlowPayload") -> "FlowPayload":
        if not self.itemsByPinId:
            return other
        if not other.itemsByPinId:
            return self
            
        merged = {}
        keys = set(self.itemsByPinId.keys()).union(set(other.itemsByPinId.keys()))
        for key in keys:
            left = self.itemsByPinId.get(key, [])
            right = other.itemsByPinId.get(key, [])
            if left or right:
                merged[key] = left + right
        return FlowPayload(itemsByPinId=merged)

    @staticmethod
    def from_items(items: List[FlowItem]) -> "FlowPayload":
        return FlowPayload(itemsByPinId={"": items})

class NodeData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    type: NodeType
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    
    inputs: List[Pin] = Field(default_factory=list)
    outputs: List[Pin] = Field(default_factory=list)
    
    # Configuration
    modelId: str = "qwen/qwen3.6-35b-a3b"
    systemPrompt: str = "You are a helpful assistant."
    allowedTools: List[str] = Field(default_factory=list)
    
    selectedToolName: Optional[str] = None
    mcpToolName: Optional[str] = None
    mcpToolArgs: Optional[str] = None
    
    triggerType: TriggerType = TriggerType.MANUAL
    triggerIntervalMinutes: int = 15
    triggerTime: Optional[str] = None
    webhookPath: Optional[str] = None
    
    userInstruction: Optional[str] = None
    promptText: Optional[str] = None
    isInteractive: bool = False
    
    attachedUris: List[str] = Field(default_factory=list)
    
    jsonSchema: Optional[str] = None
    
    routerMode: RouterMode = RouterMode.AI_LLM
    ruleCondition: Optional[str] = None
    
    switchRoutes: List[RouteDefinition] = Field(default_factory=list)
    
    mergeMode: MergeMode = MergeMode.APPEND
    mergeJoinType: MergeJoinType = MergeJoinType.KEEP_MATCHES
    mergeInput1Field: Optional[str] = None
    mergeInput2Field: Optional[str] = None
    mergeOutputIndex: int = 0
    
    variableKey: Optional[str] = None
    variableOperation: VariableOperation = VariableOperation.READ
    
    fileName: Optional[str] = None
    
    batchSize: int = 50
    
    errorMessage: Optional[str] = None
    
    httpUrl: Optional[str] = None
    httpMethod: str = "GET"
    httpHeaders: Dict[str, str] = Field(default_factory=dict)
    httpBody: Optional[str] = None
    credentialId: Optional[str] = None
    
    waitTimeMs: int = 1000
    
    codeLanguage: str = "python"
    codeBody: Optional[str] = None
    
    setFields: List[SetFieldDefinition] = Field(default_factory=list)
    keepOnlySetFields: bool = False
    
    subWorkflowId: Optional[str] = None
    subWorkflowMode: str = "runOnceForAllItems"
    waitForSubWorkflowCompletion: bool = True
    
    sortFieldName: Optional[str] = None
    sortOrder: str = "asc"
    sortType: str = "string"
    
    limitCount: int = 10
    limitOffset: int = 0
    
    aggregateMode: str = "allItemData"
    aggregateInputField: Optional[str] = None
    aggregateOutputField: str = "data"
    aggregateMergeLists: bool = False
    aggregateKeepMissing: bool = False
    
    dedupeFields: List[str] = Field(default_factory=list)
    dedupeCompareAllFields: bool = True
    
    splitOutField: Optional[str] = None
    
    summarizeFields: List[SummarizeFieldDefinition] = Field(default_factory=list)
    summarizeSplitBy: List[str] = Field(default_factory=list)
    summarizeOutputFormat: str = "separateItems"
    
    htmlOperation: str = "extract"
    htmlSourceData: str = "json"
    htmlProperty: str = "data"
    htmlExtractionValues: List[HtmlExtractionValue] = Field(default_factory=list)
    htmlTemplate: Optional[str] = None
    
    stopAndErrorType: str = "message"
    stopAndErrorObject: Optional[str] = None
    
    maxIterations: int = 3
    continueOnError: bool = False
    executeOnce: bool = False
    alwaysOutputAtLeastOneItem: bool = False
    waitForAllInputs: bool = False
    notes: Optional[str] = None
    
    # Runtime State
    status: NodeStatus = NodeStatus.IDLE
    lastInput: Optional[str] = None
    lastOutput: Optional[str] = None
    lastInputItems: List[FlowItem] = Field(default_factory=list)
    lastOutputItems: List[FlowItem] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    executionCount: int = 0
    staticData: Dict[str, Any] = Field(default_factory=dict)

class Connection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fromNodeId: str
    fromPinId: str
    toNodeId: str
    toPinId: str

class FlowProjectData(BaseModel):
    name: str = "Untitled Project"
    nodes: List[NodeData]
    connections: List[Connection]
