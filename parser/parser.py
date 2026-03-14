from __future__ import annotations

from pathlib import Path
from typing import NoReturn, TypedDict

from lexer.token import Token
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
    ParameterNode,
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


class SymbolEntry(TypedDict):
    kind: str
    name: str
    type: str
    scope_depth: int
    initialized: bool
    used: bool
    line: int | None


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0
        self.loop_depth = 0
        self.scope_stack = [{}]
        self.function_return_type = None
        self.procedure_params = {}
        self.function_params = {}
        self.temp_counter = 0
        self.code = []
        self.label_counter = 0
        self.used_variables = set()
        self.declared_variables = set()
        self.uninitialized_vars = set()
        self.ast: ProgramNode | None = None
        self.symbol_entries: list[SymbolEntry] = []

    def current_token(self) -> Token | None:
        return self.tokens[self.current] if self.current < len(self.tokens) else None

    def peek(self) -> Token | None:
        if self.current + 1 < len(self.tokens):
            return self.tokens[self.current + 1]
        return None

    def match(self, expected_type: str) -> Token | None:
        token = self.current_token()
        if token is not None and token.tipo == expected_type:
            print(f"Matched {expected_type}: {token.lexema} na linha {token.linha}")
            self.current += 1
            return token
        if token is not None and token.tipo == "INVALID":
            self.error_sintatico(f"Caractere inválido encontrado: '{token.lexema}'")
        return None

    def error_sintatico(self, message: str) -> NoReturn:
        token = self.current_token()
        context = f"Na linha {token.linha} encontrou '{token.lexema}'" if token else "no final da entrada"
        raise SyntaxError(f"[Erro Sintático] {message} {context}")

    def error_semantico(self, message: str) -> NoReturn:
        token = self.current_token()
        context = f"Na linha {token.linha} encontrou '{token.lexema}'" if token else "no final da entrada"
        raise ValueError(f"[Erro Semântico] {message} {context}")

    def require_current_token(self, message: str) -> Token:
        token = self.current_token()
        if token is None:
            self.error_sintatico(message)
        return token

    def enter_scope(self):
        self.scope_stack.append({})

    def check_unused_variables(self):
        for scope in self.scope_stack:
            for name, info in scope.items():
                if not info["used"] and not name.startswith('_'):
                    print(f"[Aviso Semântico] Variável '{name}' declarada mas não utilizada")

    def check_uninitialized_vars(self):
        for var in self.uninitialized_vars:
            print(f"[Aviso Semântico] Variável '{var}' declarada mas nunca inicializada")

    def exit_scope(self):
        self.check_uninitialized_vars()
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()

    def verify_expression_types(self, left_type, right_type, operator):
        if operator in ["+", "-", "*", "/"]:
            if left_type not in ["int", "float"] or right_type not in ["int", "float"]:
                self.error_semantico(f"Operação '{operator}' requer operandos numéricos, encontrados {left_type} e {right_type}")
            return "float" if "float" in (left_type, right_type) else "int"

        if operator in ["==", "!=", "<", "<=", ">", ">="]:
            if left_type != right_type:
                self.error_semantico(f"Operação de comparação '{operator}' requer operandos do mesmo tipo, encontrados {left_type} e {right_type}")
            return "bool"

        return None

    def add_symbol(self, name, symbol_type, initialized=False, is_param=False):
        if name in self.scope_stack[-1]:
            self.error_semantico(f"Identificador '{name}' já declarado no escopo atual.")
        if name in self.function_params or name in self.procedure_params:
            self.error_semantico(f"Identificador '{name}' já utilizado como função/procedimento.")

        token = self.current_token()
        self.symbol_entries.append(
            {
                "kind": "param" if is_param else "var",
                "name": name,
                "type": symbol_type,
                "scope_depth": len(self.scope_stack) - 1,
                "initialized": initialized or is_param,
                "used": False,
                "line": token.linha if token is not None else None,
            }
        )

        self.scope_stack[-1][name] = {
            "type": symbol_type,
            "initialized": initialized or is_param,
            "used": False,
        }
        self.declared_variables.add(name)
        if not initialized and not is_param:
            self.uninitialized_vars.add(name)

    def get_symbol_type(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                scope[name]["used"] = True
                self.used_variables.add(name)
                for entry in reversed(self.symbol_entries):
                    scope_depth = int(entry["scope_depth"])
                    if entry["name"] == name and scope_depth <= (len(self.scope_stack) - 1):
                        entry["used"] = True
                        break
                if name in self.uninitialized_vars:
                    self.uninitialized_vars.remove(name)
                if not scope[name]["initialized"]:
                    self.error_semantico(f"Variável '{name}' usada antes de ser inicializada.")
                return scope[name]["type"]
        self.error_semantico(f"Identificador '{name}' não declarado.")

    def save_symbol_table(self, file_path: str = "tabela_simbolos.txt") -> Path:
        output = Path(file_path)
        if not output.is_absolute():
            output = Path.cwd() / output

        lines: list[str] = ["=== TABELA DE SIMBOLOS ===", ""]

        lines.append("[SIMBOLOS DECLARADOS]")
        for entry in self.symbol_entries:
            lines.append(
                "- kind={kind}; name={name}; type={type}; scope={scope_depth}; "
                "initialized={initialized}; used={used}; line={line}".format(**entry)
            )

        lines.append("")
        lines.append("[FUNCOES]")
        if self.function_params:
            for function_name, function_info in self.function_params.items():
                param_types = ", ".join(function_info["param_types"])
                lines.append(
                    f"- name={function_name}; return_type={function_info['return_type']}; params=[{param_types}]"
                )
        else:
            lines.append("- (nenhuma)")

        lines.append("")
        lines.append("[PROCEDIMENTOS]")
        if self.procedure_params:
            for procedure_name, param_types in self.procedure_params.items():
                params_text = ", ".join(param_types)
                lines.append(f"- name={procedure_name}; params=[{params_text}]")
        else:
            lines.append("- (nenhum)")

        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output

    def parse(self) -> ProgramNode | None:
        try:
            self.ast = self.programa()
            self.check_unused_variables()
            self.check_uninitialized_vars()

            token = self.current_token()
            if token is not None and token.tipo != "FIM":
                self.error_sintatico("Fim inesperado do parsing")

            return self.ast
        except (SyntaxError, ValueError) as error:
            print(f"\nErro encontrado: {error}")
            self.ast = None
            return None

    def programa(self) -> ProgramNode:
        statements = self.bloco(stop_tokens={"FIM"})
        print("Parsing completo sem erros.\n\n")
        return ProgramNode(statements=statements)

    def bloco(self, stop_tokens: set[str], expected_return_type: str | None = None) -> list[StatementNode]:
        statements: list[StatementNode] = []

        while True:
            token = self.current_token()
            if token is None or token.tipo in stop_tokens:
                return statements

            statement = self.parse_statement(expected_return_type)
            if statement is None:
                self.error_sintatico(f"Comando inválido: {token.lexema}")
            statements.append(statement)

    def parse_statement(self, expected_return_type: str | None = None) -> StatementNode | None:
        statement = self.declaracao_variavel()
        if statement is not None:
            return statement

        statement = self.comando_impressao()
        if statement is not None:
            return statement

        statement = self.comando_condicional(expected_return_type)
        if statement is not None:
            return statement

        statement = self.comando_enquanto(expected_return_type)
        if statement is not None:
            return statement

        statement = self.declaracao_funcao()
        if statement is not None:
            return statement

        statement = self.declaracao_procedimento()
        if statement is not None:
            return statement

        statement = self.desvio_incondicional()
        if statement is not None:
            return statement

        statement = self.chamada_procedimento()
        if statement is not None:
            if not self.match("SEMICOLON"):
                self.error_sintatico("Esperado ';' após a chamada do procedimento.")
            return statement

        if expected_return_type is not None:
            statement = self.comando_retorno(expected_return_type)
            if statement is not None:
                return statement

        func_call = self.chamada_funcao()
        if func_call is not None:
            return_type, call_node = func_call
            if not self.match("SEMICOLON"):
                self.error_sintatico("Esperado ';' após a chamada da função.")
            if return_type != "void":
                print(f"[Aviso Semântico] Resultado da função '{call_node.name}' não utilizado")
            return ExpressionStatementNode(expression=call_node)

        return None

    def declaracao_variavel(self) -> VariableDeclarationNode | AssignmentNode | None:
        tipo = self.especificador_tipo()
        if not tipo:
            token = self.current_token()
            if token is not None and token.tipo == "ID_VAR":
                next_token = self.peek()
                if next_token is not None and next_token.tipo == "ATTR":
                    return self.atribuicao_variavel()
                self.error_semantico(
                    f"Declaração de variável '{token.lexema}' na linha {token.linha} não é antecedida por um especificador de tipo."
                )
            return None

        if tipo == "void":
            self.error_semantico("Não é permitido declarar variáveis do tipo 'void'.")

        identifier = self.match("ID_VAR")
        if identifier is None:
            self.error_sintatico("Esperado identificador de variável.")

        initializer: ExpressionNode | None = None
        initialized = False
        if self.match("ATTR"):
            expr_type, initializer = self.expressao()
            if expr_type != tipo:
                self.error_semantico(f"Atribuição inválida: esperado '{tipo}', encontrado '{expr_type}'.")
            initialized = True

        if not self.match("SEMICOLON"):
            self.error_sintatico("Esperado ';' após a declaração da variável.")

        self.add_symbol(identifier.lexema, tipo, initialized=initialized)
        return VariableDeclarationNode(var_type=tipo, name=identifier.lexema, initializer=initializer)

    def atribuicao_variavel(self) -> AssignmentNode | None:
        token = self.require_current_token("Esperado identificador de variável.")
        var_name = token.lexema

        var_type = None
        for scope in reversed(self.scope_stack):
            if var_name in scope:
                var_type = scope[var_name]["type"]
                break

        if var_type is None:
            self.error_semantico(f"Variável '{var_name}' não declarada.")

        self.match("ID_VAR")
        if not self.match("ATTR"):
            self.error_sintatico("Esperado '=' após o identificador da variável.")

        expr_type, expr_node = self.expressao()
        if expr_type != var_type:
            self.error_semantico(f"Atribuição inválida: esperado '{var_type}', encontrado '{expr_type}'.")

        for scope in reversed(self.scope_stack):
            if var_name in scope:
                scope[var_name]["initialized"] = True
                break

        if var_name in self.uninitialized_vars:
            self.uninitialized_vars.remove(var_name)

        if not self.match("SEMICOLON"):
            self.error_sintatico("Esperado ';' após a atribuição da variável.")

        return AssignmentNode(name=var_name, value=expr_node)

    def especificador_tipo(self) -> str | None:
        if self.match("TYPE_INT"):
            return "int"
        if self.match("TYPE_BOOL"):
            return "bool"
        if self.match("TYPE_FLOAT"):
            return "float"
        if self.match("TYPE_CHAR"):
            return "char"
        if self.match("TYPE_VOID"):
            return "void"
        return None

    def comando_condicional(self, expected_return_type: str | None = None) -> IfNode | None:
        if not self.match("IF"):
            return None

        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' para abrir a condição do 'if'.")

        expr_type, condition = self.expressao()
        if expr_type != "bool":
            self.error_semantico(f"Condição do 'if' deve ser do tipo 'bool', encontrado '{expr_type}'.")

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' para fechar a condição do 'if'.")
        if not self.match("LCBRACK"):
            self.error_sintatico("Esperado '{' para iniciar o bloco do 'if'.")

        then_block = self.bloco(stop_tokens={"RCBRACK"}, expected_return_type=expected_return_type)

        if not self.match("RCBRACK"):
            self.error_sintatico("Esperado '}' para fechar o bloco do 'if'.")

        else_block = self.else_opcional(expected_return_type)
        return IfNode(condition=condition, then_block=then_block, else_block=else_block)

    def else_opcional(self, expected_return_type: str | None = None) -> list[StatementNode] | None:
        if not self.match("ELSE"):
            return None

        if not self.match("LCBRACK"):
            self.error_sintatico("Esperado '{' para abrir o bloco do 'else'.")

        else_block = self.bloco(stop_tokens={"RCBRACK"}, expected_return_type=expected_return_type)
        if not self.match("RCBRACK"):
            self.error_sintatico("Esperado '}' para fechar o bloco do 'else'.")
        return else_block

    def comando_enquanto(self, expected_return_type: str | None = None) -> WhileNode | None:
        if not self.match("WHILE"):
            return None

        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' para abrir a condição do 'while'.")

        expr_type, condition = self.expressao()
        if expr_type != "bool":
            self.error_semantico(f"Condição do 'while' deve ser do tipo 'bool', encontrado '{expr_type}'.")

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' para fechar a condição do 'while'.")
        if not self.match("LCBRACK"):
            self.error_sintatico("Esperado '{' para iniciar o bloco do 'while'.")

        self.loop_depth += 1
        body = self.bloco(stop_tokens={"RCBRACK"}, expected_return_type=expected_return_type)
        self.loop_depth -= 1

        if not self.match("RCBRACK"):
            self.error_sintatico("Esperado '}' para fechar o bloco do 'while'.")
        return WhileNode(condition=condition, body=body)

    def comando_impressao(self) -> PrintNode | None:
        if not self.match("PRINT"):
            return None

        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' após 'print'.")

        expr_type, expression = self.expressao()
        if expr_type not in ["int", "bool", "float", "char"]:
            self.error_semantico(f"Tipo inválido para impressão: '{expr_type}'.")

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' após o argumento de 'print'.")
        if not self.match("SEMICOLON"):
            self.error_sintatico("Esperado ';' após o comando 'print'.")
        return PrintNode(expression=expression)

    def declaracao_funcao(self) -> FunctionDeclarationNode | None:
        if not self.match("FUNC"):
            return None

        return_type = self.especificador_tipo()
        if not return_type:
            self.error_sintatico("Esperado tipo de retorno da função.")

        identifier = self.match("ID_FUNC")
        if identifier is None:
            self.error_sintatico("Esperado identificador da função.")
        func_name = identifier.lexema

        if func_name in self.function_params or func_name in self.procedure_params:
            self.error_semantico(f"Função/procedimento '{func_name}' já declarado.")

        self.function_params[func_name] = {"return_type": return_type, "param_types": []}
        previous_return_type = self.function_return_type
        self.function_return_type = return_type
        self.enter_scope()

        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' para iniciar a lista de parâmetros.")

        params = self.lista_parametros()
        self.function_params[func_name]["param_types"] = [param.param_type for param in params]

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' para fechar a lista de parâmetros.")
        if not self.match("LCBRACK"):
            self.error_sintatico("Esperado '{' para iniciar o corpo da função.")

        body = self.bloco(stop_tokens={"RCBRACK"}, expected_return_type=return_type)

        if return_type != "void" and not self.block_guarantees_return(body):
            self.error_semantico(f"Função '{func_name}' não retorna valor em todos os caminhos.")

        if not self.match("RCBRACK"):
            self.error_sintatico("Esperado '}' para fechar o corpo da função.")

        self.exit_scope()
        self.function_return_type = previous_return_type
        return FunctionDeclarationNode(return_type=return_type, name=func_name, parameters=params, body=body)

    def block_guarantees_return(self, statements: list[StatementNode]) -> bool:
        for statement in statements:
            if self.statement_guarantees_return(statement):
                return True
        return False

    def statement_guarantees_return(self, statement: StatementNode) -> bool:
        if isinstance(statement, ReturnNode):
            return True
        if isinstance(statement, IfNode) and statement.else_block is not None:
            return self.block_guarantees_return(statement.then_block) and self.block_guarantees_return(statement.else_block)
        return False

    def lista_parametros(self) -> list[ParameterNode]:
        params: list[ParameterNode] = []
        token = self.current_token()
        if token is not None and token.tipo == "RBRACK":
            return params

        while True:
            tipo = self.especificador_tipo()
            if not tipo or tipo == "void":
                self.error_sintatico("Esperado tipo do parâmetro (não pode ser void).")

            identifier = self.match("ID_VAR")
            if identifier is None:
                self.error_sintatico("Esperado identificador do parâmetro.")

            self.add_symbol(identifier.lexema, tipo, is_param=True)
            params.append(ParameterNode(param_type=tipo, name=identifier.lexema))

            if self.match("COMMA"):
                continue
            break

        return params

    def declaracao_parametro(self):
        tipo = self.especificador_tipo()
        if not tipo:
            self.error_sintatico("Esperado tipo do parâmetro.")

        if self.match("ID_VAR"):
            param_name = self.tokens[self.current - 1].lexema
            self.add_symbol(param_name, tipo)
            return True
        return False

    def comando_retorno(self, expected_return_type: str) -> ReturnNode | None:
        if not self.match("RETURN"):
            return None

        if expected_return_type == "void":
            self.error_semantico("Função void não pode retornar valor.")

        expr_type, expression = self.expressao()
        if expr_type != expected_return_type:
            self.error_semantico(f"Tipo de retorno inválido: esperado '{expected_return_type}', encontrado '{expr_type}'.")

        if not self.match("SEMICOLON"):
            self.error_sintatico("Esperado ';' após o retorno.")
        return ReturnNode(expression=expression)

    def expressao(self) -> tuple[str, ExpressionNode]:
        return self.expressao_logica()

    def expressao_logica(self) -> tuple[str, ExpressionNode]:
        left_type, left_node = self.expressao_aditiva()
        token = self.current_token()

        if token is not None and token.tipo in ["EQUAL", "NOTEQUAL", "LESS", "LESSEQUAL", "GREAT", "GREATEQUAL"]:
            op_token = token
            self.match(token.tipo)
            right_type, right_node = self.expressao_aditiva()

            if left_type != right_type:
                self.error_semantico(f"Tipos incompatíveis na expressão: '{left_type}' e '{right_type}'.")

            if op_token.tipo in ["LESS", "LESSEQUAL", "GREAT", "GREATEQUAL"]:
                if left_type not in ["int", "float", "char"]:
                    self.error_semantico(f"Operador '{op_token.tipo}' requer operandos do tipo 'int', 'float' ou 'char', encontrado '{left_type}'.")
            elif left_type not in ["int", "bool", "float", "char"]:
                self.error_semantico(f"Operador '{op_token.tipo}' requer operandos compatíveis, encontrado '{left_type}'.")

            op_map = {
                "EQUAL": "==",
                "NOTEQUAL": "!=",
                "LESS": "<",
                "LESSEQUAL": "<=",
                "GREAT": ">",
                "GREATEQUAL": ">=",
            }
            return "bool", BinaryExpressionNode(operator=op_map[op_token.tipo], left=left_node, right=right_node)

        return left_type, left_node

    def expressao_aditiva(self) -> tuple[str, ExpressionNode]:
        left_type, left_node = self.expressao_multiplicativa()
        token = self.current_token()

        while token is not None and token.tipo in ["SUM", "SUB"]:
            op_token = token
            self.match(token.tipo)
            right_type, right_node = self.expressao_multiplicativa()
            if left_type not in ["int", "float"] or right_type not in ["int", "float"]:
                self.error_semantico(
                    f"Operação aritmética requer operandos numéricos ('int' ou 'float'), encontrado '{left_type}' e '{right_type}'."
                )

            op_map = {"SUM": "+", "SUB": "-"}
            left_type = "float" if "float" in (left_type, right_type) else "int"
            left_node = BinaryExpressionNode(operator=op_map[op_token.tipo], left=left_node, right=right_node)
            token = self.current_token()

        return left_type, left_node

    def expressao_multiplicativa(self) -> tuple[str, ExpressionNode]:
        left_type, left_node = self.termo()
        token = self.current_token()

        while token is not None and token.tipo in ["MUL", "DIV"]:
            op_token = token
            self.match(token.tipo)
            right_type, right_node = self.termo()
            if left_type not in ["int", "float"] or right_type not in ["int", "float"]:
                self.error_semantico(
                    f"Operação multiplicativa requer operandos numéricos ('int' ou 'float'), encontrado '{left_type}' e '{right_type}'."
                )

            op_map = {"MUL": "*", "DIV": "/"}
            left_type = "float" if "float" in (left_type, right_type) else "int"
            left_node = BinaryExpressionNode(operator=op_map[op_token.tipo], left=left_node, right=right_node)
            token = self.current_token()

        return left_type, left_node

    def termo(self) -> tuple[str, ExpressionNode]:
        token = self.current_token()
        if token is None:
            self.error_sintatico("Esperado número, variável ou chamada de função, mas a entrada terminou.")

        if token.tipo == "NUMBER":
            self.match("NUMBER")
            return "int", LiteralNode(literal_type="int", value=token.lexema)
        if token.tipo == "FLOAT_NUMBER":
            self.match("FLOAT_NUMBER")
            return "float", LiteralNode(literal_type="float", value=token.lexema)
        if token.tipo == "CHAR_CONST":
            self.match("CHAR_CONST")
            return "char", LiteralNode(literal_type="char", value=token.lexema)
        if token.tipo in ["TRUE", "FALSE"]:
            self.match(token.tipo)
            return "bool", LiteralNode(literal_type="bool", value=token.lexema)
        if token.tipo == "ID_VAR":
            var_name = token.lexema
            var_type = self.get_symbol_type(var_name)
            self.match("ID_VAR")
            return var_type, VariableReferenceNode(name=var_name)
        if token.tipo == "ID_FUNC":
            result = self.chamada_funcao()
            if result is not None:
                return result

        self.error_sintatico(f"Esperado número, variável ou chamada de função, encontrado '{token.lexema}'.")

    def chamada_funcao(self) -> tuple[str, FunctionCallNode] | None:
        identifier = self.match("ID_FUNC")
        if identifier is None:
            return None

        func_name = identifier.lexema
        if func_name not in self.function_params:
            self.error_semantico(f"Função '{func_name}' não declarada")

        func_info = self.function_params[func_name]
        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' após nome da função")

        actual_args = self.lista_argumentos()
        expected_params = func_info["param_types"]

        if len(actual_args) != len(expected_params):
            self.error_semantico(
                f"Número incorreto de argumentos para '{func_name}'. Esperado {len(expected_params)}, encontrado {len(actual_args)}"
            )

        argument_nodes: list[ExpressionNode] = []
        for index, ((arg_type, arg_node), expected_type) in enumerate(zip(actual_args, expected_params), start=1):
            if arg_type != expected_type:
                self.error_semantico(
                    f"Tipo incorreto para argumento {index} em '{func_name}'. Esperado {expected_type}, encontrado {arg_type}"
                )
            argument_nodes.append(arg_node)

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' após argumentos da função")

        return func_info["return_type"], FunctionCallNode(name=func_name, arguments=argument_nodes)

    def lista_argumentos(self) -> list[tuple[str, ExpressionNode]]:
        token = self.current_token()
        if token is not None and token.tipo == "RBRACK":
            return []

        args: list[tuple[str, ExpressionNode]] = []
        expr_type, expr_node = self.expressao()
        args.append((expr_type, expr_node))
        while self.match("COMMA"):
            expr_type, expr_node = self.expressao()
            args.append((expr_type, expr_node))
        return args

    def declaracao_procedimento(self) -> ProcedureDeclarationNode | None:
        if not self.match("PROC"):
            return None

        identifier = self.match("ID_PROC")
        if identifier is None:
            self.error_sintatico("Esperado identificador do procedimento.")
        proc_name = identifier.lexema

        if proc_name in self.procedure_params or proc_name in self.function_params:
            self.error_semantico(f"Função/procedimento '{proc_name}' já declarado.")

        self.enter_scope()
        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' para iniciar a lista de parâmetros.")

        params = self.lista_parametros()
        self.procedure_params[proc_name] = [param.param_type for param in params]

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' para fechar a lista de parâmetros.")
        if not self.match("LCBRACK"):
            self.error_sintatico("Esperado '{' para iniciar o corpo do procedimento.")

        body = self.bloco(stop_tokens={"RCBRACK"})

        if not self.match("RCBRACK"):
            self.error_sintatico("Esperado '}' para fechar o corpo do procedimento.")

        self.exit_scope()
        return ProcedureDeclarationNode(name=proc_name, parameters=params, body=body)

    def chamada_procedimento(self) -> ProcedureCallNode | None:
        identifier = self.match("ID_PROC")
        if identifier is None:
            return None

        proc_name = identifier.lexema
        if not self.match("LBRACK"):
            self.error_sintatico("Esperado '(' para iniciar os argumentos do procedimento.")

        expected_params = self.get_procedure_params(proc_name)
        actual_args = self.lista_argumentos()
        if len(actual_args) != len(expected_params):
            self.error_semantico(
                f"Número incorreto de argumentos para o procedimento '{proc_name}'. Esperado {len(expected_params)}, encontrado {len(actual_args)}."
            )

        argument_nodes: list[ExpressionNode] = []
        for index, ((arg_type, arg_node), param_type) in enumerate(zip(actual_args, expected_params), start=1):
            if arg_type != param_type:
                self.error_semantico(
                    f"Tipo incorreto para o argumento {index} no procedimento '{proc_name}'. Esperado '{param_type}', encontrado '{arg_type}'."
                )
            argument_nodes.append(arg_node)

        if not self.match("RBRACK"):
            self.error_sintatico("Esperado ')' para fechar os argumentos do procedimento.")
        return ProcedureCallNode(name=proc_name, arguments=argument_nodes)

    def desvio_incondicional(self) -> BreakNode | ContinueNode | None:
        if self.match("BREAK"):
            if self.loop_depth == 0:
                self.error_sintatico("'break' e 'continue' só podem ser usados dentro de loops.")
            if not self.match("SEMICOLON"):
                self.error_sintatico("Esperado ';' após 'break' ou 'continue'.")
            return BreakNode()

        if self.match("CONTINUE"):
            if self.loop_depth == 0:
                self.error_sintatico("'break' e 'continue' só podem ser usados dentro de loops.")
            if not self.match("SEMICOLON"):
                self.error_sintatico("Esperado ';' após 'break' ou 'continue'.")
            return ContinueNode()

        return None

    def get_procedure_params(self, proc_name):
        if proc_name in self.procedure_params:
            return self.procedure_params[proc_name]
        self.error_semantico(f"Procedimento '{proc_name}' não declarado.")

    def get_function_params(self, func_name):
        if func_name in self.function_params:
            return self.function_params[func_name]
        self.error_semantico(f"Função '{func_name}' não declarada.")
