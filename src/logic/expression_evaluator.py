import json
import re
from typing import List, Dict, Any, Optional
from src.models.node_models import NodeData, FlowItem, FlowPayload

class ExpressionEvaluator:
    def __init__(self, items: List[FlowItem], all_nodes: List[NodeData], runtime_payloads: Dict[str, FlowPayload], variables: Dict[str, str]):
        self.items = items
        self.all_nodes = all_nodes
        self.runtime_payloads = runtime_payloads
        self.variables = variables

    def evaluate(self, expr_raw: Optional[str]) -> str:
        if not expr_raw:
            return ""
        
        raw = str(expr_raw)
        if "{{" not in raw or "}}" not in raw:
            return raw

        out = []
        idx = 0
        while idx < len(raw):
            start = raw.find("{{", idx)
            if start < 0:
                out.append(raw[idx:])
                break
            out.append(raw[idx:start])
            end = raw.find("}}", start + 2)
            if end < 0:
                out.append(raw[start:])
                break

            expr = raw[start + 2:end].strip()
            # For simplicity, we just use the first item to evaluate templates
            item = self.items[0] if self.items else None
            value = self._evaluate_expression(expr, item)
            out.append(str(value) if value is not None else "")
            idx = end + 2

        return "".join(out)

    def _evaluate_expression(self, expr: str, item: Optional[FlowItem]) -> Any:
        expr = expr.strip()

        # Handle $node["Node Name"].context["key"]
        if expr.lower().startswith("$node["):
            node_name = self._extract_bracket_string(expr, "$node[")
            if not node_name:
                return None
            
            node = next((n for n in self.all_nodes if n.title.lower() == node_name.lower() or n.id == node_name), None)
            if not node:
                return None

            after_node = expr[expr.find("]") + 1:]
            if not after_node.startswith(".context"):
                return None
            
            after_context = after_node[len(".context"):]
            ctx_key = ""
            if after_context.startswith("["):
                ctx_key = self._extract_bracket_string(after_context, "")
            elif after_context.startswith("."):
                ctx_key = re.match(r"^\.([a-zA-Z0-9_]+)", after_context)
                if ctx_key:
                    ctx_key = ctx_key.group(1)
            
            if not ctx_key:
                return None
            
            return node.context.get(ctx_key)

        # Handle $json.path
        if expr.lower().startswith("$json"):
            json_path = expr[len("$json"):].strip().lstrip(".")
            return self.get_json_path_value(item.json_data if item else None, json_path)

        # Handle variables
        if expr.lower().startswith("$var"):
            var_path = expr[len("$var"):].strip().lstrip(".")
            return self.variables.get(var_path)

        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
            
        return expr

    def _extract_bracket_string(self, raw: str, prefix: str) -> Optional[str]:
        start = raw.find('[') if not prefix else raw.find(prefix) + len(prefix)
        if start < 0:
            return None
        
        open_idx = raw.find('[', 0 if not prefix else start - len(prefix))
        if open_idx < 0:
            return None
            
        close_idx = raw.find(']', open_idx + 1)
        if close_idx < 0:
            return None
            
        inside = raw[open_idx + 1:close_idx].strip().strip('"').strip("'")
        return inside

    @staticmethod
    def get_json_path_value(root: Any, raw_path: str) -> Any:
        path = raw_path.strip().lstrip("$").lstrip(".")
        if not path:
            return root
            
        current = root
        segments = [s for s in path.split('.') if s.strip()]

        for segment in segments:
            name = segment.split('[')[0]
            indices = ExpressionEvaluator._parse_indices(segment[len(name):])

            if name:
                if isinstance(current, dict):
                    current = current.get(name)
                else:
                    return None

            for idx in indices:
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None

        return current

    @staticmethod
    def _parse_indices(rest: str) -> List[int]:
        indices = []
        r = rest
        while r.startswith("["):
            end = r.find(']')
            if end <= 1:
                break
            idx_str = r[1:end]
            if idx_str.isdigit():
                indices.append(int(idx_str))
            r = r[end + 1:]
        return indices
