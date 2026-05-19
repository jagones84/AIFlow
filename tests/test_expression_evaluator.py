from src.logic.expression_evaluator import ExpressionEvaluator
from src.models.node_models import FlowItem, FlowPayload, NodeData, NodeType


def test_expression_evaluator_json_and_literals():
    node = NodeData(title="n", type=NodeType.SET)
    item = FlowItem(json={"a": {"b": [10, 20]}, "count": 42})
    ev = ExpressionEvaluator([item], [node], {node.id: FlowPayload.from_items([item])}, {"x": "y"})

    assert ev.evaluate("{{ $json.count }}") == "42"
    assert ev.evaluate("{{ $json.a.b[1] }}") == "20"
    assert ev.evaluate("hello {{ $var.x }}") == "hello y"
