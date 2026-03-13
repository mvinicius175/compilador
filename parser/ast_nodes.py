from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any


class AstNode:
    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ParameterNode(AstNode):
    param_type: str
    name: str


@dataclass(slots=True)
class ProgramNode(AstNode):
    statements: list[StatementNode]


@dataclass(slots=True)
class VariableDeclarationNode(AstNode):
    var_type: str
    name: str
    initializer: ExpressionNode | None


@dataclass(slots=True)
class AssignmentNode(AstNode):
    name: str
    value: ExpressionNode


@dataclass(slots=True)
class PrintNode(AstNode):
    expression: ExpressionNode


@dataclass(slots=True)
class IfNode(AstNode):
    condition: ExpressionNode
    then_block: list[StatementNode]
    else_block: list[StatementNode] | None


@dataclass(slots=True)
class WhileNode(AstNode):
    condition: ExpressionNode
    body: list[StatementNode]


@dataclass(slots=True)
class FunctionDeclarationNode(AstNode):
    return_type: str
    name: str
    parameters: list[ParameterNode]
    body: list[StatementNode]


@dataclass(slots=True)
class ProcedureDeclarationNode(AstNode):
    name: str
    parameters: list[ParameterNode]
    body: list[StatementNode]


@dataclass(slots=True)
class ProcedureCallNode(AstNode):
    name: str
    arguments: list[ExpressionNode]


@dataclass(slots=True)
class ReturnNode(AstNode):
    expression: ExpressionNode


@dataclass(slots=True)
class BreakNode(AstNode):
    pass


@dataclass(slots=True)
class ContinueNode(AstNode):
    pass


@dataclass(slots=True)
class ExpressionStatementNode(AstNode):
    expression: ExpressionNode


@dataclass(slots=True)
class LiteralNode(AstNode):
    literal_type: str
    value: str


@dataclass(slots=True)
class VariableReferenceNode(AstNode):
    name: str


@dataclass(slots=True)
class BinaryExpressionNode(AstNode):
    operator: str
    left: ExpressionNode
    right: ExpressionNode


@dataclass(slots=True)
class FunctionCallNode(AstNode):
    name: str
    arguments: list[ExpressionNode]


ExpressionNode = (
    LiteralNode
    | VariableReferenceNode
    | BinaryExpressionNode
    | FunctionCallNode
)

StatementNode = (
    VariableDeclarationNode
    | AssignmentNode
    | PrintNode
    | IfNode
    | WhileNode
    | FunctionDeclarationNode
    | ProcedureDeclarationNode
    | ProcedureCallNode
    | ReturnNode
    | BreakNode
    | ContinueNode
    | ExpressionStatementNode
)


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value
