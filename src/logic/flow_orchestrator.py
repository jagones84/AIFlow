import asyncio
import time
from typing import List, Dict, Callable, Optional, Set
from collections import deque

from src.models.node_models import NodeData, Connection, FlowProjectData, NodeStatus, NodeType, FlowPayload, FlowItem, MergeMode
from src.logic.node_executor import NodeExecutor
from src.logic.flow_graph_traverser import FlowGraphTraverser
from src.utils.managers import LogManager

class FlowOrchestrator:
    def __init__(
        self,
        node_executor: NodeExecutor,
        get_nodes: Callable[[], List[NodeData]],
        get_connections: Callable[[], List[Connection]],
        update_nodes: Callable[[List[NodeData]], None],
        update_connections: Callable[[List[Connection]], None] = lambda c: None,
        load_flow: Callable[[str], Optional[FlowProjectData]] = lambda id: None
    ):
        self.node_executor = node_executor
        self.get_nodes = get_nodes
        self.get_connections = get_connections
        self.update_nodes = update_nodes
        self.update_connections = update_connections
        self.load_flow = load_flow

        self.is_flow_running = False
        self.is_flow_paused = False
        self.is_flow_stuck = False
        
        self.execution_logs = []
        self.node_failures = {}
        
        self.node_start_times = {}
        self.active_job_count = 0
        self.pending_execution_queue = deque()
        self.runtime_payload_by_node_id: Dict[str, FlowPayload] = {}
        
        self._state_lock = asyncio.Lock()
        self._monitor_task = None

    def _log(self, message: str):
        LogManager.info("FlowOrchestrator", message)

    def _log_error(self, message: str):
        LogManager.error("FlowOrchestrator", message)

    async def start_flow(self):
        if self.is_flow_running:
            return
            
        self.is_flow_running = True
        self.is_flow_paused = False
        self.is_flow_stuck = False
        self.node_start_times.clear()
        self.active_job_count = 0
        self.pending_execution_queue.clear()
        self.runtime_payload_by_node_id.clear()
        self.execution_logs = []
        self.node_failures.clear()
        
        self._log("Flow Started")
        
        # Monitor task
        async def monitor():
            while self.is_flow_running:
                await asyncio.sleep(5)
                now = time.time() * 1000
                stuck = False
                for nid, start in self.node_start_times.items():
                    if now - start > 180000:  # 3 minutes instead of 45 seconds to allow LLMs to search the web
                        stuck = True
                        nodes = self.get_nodes()
                        node = next((n for n in nodes if n.id == nid), None)
                        if node and node.status == NodeStatus.RUNNING:
                            self._log(f"WARNING: Node '{node.title}' appears stuck.")
                self.is_flow_stuck = stuck
                
        self._monitor_task = asyncio.create_task(monitor())

        async with self._state_lock:
            nodes = self.get_nodes()
            reset_nodes = []
            for n in nodes:
                n_copy = n.model_copy(deep=True)
                n_copy.status = NodeStatus.IDLE
                n_copy.lastOutput = None
                n_copy.lastInput = None
                n_copy.lastInputItems = []
                n_copy.lastOutputItems = []
                n_copy.context = {}
                n_copy.executionCount = 0
                reset_nodes.append(n_copy)
            self.update_nodes(reset_nodes)

        try:
            nodes = self.get_nodes()
            trigger_nodes = [n for n in nodes if n.type == NodeType.TRIGGER]
            if not trigger_nodes:
                self._log_error("No TRIGGER nodes found.")
                self.is_flow_running = False
                if self._monitor_task:
                    self._monitor_task.cancel()
                return

            self._log(f"Starting flow with {len(trigger_nodes)} Trigger node(s).")
            for t in trigger_nodes:
                await self._launch_node_execution(t)
        except Exception as e:
            self._log_error(f"Error starting flow: {str(e)}")
            self.is_flow_running = False

    def stop_flow(self):
        self.is_flow_running = False
        self.is_flow_paused = False
        self.is_flow_stuck = False
        self.node_start_times.clear()
        self.active_job_count = 0
        self.pending_execution_queue.clear()
        if self._monitor_task:
            self._monitor_task.cancel()
        self._log("Flow Stopped by User")

    async def _launch_node_execution(self, node: NodeData):
        if node.type not in (NodeType.TRIGGER, NodeType.ERROR_TRIGGER):
            if not any(c.toNodeId == node.id for c in self.get_connections()):
                self._log(f"Skipping node '{node.title}': no incoming connections.")
                return

        if self.is_flow_paused:
            self._log(f"Paused. Node '{node.title}' queued.")
            self.pending_execution_queue.append(node)
            return

        self.active_job_count += 1
        # Add a tiny artificial delay before spawning the task to ensure log ordering
        # matches the breadth-first traversal logic in async environments
        await asyncio.sleep(0.01)
        asyncio.create_task(self._execute_node_task(node))

    async def _execute_node_task(self, node: NodeData):
        try:
            await self._execute_node(node)
        finally:
            self.active_job_count -= 1
            if self.active_job_count == 0 and not self.pending_execution_queue:
                self._check_if_finished()

    async def _atomic_update(self, action: Callable[[List[NodeData]], List[NodeData]]):
        async with self._state_lock:
            current = self.get_nodes()
            new_nodes = action(current)
            self.update_nodes(new_nodes)

    async def _update_node_status(self, nid: str, status: NodeStatus, execution_count: Optional[int] = None):
        now = time.time() * 1000
        if status == NodeStatus.RUNNING:
            self.node_start_times[nid] = now
        elif status in (NodeStatus.SUCCESS, NodeStatus.FAILURE, NodeStatus.WAITING_FOR_USER):
            self.node_start_times.pop(nid, None)

        def action(nodes: List[NodeData]) -> List[NodeData]:
            res = []
            for n in nodes:
                if n.id == nid:
                    n_copy = n.model_copy(deep=True)
                    n_copy.status = status
                    if execution_count is not None:
                        n_copy.executionCount = execution_count
                    if status == NodeStatus.RUNNING:
                        n_copy.context["lastStartMs"] = now
                    res.append(n_copy)
                else:
                    res.append(n)
            return res
        await self._atomic_update(action)

    async def _execute_node(self, node: NodeData):
        if not self.is_flow_running:
            return

        if node.executionCount >= node.maxIterations:
            self.node_failures[node.id] = f"Max iterations ({node.maxIterations}) reached."
            await self._update_node_status(node.id, NodeStatus.FAILURE)
            return

        is_merge_sync = node.type == NodeType.MERGE and node.mergeMode in (
            MergeMode.WAIT, MergeMode.COMBINE_BY_POSITION, MergeMode.COMBINE_BY_FIELDS, MergeMode.MULTIPLEX
        )

        if node.waitForAllInputs or is_merge_sync:
            conns = self.get_connections()
            # Only consider connections that actually target this node
            parent_conns = [c for c in conns if c.toNodeId == node.id]
            parent_ids = {c.fromNodeId for c in parent_conns}
            
            if parent_ids:
                nodes = self.get_nodes()
                # Find all parent nodes
                parents = [n for n in nodes if n.id in parent_ids]
                
                # We need to wait if ANY parent is still running or idle
                # Note: SKIPPED is considered a terminal state, but if a node is IDLE it hasn't run yet
                pending_parents = [p for p in parents if p.status in (NodeStatus.IDLE, NodeStatus.RUNNING, NodeStatus.WAITING_FOR_USER)]
                
                if pending_parents:
                    self._log(f"Node '{node.title}' (ID: {node.id}) waiting for inputs from parents: {[p.id for p in pending_parents]}")
                    return

        started_at = time.time() * 1000
        current_count = node.executionCount + 1
        await self._update_node_status(node.id, NodeStatus.RUNNING, current_count)
        self._log(f"Executing Node: {node.title}")

        # Artificial delay to allow the UI polling (every 500ms) to catch the RUNNING state
        # and animate the green border, making the execution flow visually clear to the user.
        await asyncio.sleep(0.6)

        payload = self.runtime_payload_by_node_id.get(node.id)
        input_items = payload.all_items() if payload else []

        def update_inputs(nodes):
            res = []
            for n in nodes:
                if n.id == node.id:
                    n_copy = n.model_copy(deep=True)
                    n_copy.lastInputItems = input_items
                    res.append(n_copy)
                else:
                    res.append(n)
            return res
        await self._atomic_update(update_inputs)

        try:
            # Execute on a separate thread to avoid blocking the asyncio event loop
            # This allows FastAPI to serve /api/status requests concurrently!
            
            def append_log_callback(msg: str):
                self._log(msg)
                
            def check_running_callback() -> bool:
                return self.is_flow_running
                
            result = await asyncio.to_thread(
                self.node_executor.execute,
                node, input_items, self.get_nodes(), self.runtime_payload_by_node_id, append_log_callback, check_running_callback
            )
            self.runtime_payload_by_node_id.pop(node.id, None)
        except Exception as e:
            self.runtime_payload_by_node_id.pop(node.id, None)
            from src.logic.node_executor import ExecutionResult
            result = ExecutionResult(
                output=f"Exception: {str(e)}",
                success=False
            )

        if result.updatedNode:
            def update_node_data(nodes):
                return [result.updatedNode if n.id == result.updatedNode.id else n for n in nodes]
            await self._atomic_update(update_node_data)

        if result.success:
            def update_outputs(nodes):
                res = []
                for n in nodes:
                    if n.id == node.id:
                        n_copy = n.model_copy(deep=True)
                        n_copy.lastOutput = result.output
                        n_copy.lastOutputItems = result.outputItems
                        res.append(n_copy)
                    else:
                        res.append(n)
                return res
            await self._atomic_update(update_outputs)

            await self._update_node_status(node.id, NodeStatus.SUCCESS)

            if result.shouldTriggerNext:
                await self._trigger_next_nodes(node, result.outputItems)
        else:
            def update_outputs_err(nodes):
                res = []
                for n in nodes:
                    if n.id == node.id:
                        n_copy = n.model_copy(deep=True)
                        n_copy.lastOutput = result.output
                        res.append(n_copy)
                    else:
                        res.append(n)
                return res
            await self._atomic_update(update_outputs_err)
            
            await self._update_node_status(node.id, NodeStatus.FAILURE)
            self.node_failures[node.id] = result.output

            if node.type == NodeType.STOP_AND_ERROR or result.shouldStopFlow:
                self.stop_flow()
                return

            if node.continueOnError and result.shouldTriggerNext:
                self._log(f"Continue on error: {node.title}")
                await self._trigger_next_nodes(node, result.outputItems)

    async def resume_node(self, node_id: str, user_text: str):
        nodes = self.get_nodes()
        node = next((n for n in nodes if n.id == node_id), None)
        if node and node.status == NodeStatus.WAITING_FOR_USER:
            self._log(f"User provided input for node '{node.title}': {user_text}")
            
            # Update node output and set status to SUCCESS
            from src.models.node_models import FlowItem
            out_item = FlowItem(json_data={"text": user_text})
            
            async def update_action(nodes):
                res = []
                for n in nodes:
                    if n.id == node_id:
                        n_copy = n.model_copy(deep=True)
                        n_copy.lastOutput = user_text
                        n_copy.lastOutputItems = [out_item]
                        res.append(n_copy)
                    else:
                        res.append(n)
                return res
                
            await self._atomic_update(update_action)
            await self._update_node_status(node_id, NodeStatus.SUCCESS)
            
            # Trigger next nodes
            fresh_node = next((n for n in self.get_nodes() if n.id == node_id), node)
            await self._trigger_next_nodes(fresh_node, [out_item])
            
            # Check if finished just in case
            self._check_if_finished()

    async def _trigger_next_nodes(self, node: NodeData, output_items_override: Optional[List[FlowItem]] = None, active_pins: Optional[Set[str]] = None):
        async with self._state_lock:
            current_nodes = self.get_nodes()
            fresh_node = next((n for n in current_nodes if n.id == node.id), node)
            output_items = output_items_override or []
            
            traversal = FlowGraphTraverser.determine_next_nodes(
                source_node=fresh_node,
                all_nodes=current_nodes,
                all_connections=self.get_connections(),
                output_items=output_items,
                active_from_pin_ids_override=active_pins
            )
            self.update_nodes(traversal.updatedNodes)
            
        for log in traversal.logs:
            self._log(log)

        for nid, payload in traversal.payloadByNextNodeId.items():
            existing = self.runtime_payload_by_node_id.get(nid, FlowPayload())
            self.runtime_payload_by_node_id[nid] = existing.merged_with(payload)

        for next_id in traversal.nextNodeIds:
            next_node = next((n for n in traversal.updatedNodes if n.id == next_id), None)
            if next_node:
                if next_node.status in (NodeStatus.IDLE, NodeStatus.RUNNING) or next_node.type in (NodeType.MERGE, NodeType.OUTPUT_DISPLAY):
                    await self._launch_node_execution(next_node)
                elif next_node.status in (NodeStatus.SUCCESS, NodeStatus.FAILURE):
                    self._log(f"Re-triggering node {next_node.title}")
                    await self._launch_node_execution(next_node)

    def _check_if_finished(self):
        if not self.is_flow_running or self.is_flow_paused:
            return
        
        if self.active_job_count == 0 and not self.pending_execution_queue:
            waiting = any(n.status == NodeStatus.WAITING_FOR_USER for n in self.get_nodes())
            if not waiting:
                self.is_flow_running = False
                self.is_flow_stuck = False
                self._log("Flow Finished Automatically")
                if self._monitor_task:
                    self._monitor_task.cancel()
