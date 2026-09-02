from pathlib import Path

from parser.ast_nodes import (
    AssignmentNode,
    BinaryExpressionNode,
    BreakNode,
    ContinueNode,
    ExpressionNode,
    ExpressionStatementNode,
    FunctionCallNode,
    FunctionDeclarationNode,
    IfNode,
    LiteralNode,
    PrintNode,
    ProcedureCallNode,
    ProcedureDeclarationNode,
    ProgramNode,
    ReturnNode,
    StatementNode,
    VariableDeclarationNode,
    VariableReferenceNode,
    WhileNode,
)


class ThreeAddressGenerator:
    def __init__(self):
        self.temp_counter = 0
        self.label_counter = 0
        self.code: list[str] = []
        self.loop_stack: list[tuple[str, str]] = []

    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self) -> str:
        self.label_counter += 1
        return f"L{self.label_counter}"

    def emit(self, instruction: str, indent: int = 0) -> None:
        if instruction.strip().startswith("//") and self.code and self.code[-1].strip().startswith("//"):
            return
        self.code.append(f"{'    ' * indent}{instruction}")

    def get_formatted_code(self) -> str:
        return "\n".join(f"{index:4d}: {instruction}" for index, instruction in enumerate(self.code, 1))

    def generate(self, program: ProgramNode) -> str:
        self.temp_counter = 0
        self.label_counter = 0
        self.code = []
        self.loop_stack = []
        self.gen_block(program.statements, indent=0)
        return self.get_formatted_code()

    def save(self, program: ProgramNode, file_path: str = "3aderecos.txt") -> Path:
        text = self.generate(program)
        output = Path(file_path)
        if not output.is_absolute():
            output = Path.cwd() / output
        output.write_text(text + "\n", encoding="utf-8")
        return output

    def gen_block(self, statements: list[StatementNode], indent: int) -> None:
        for statement in statements:
            self.gen_statement(statement, indent)

    def gen_statement(self, statement: StatementNode, indent: int) -> None:
        if isinstance(statement, VariableDeclarationNode):
            if statement.initializer is not None:
                value = self.gen_expression(statement.initializer, indent)
                self.emit(f"{statement.name} = {value}", indent)
            return

        if isinstance(statement, AssignmentNode):
            value = self.gen_expression(statement.value, indent)
            self.emit(f"{statement.name} = {value}", indent)
            return

        if isinstance(statement, PrintNode):
            value = self.gen_expression(statement.expression, indent)
            self.emit(f"print {value}", indent)
            return

        if isinstance(statement, IfNode):
            self.gen_if(statement, indent)
            return

        if isinstance(statement, WhileNode):
            self.gen_while(statement, indent)
            return

        if isinstance(statement, FunctionDeclarationNode):
            self.emit(f"// func {statement.name}", indent)
            self.gen_block(statement.body, indent + 1)
            return

        if isinstance(statement, ProcedureDeclarationNode):
            self.emit(f"// proc {statement.name}", indent)
            self.gen_block(statement.body, indent + 1)
            return

        if isinstance(statement, ProcedureCallNode):
            self.emit(self._call_instruction(statement.name, statement.arguments, indent), indent)
            return

        if isinstance(statement, ReturnNode):
            value = self.gen_expression(statement.expression, indent)
            self.emit(f"return {value}", indent)
            return

        if isinstance(statement, BreakNode):
            _, end_label = self._current_loop()
            self.emit(f"goto {end_label}", indent)
            return

        if isinstance(statement, ContinueNode):
            start_label, _ = self._current_loop()
            self.emit(f"goto {start_label}", indent)
            return

        if isinstance(statement, ExpressionStatementNode):
            self.gen_expression(statement.expression, indent)
            return

    def gen_if(self, statement: IfNode, indent: int) -> None:
        condition = self.gen_expression(statement.condition, indent)
        false_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"ifFalse {condition} goto {false_label}", indent)
        self.emit("// Bloco do if", indent)
        self.gen_block(statement.then_block, indent + 1)
        self.emit(f"goto {end_label}", indent)
        self.emit(f"{false_label}:", indent)

        if statement.else_block is not None:
            self.emit("// Bloco do else", indent)
            self.gen_block(statement.else_block, indent + 1)

        self.emit(f"{end_label}:", indent)

    def gen_while(self, statement: WhileNode, indent: int) -> None:
        start_label = self.new_label()
        loop_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{start_label}:", indent)
        condition = self.gen_expression(statement.condition, indent)
        self.emit(f"ifFalse {condition} goto {end_label}", indent)
        self.emit(f"{loop_label}:", indent)
        self.emit("// Bloco do while", indent)

        self.loop_stack.append((start_label, end_label))
        self.gen_block(statement.body, indent + 1)
        self.loop_stack.pop()

        self.emit(f"goto {start_label}", indent)
        self.emit(f"{end_label}:", indent)

    def gen_expression(self, expression: ExpressionNode, indent: int) -> str:
        if isinstance(expression, LiteralNode):
            temp = self.new_temp()
            self.emit(f"{temp} = {self._literal_text(expression)}", indent)
            return temp

        if isinstance(expression, VariableReferenceNode):
            return expression.name

        if isinstance(expression, BinaryExpressionNode):
            left = self.gen_expression(expression.left, indent)
            right = self.gen_expression(expression.right, indent)
            temp = self.new_temp()
            self.emit(f"{temp} = {left} {expression.operator} {right}", indent)
            return temp

        if isinstance(expression, FunctionCallNode):
            temp = self.new_temp()
            self.emit(f"{temp} = {self._call_instruction(expression.name, expression.arguments, indent)}", indent)
            return temp

        raise TypeError(f"Expressão não suportada na geração de código: {type(expression).__name__}")

    def _call_instruction(self, name: str, arguments: list[ExpressionNode], indent: int) -> str:
        args = [self.gen_expression(argument, indent) for argument in arguments]
        if args:
            return f"call {name}, {', '.join(args)}"
        return f"call {name}"

    def _literal_text(self, literal: LiteralNode) -> str:
        if literal.literal_type == "char":
            return f"'{literal.value}'"
        return literal.value

    def _current_loop(self) -> tuple[str, str]:
        if not self.loop_stack:
            raise ValueError("break/continue sem laço correspondente na geração de código")
        return self.loop_stack[-1]
