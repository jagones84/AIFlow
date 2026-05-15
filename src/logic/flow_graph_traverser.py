from typing import List, Dict, Set, Optional, Any, Tuple
from pydantic import BaseModel
from src.models.node_models import NodeData, Connection, FlowItem, FlowPayload, NodeType, RouterMode
from src.logic.expression_evaluator import ExpressionEvaluator

class TraversalResult(BaseModel):
    nextNodeIds: List[str]
    updatedNodes: List[NodeData]
    logs: List[str]
    payloadByNextNodeId: Dict[str, FlowPayload]
    skippedNodeIds: List[str] = []

class FlowGraphTraverser:
    
    @staticmethod
    def _item_text(item: FlowItem) -> str:
        text = item.json_data.get("text")
        if text and str(text).strip():
            return str(text)
        import json
        return json.dumps(item.json_data)

    @staticmethod
    def _parse_boolean_like(value: str) -> Optional[bool]:
        v = str(value).strip().lower()
        if v in ["true", "yes", "1"]:
            return True
        if v in ["false", "no", "0"]:
            return False
        return None

    @staticmethod
    def _evaluate_condition(
        condition_raw: str,
        source_node: NodeData,
        all_nodes: List[NodeData],
        item: FlowItem,
        text: str
    ) -> Optional[bool]:
        condition = condition_raw.strip()
        evaluator = ExpressionEvaluator([item], all_nodes, {}, {})

        if condition.lower().startswith("expr:"):
            expr_body = condition[5:].strip()
            resolved = evaluator.evaluate(expr_body).strip()

            op = None
            if "!=" in resolved:
                op = "!="
            elif "==" in resolved:
                op = "=="

            if op:
                parts = resolved.split(op, 1)
                left_raw = parts[0].strip()
                right_raw = parts[1].strip().strip('"').strip("'")

                left_value = evaluator.evaluate(left_raw).strip() if "{{" in left_raw else str(evaluator.evaluate(left_raw) or left_raw).strip()
                right_value = evaluator.evaluate(right_raw).strip() if "{{" in right_raw else right_raw

                try:
                    left_num = float(left_value)
                    right_num = float(right_value)
                    eq = (left_num == right_num)
                except ValueError:
                    eq = (left_value.lower() == right_value.lower())

                return eq if op == "==" else not eq

            bool_val = FlowGraphTraverser._parse_boolean_like(resolved)
            if bool_val is not None:
                return bool_val

            direct = str(evaluator.evaluate(expr_body) or "")
            return FlowGraphTraverser._parse_boolean_like(direct)

        if condition.lower().startswith("json:"):
            json_expr = condition[5:].strip()
            resolved = evaluator.evaluate(json_expr)
            return FlowGraphTraverser._match_json_condition(item, resolved)

        if condition.lower().startswith("contains:"):
            needle = evaluator.evaluate(condition[9:].strip())
            return needle.lower() in text.lower()

        if condition.lower().startswith("not_contains:"):
            needle = evaluator.evaluate(condition[13:].strip())
            return needle.lower() not in text.lower()

        if condition.lower().startswith("exact:"):
            expected = evaluator.evaluate(condition[6:].strip())
            return text.strip().lower() == expected.strip().lower()

        if "{{" in condition and "}}" in condition:
            resolved = evaluator.evaluate(condition)
            bool_val = FlowGraphTraverser._parse_boolean_like(resolved)
            if bool_val is not None:
                return bool_val
            return resolved.lower() in text.lower()

        return None

    @staticmethod
    def _match_json_condition(item: FlowItem, expr: str) -> bool:
        trimmed = expr.strip()
        op = None
        if "!=" in trimmed:
            op = "!="
        elif "==" in trimmed:
            op = "=="
        
        if not op:
            return False

        parts = trimmed.split(op, 1)
        left = parts[0].strip()
        right_raw = parts[1].strip().strip('"').strip("'")
        
        value = ExpressionEvaluator.get_json_path_value(item.json_data, left)
        value_string = str(value) if value is not None else ""
        
        if op == "==":
            return value_string.lower() == right_raw.lower()
        else:
            return value_string.lower() != right_raw.lower()

    @staticmethod
    def determine_next_nodes(
        source_node: NodeData,
        all_nodes: List[NodeData],
        all_connections: List[Connection],
        output_items: List[FlowItem],
        active_from_pin_ids_override: Optional[Set[str]] = None
    ) -> TraversalResult:
        logs = []
        outgoing = [c for c in all_connections if c.fromNodeId == source_node.id]
        
        if not outgoing:
            return TraversalResult(nextNodeIds=[], updatedNodes=all_nodes, logs=logs, payloadByNextNodeId={}, skippedNodeIds=[])

        payload_by_next_node_id: Dict[str, Dict[str, List[FlowItem]]] = {}

        def add_payload(next_node_id: str, to_pin_id: str, items: List[FlowItem]):
            if not items:
                return
            if next_node_id not in payload_by_next_node_id:
                payload_by_next_node_id[next_node_id] = {}
            if to_pin_id not in payload_by_next_node_id[next_node_id]:
                payload_by_next_node_id[next_node_id][to_pin_id] = []
            payload_by_next_node_id[next_node_id][to_pin_id].extend(items)

        next_node_ids = []

        if active_from_pin_ids_override is not None:
            active_connections = [c for c in outgoing if c.fromPinId in active_from_pin_ids_override]
            for c in active_connections:
                add_payload(c.toNodeId, c.toPinId, output_items)
            next_node_ids = list({c.toNodeId for c in active_connections})
        else:
            if source_node.type == NodeType.SWITCH:
                output_decision = str(source_node.lastOutput or "").strip()
                forced_route_pin = next((p for p in source_node.outputs if p.name.lower() == output_decision.lower()), None)
                
                if forced_route_pin:
                    for c in [conn for conn in outgoing if conn.fromPinId == forced_route_pin.id]:
                        add_payload(c.toNodeId, c.toPinId, output_items)
                    logs.append(f"Switch '{source_node.title}' routing via '{output_decision}' (Execution Result)")
                else:
                    for item in output_items:
                        text = FlowGraphTraverser._item_text(item)
                        route_name = None
                        for route in source_node.switchRoutes:
                            cond = route.condition
                            if cond.lower() == "always":
                                route_name = route.name
                                break
                            
                            is_match = FlowGraphTraverser._evaluate_condition(cond, source_node, all_nodes, item, text)
                            if is_match is None:
                                if cond.lower().startswith("contains:"):
                                    is_match = cond[9:].strip().lower() in text.lower()
                                elif cond.lower().startswith("exact:"):
                                    is_match = text.strip().lower() == cond[6:].strip().lower()
                                elif cond.lower().startswith("json:"):
                                    is_match = FlowGraphTraverser._match_json_condition(item, cond[5:].strip())
                                else:
                                    is_match = cond.lower() in text.lower()
                            
                            if is_match:
                                route_name = route.name
                                break
                        
                        if route_name:
                            pin = next((p for p in source_node.outputs if p.name == route_name), None)
                            if pin:
                                for c in [conn for conn in outgoing if conn.fromPinId == pin.id]:
                                    add_payload(c.toNodeId, c.toPinId, [item])
                
                next_node_ids = list(payload_by_next_node_id.keys())

            elif source_node.type == NodeType.ROUTER:
                true_pin = next((p for p in source_node.outputs if "true" in p.name.lower() or "yes" in p.name.lower()), None)
                false_pin = next((p for p in source_node.outputs if "false" in p.name.lower() or "no" in p.name.lower()), None)
                
                # Fallback if no named pins found: first is True, second is False
                if not true_pin and len(source_node.outputs) > 0:
                    true_pin = source_node.outputs[0]
                if not false_pin and len(source_node.outputs) > 1:
                    false_pin = source_node.outputs[1]

                output_decision = str(source_node.lastOutput or "").strip().upper()
                raw_rule = str(source_node.ruleCondition or "").strip()
                
                should_trust_execution = not (source_node.routerMode == RouterMode.SIMPLE_RULE and 
                                              (raw_rule.lower().startswith("expr:") or "{{" in raw_rule))

                if should_trust_execution and ("TRUE" in output_decision or "YES" in output_decision):
                    if true_pin:
                        for c in [conn for conn in outgoing if conn.fromPinId == true_pin.id]:
                            add_payload(c.toNodeId, c.toPinId, output_items)
                    logs.append(f"Router '{source_node.title}' routed TRUE (Execution Result)")
                elif should_trust_execution and ("FALSE" in output_decision or "NO" in output_decision):
                    if false_pin:
                        for c in [conn for conn in outgoing if conn.fromPinId == false_pin.id]:
                            add_payload(c.toNodeId, c.toPinId, output_items)
                    logs.append(f"Router '{source_node.title}' routed FALSE (Execution Result)")
                elif source_node.routerMode == RouterMode.SIMPLE_RULE and source_node.ruleCondition:
                    cond = source_node.ruleCondition
                    for item in output_items:
                        text = FlowGraphTraverser._item_text(item)
                        is_true = FlowGraphTraverser._evaluate_condition(cond, source_node, all_nodes, item, text)
                        if is_true is None:
                            if cond.lower().startswith("contains:"):
                                is_true = cond[9:].strip().lower() in text.lower()
                            elif cond.lower().startswith("not_contains:"):
                                is_true = cond[13:].strip().lower() not in text.lower()
                            elif cond.lower().startswith("json:"):
                                is_true = FlowGraphTraverser._match_json_condition(item, cond[5:].strip())
                            else:
                                is_true = cond.lower() in text.lower()
                        
                        pin = true_pin if is_true else false_pin
                        if pin:
                            for c in [conn for conn in outgoing if conn.fromPinId == pin.id]:
                                add_payload(c.toNodeId, c.toPinId, [item])
                    logs.append(f"Router '{source_node.title}' routed per-item (Simple Rule)")
                else:
                    for c in outgoing:
                        add_payload(c.toNodeId, c.toPinId, output_items)
                
                next_node_ids = list(payload_by_next_node_id.keys())
            
            else:
                for c in outgoing:
                    add_payload(c.toNodeId, c.toPinId, output_items)
                next_node_ids = list(payload_by_next_node_id.keys())

        if not next_node_ids:
            logs.append(f"Node '{source_node.title}' finished but no active next nodes found.")

        def preview(source_title: str, items: List[FlowItem]) -> str:
            count = len(items)
            first_text = FlowGraphTraverser._item_text(items[0]).strip() if items else ""
            snippet = first_text[:120] + "…" if len(first_text) > 120 else first_text
            return f"[{source_title}] {count} item(s)" if not snippet else f"[{source_title}] {count} item(s): {snippet}"

        new_nodes = []
        for n in all_nodes:
            incoming_by_pin = payload_by_next_node_id.get(n.id)
            if incoming_by_pin:
                incoming_items = [item for sublist in incoming_by_pin.values() for item in sublist]
                n_copy = n.model_copy(deep=True)
                n_copy.lastInput = preview(source_node.title, incoming_items)
                new_nodes.append(n_copy)
            else:
                new_nodes.append(n)

        payload_map = {}
        for nid, by_pin in payload_by_next_node_id.items():
            payload_map[nid] = FlowPayload(itemsByPinId={k: list(v) for k, v in by_pin.items()})

        skipped_node_ids = list({c.toNodeId for c in outgoing if c.toNodeId not in next_node_ids})

        return TraversalResult(
            nextNodeIds=next_node_ids,
            updatedNodes=new_nodes,
            logs=logs,
            payloadByNextNodeId=payload_map,
            skippedNodeIds=skipped_node_ids
        )
