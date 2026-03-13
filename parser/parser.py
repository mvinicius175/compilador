from typing import NoReturn

from lexer.token import Token


class Parser:
    def __init__(self, tokens):
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

    def current_token(self) -> Token | None:
        return self.tokens[self.current] if self.current < len(self.tokens) else None

    def peek(self) -> Token | None:
        # Retorna o próximo token sem avançar o índice.
        if self.current + 1 < len(self.tokens):
            return self.tokens[self.current + 1]
        return None

    def match(self, expected_type) -> Token | None:
        # Verifica se o token atual corresponde ao tipo esperado.
        token = self.current_token()
        if token and token.tipo == expected_type:
            print(f"Matched {expected_type}: {token.lexema} na linha {token.linha}")
            self.current += 1
            return token
        elif token and token.tipo == "INVALID":
            self.error_sintatico(f"Caractere inválido encontrado: '{token.lexema}'")
        return None

    def error_sintatico(self, message) -> NoReturn:
        # Gera um erro de sintaxe com contexto.
        token = self.current_token()
        context = f"Na linha {token.linha} encontrou '{token.lexema}'" if token else "no final da entrada"
        raise SyntaxError(f"[Erro Sintático] {message} {context}")

    def error_semantico(self, message) -> NoReturn:
        # Gera um erro semântico com contexto.
        token = self.current_token()
        context = f"Na linha {token.linha} encontrou '{token.lexema}'" if token else "no final da entrada"
        raise ValueError(f"[Erro Semântico] {message} {context}")

    def require_current_token(self, message: str) -> Token:
        token = self.current_token()
        if token is None:
            self.error_sintatico(message)
        return token

    # ========================
    # Analisador Semântico
    # (tabela de símbolos, escopos, tipos)
    # ========================

    def enter_scope(self):
        """Entra em um novo escopo."""
        self.scope_stack.append({})

    def check_unused_variables(self):
        """Verifica se há variáveis declaradas mas não utilizadas."""
        for scope in self.scope_stack:
            for name, info in scope.items():
                if not info["used"] and not name.startswith('_'):
                    print(f"[Aviso Semântico] Variável '{name}' declarada mas não utilizada")

    def check_uninitialized_vars(self):
        """Verifica variáveis declaradas mas não inicializadas ao sair do escopo."""
        for var in self.uninitialized_vars:
            print(f"[Aviso Semântico] Variável '{var}' declarada mas nunca inicializada")

    def exit_scope(self):
        """Sai do escopo atual com verificações adicionais."""
        self.check_uninitialized_vars()
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()

    def verify_expression_types(self, left_type, right_type, operator):
        """Verifica compatibilidade de tipos em operações."""
        if operator in ["+", "-", "*", "/"]:
            if left_type not in ["int", "float"] or right_type not in ["int", "float"]:
                self.error_semantico(f"Operação '{operator}' requer operandos numéricos, encontrados {left_type} e {right_type}")
            return "float" if "float" in (left_type, right_type) else "int"

        elif operator in ["==", "!=", "<", "<=", ">", ">="]:
            if left_type != right_type:
                self.error_semantico(f"Operação de comparação '{operator}' requer operandos do mesmo tipo, encontrados {left_type} e {right_type}")
            return "bool"

        return None

    def check_return_paths(self, function_name, return_type):
        """Verifica se todos os caminhos da função retornam um valor."""
        if return_type != "void" and not self.scope_stack[-1].get("_has_return", False):
            self.error_semantico(f"Função '{function_name}' não retorna valor em todos os caminhos")

    def verify_function_return(self, function_name, expr_type):
        """Verifica se o tipo de retorno corresponde ao declarado."""
        expected_type = self.function_params[function_name]["return_type"]
        if expr_type != expected_type:
            self.error_semantico(f"Tipo de retorno incorreto em '{function_name}'. Esperado {expected_type}, encontrado {expr_type}")

    def verify_parameters(self, name, expected_types, actual_args, is_function=True):
        """Verifica os parâmetros de funções/procedimentos."""
        if len(expected_types) != len(actual_args):
            kind = "função" if is_function else "procedimento"
            self.error_semantico(f"Número incorreto de argumentos para {kind} '{name}'. Esperado {len(expected_types)}, encontrado {len(actual_args)}")

        for i, (expected, (actual_type, _)) in enumerate(zip(expected_types, actual_args)):
            if expected != actual_type:
                self.error_semantico(f"Tipo incorreto para argumento {i+1} em '{name}'. Esperado {expected}, encontrado {actual_type}")

    def add_symbol(self, name, symbol_type, initialized=False, is_param=False):
        """Adiciona um símbolo ao escopo atual com verificação de declaração duplicada."""
        if name in self.scope_stack[-1]:
            self.error_semantico(f"Identificador '{name}' já declarado no escopo atual.")
        # Impede colisão entre variáveis e funções/procedimentos (sem sobrecarga)
        if name in self.function_params or name in self.procedure_params:
            self.error_semantico(f"Identificador '{name}' já utilizado como função/procedimento.")

        self.scope_stack[-1][name] = {
            "type": symbol_type,
            "initialized": initialized or is_param,
            "used": False
        }
        self.declared_variables.add(name)
        if not initialized and not is_param:
            self.uninitialized_vars.add(name)

    def get_symbol_type(self, name):
        """Retorna o tipo de um símbolo com verificações adicionais."""
        for scope in reversed(self.scope_stack):
            if name in scope:
                scope[name]["used"] = True
                self.used_variables.add(name)

                if name in self.uninitialized_vars:
                    self.uninitialized_vars.remove(name)

                if not scope[name]["initialized"]:
                    self.error_semantico(f"Variável '{name}' usada antes de ser inicializada.")
                return scope[name]["type"]
        self.error_semantico(f"Identificador '{name}' não declarado.")


    def parse(self):
        """Executa análise sintática e semântica baseada em tipos e tabela de símbolos."""
        try:
            self.programa()

            # Verificações semânticas finais
            self.check_unused_variables()
            self.check_uninitialized_vars()

            token = self.current_token()
            if token is not None and token.tipo != "FIM":
                self.error_sintatico("Fim inesperado do parsing")

            return True

        except (SyntaxError, ValueError) as e:
            print(f"\nErro encontrado: {e}")
            return False

    # ========================
    # Analisador Sintático
    # (parsing da gramática BNF)
    # ========================

    def programa(self):
        """Processa o programa principal."""
        if self.bloco():
            print("Parsing completo sem erros.\n\n")
        else:
            self.error_sintatico("Erro ao interpretar o programa.")
        return True

    def bloco(self):
        """Processa um bloco de código."""
        while True:
            token = self.current_token()
            if token is None:
                break

            if token.tipo in ["RCBRACK", "FIM"]:
                return True

            if self.declaracao_variavel():
                continue
            elif self.comando_impressao():
                continue
            elif self.comando_condicional():
                continue
            elif self.comando_enquanto():
                continue
            elif self.declaracao_funcao():
                continue
            elif self.declaracao_procedimento():
                continue
            elif self.desvio_incondicional():
                continue
            elif self.chamada_procedimento():
                if not self.match("SEMICOLON"):
                    self.error_sintatico("Esperado ';' após a chamada do procedimento.")
                continue
            else:
                func_call = self.chamada_funcao()
                if func_call is not None:
                    if not self.match("SEMICOLON"):
                        self.error_sintatico("Esperado ';' após a chamada da função.")
                    continue

                if token.tipo != "RCBRACK":
                    self.error_sintatico(f"Comando inválido: {token.lexema}")
                break
        return True

    def declaracao_variavel(self):
        """Processa declaração de variável (atribuição opcional pela gramática)."""
        tipo = self.especificador_tipo()
        if not tipo:
            token = self.current_token()
            if token is not None and token.tipo == "ID_VAR":
                next_token = self.peek()
                if next_token is not None and next_token.tipo == "ATTR":
                    return self.atribuicao_variavel()
                else:
                    self.error_semantico(f"Declaração de variável '{token.lexema}' na linha {token.linha} não é antecedida por um especificador de tipo.")
            return False

        if tipo == "void":
            self.error_semantico("Não é permitido declarar variáveis do tipo 'void'.")

        if self.match("ID_VAR"):
            var_name = self.tokens[self.current - 1].lexema

            initialized = False

            # <variable_assignment> ::= "=" <expression> | ε
            if self.match("ATTR"):
                expr_type, _ = self.expressao()
                if expr_type != tipo:
                    self.error_semantico(f"Atribuição inválida: esperado '{tipo}', encontrado '{expr_type}'.")
                initialized = True

            if self.match("SEMICOLON"):
                self.add_symbol(var_name, tipo, initialized=initialized)
                return True
            else:
                self.error_sintatico("Esperado ';' após a declaração da variável.")
        else:
            self.error_sintatico("Esperado identificador de variável.")
        return False

    def atribuicao_variavel(self):
        """Processa uma atribuição de variável marcando como inicializada."""
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
        if self.match("ATTR"):
            expr_type, _ = self.expressao()
            if expr_type != var_type:
                self.error_semantico(f"Atribuição inválida: esperado '{var_type}', encontrado '{expr_type}'.")

            # Atualiza o status de inicialização no escopo mais interno onde a variável existe
            for scope in reversed(self.scope_stack):
                if var_name in scope:
                    scope[var_name]["initialized"] = True
                    break

            if var_name in self.uninitialized_vars:
                self.uninitialized_vars.remove(var_name)

            if self.match("SEMICOLON"):
                return True
            else:
                self.error_sintatico("Esperado ';' após a atribuição da variável.")
        else:
            self.error_sintatico("Esperado '=' após o identificador da variável.")
        return False

    def especificador_tipo(self):
        """Processa o tipo de uma variável."""
        if self.match("TYPE_INT"):
            return "int"
        elif self.match("TYPE_BOOL"):
            return "bool"
        elif self.match("TYPE_FLOAT"):
            return "float"
        elif self.match("TYPE_CHAR"):
            return "char"
        elif self.match("TYPE_VOID"):
            return "void"
        return None

    def comando_condicional(self):
        """Processa um comando condicional (if)."""
        if self.match("IF"):
            if self.match("LBRACK"):
                expr_type, _ = self.expressao()
                if expr_type != "bool":
                    self.error_semantico(f"Condição do 'if' deve ser do tipo 'bool', encontrado '{expr_type}'.")

                if self.match("RBRACK"):
                    if self.match("LCBRACK"):
                        if self.bloco():
                            if self.match("RCBRACK"):
                                self.else_opcional(None)
                                return True
                            else:
                                self.error_sintatico("Esperado '}' para fechar o bloco do 'if'.")
                        else:
                            self.error_sintatico("Bloco do 'if' inválido.")
                    else:
                        self.error_sintatico("Esperado '{' para iniciar o bloco do 'if'.")
                else:
                    self.error_sintatico("Esperado ')' para fechar a condição do 'if'.")
            else:
                self.error_sintatico("Esperado '(' para abrir a condição do 'if'.")
        return False

    def else_opcional(self, end_label):
        """Processa o bloco else opcional."""
        if self.match("ELSE"):
            if self.match("LCBRACK"):
                if self.bloco():
                    if not self.match("RCBRACK"):
                        self.error_sintatico("Esperado '}' para fechar o bloco do 'else'.")
                else:
                    self.error_sintatico("Bloco do 'else' inválido.")
            else:
                self.error_sintatico("Esperado '{' para abrir o bloco do 'else'.")
        return True

    def comando_enquanto(self):
        """Processa um comando while."""
        if self.match("WHILE"):
            if self.match("LBRACK"):
                expr_type, _ = self.expressao()
                if expr_type != "bool":
                    self.error_semantico(f"Condição do 'while' deve ser do tipo 'bool', encontrado '{expr_type}'.")

                if self.match("RBRACK"):
                    if self.match("LCBRACK"):
                        self.loop_depth += 1

                        while True:
                            token = self.current_token()
                            if not token:
                                self.error_sintatico("Fechamento '}' esperado para o bloco while")

                            if token.tipo == "RCBRACK":
                                self.match("RCBRACK")
                                break

                            if not (self.declaracao_variavel() or
                                    self.comando_condicional() or
                                    self.comando_impressao() or
                                    self.atribuicao_variavel() or
                                    self.desvio_incondicional()):
                                self.error_sintatico(f"Comando inválido dentro do bloco while: {token.lexema}")

                        self.loop_depth -= 1
                        return True
                    else:
                        self.error_sintatico("Esperado '{' para iniciar o bloco do 'while'.")
                else:
                    self.error_sintatico("Esperado ')' para fechar a condição do 'while'.")
            else:
                self.error_sintatico("Esperado '(' para abrir a condição do 'while'.")
        return False

    def comando_impressao(self):
        """Processa um comando print com parênteses obrigatórios."""
        if self.match("PRINT"):
            if not self.match("LBRACK"):
                self.error_sintatico("Esperado '(' após 'print'.")

            expr_type, _ = self.expressao()
            if expr_type not in ["int", "bool", "float", "char"]:
                self.error_semantico(f"Tipo inválido para impressão: '{expr_type}'.")

            if not self.match("RBRACK"):
                self.error_sintatico("Esperado ')' após o argumento de 'print'.")

            if not self.match("SEMICOLON"):
                self.error_sintatico("Esperado ';' após o comando 'print'.")

            return True
        return False

    def declaracao_funcao(self):
        """Processa a declaração de uma função."""
        if self.match("FUNC"):
            return_type = self.especificador_tipo()
            if not return_type:
                self.error_sintatico("Esperado tipo de retorno da função.")

            if self.match("ID_FUNC"):
                func_name = self.tokens[self.current - 1].lexema

                # Sem sobrecarga: não permite função com mesmo nome já declarado
                if func_name in self.function_params or func_name in self.procedure_params:
                    self.error_semantico(f"Função/procedimento '{func_name}' já declarado.")

                # Armazena o tipo de retorno no dicionário de funções
                self.function_params[func_name] = {
                    "return_type": return_type,
                    "param_types": []
                }
                self.function_return_type = return_type  # Mantém para compatibilidade
                self.enter_scope()  # Entra no escopo da função

                if self.match("LBRACK"):
                    params = self.lista_parametros()
                    self.function_params[func_name]["param_types"] = [param["type"] for param in params]
                    if self.match("RBRACK"):
                        if self.match("LCBRACK"):
                            # Verifica se o bloco tem retorno em todos os caminhos
                            self.scope_stack[-1]["_has_return"] = False

                            if return_type == "void":
                                if not self.bloco():
                                    self.error_sintatico("Bloco da função inválido.")
                            else:
                                self.bloco_com_retorno(return_type)
                                if not self.scope_stack[-1]["_has_return"]:
                                    self.error_semantico(f"Função '{func_name}' não retorna valor em todos os caminhos.")

                            if self.match("RCBRACK"):
                                self.exit_scope()
                                return True
                            else:
                                self.error_sintatico("Esperado '}' para fechar o corpo da função.")
                        else:
                            self.error_sintatico("Esperado '{' para iniciar o corpo da função.")
                    else:
                        self.error_sintatico("Esperado ')' para fechar a lista de parâmetros.")
                else:
                    self.error_sintatico("Esperado '(' para iniciar a lista de parâmetros.")
            else:
                self.error_sintatico("Esperado identificador da função.")
        return False

    def bloco_com_retorno(self, expected_return_type):
        """Processa um bloco verificando declarações de retorno."""
        has_return = False

        while True:
            token = self.current_token()
            if token is None:
                break

            if token.tipo == "RCBRACK":
                break

            if token.tipo == "FIM":
                break  # Final do programa, não precisa de SEMICOLON

            if self.match("RETURN"):
                if expected_return_type == "void":
                    self.error_semantico("Função void não pode retornar valor.")

                expr_type, _ = self.expressao()
                if expr_type != expected_return_type:
                    self.error_semantico(f"Tipo de retorno inválido: esperado '{expected_return_type}', encontrado '{expr_type}'.")

                token = self.current_token()
                if token is not None and token.tipo != "RCBRACK":
                    if not self.match("SEMICOLON"):
                        self.error_sintatico("Esperado ';' após o retorno.")

                self.scope_stack[-1]["_has_return"] = True
                has_return = True
                continue

            if self.declaracao_variavel():
                continue
            elif self.comando_condicional_com_retorno(expected_return_type):
                if self.scope_stack[-1].get("_has_return", False):
                    has_return = True
                continue
            elif self.comando_enquanto():
                continue
            elif self.chamada_procedimento():
                continue
            elif self.comando_impressao():
                continue
            elif self.desvio_incondicional():
                continue
            else:
                func_call = self.chamada_funcao()
                if func_call is not None:
                    if not self.match("SEMICOLON"):
                        self.error_sintatico("Esperado ';' após a chamada da função.")
                    continue

                break

        if expected_return_type != "void" and not has_return:
            self.error_semantico(f"Função não retorna valor em todos os caminhos.")

        return has_return

    def comando_condicional_com_retorno(self, expected_return_type):
        """Processa if/else verificando retorno em ambos os ramos."""
        if self.match("IF"):
            if self.match("LBRACK"):
                expr_type, _ = self.expressao()
                if expr_type != "bool":
                    self.error_semantico(f"Condição do 'if' deve ser do tipo 'bool', encontrado '{expr_type}'.")

                if self.match("RBRACK"):
                    if self.match("LCBRACK"):

                        if_has_return = self.bloco_com_retorno(expected_return_type)
                        if self.match("RCBRACK"):

                            else_has_return = self.else_opcional_com_retorno(expected_return_type)

                            if if_has_return and else_has_return:
                                self.scope_stack[-1]["_has_return"] = True
                            return True
                        else:
                            self.error_sintatico("Esperado '}' para fechar o bloco do 'if'.")
                    else:
                        self.error_sintatico("Esperado '{' para iniciar o bloco do 'if'.")
                else:
                    self.error_sintatico("Esperado ')' para fechar a condição do 'if'.")
            else:
                self.error_sintatico("Esperado '(' para abrir a condição do 'if'.")
        return False

    def else_opcional_com_retorno(self, expected_return_type, end_label=None):
        """Processa else verificando retorno."""
        if self.match("ELSE"):
            if self.match("LCBRACK"):
                else_has_return = self.bloco_com_retorno(expected_return_type)
                if not self.match("RCBRACK"):
                    self.error_sintatico("Esperado '}' para fechar o bloco do 'else'.")
                return else_has_return
            else:
                self.error_sintatico("Esperado '{' para abrir o bloco do 'else'.")
        return False

    def lista_parametros(self) -> list[dict[str, str]]:
        """Processa a lista de parâmetros marcando-os como inicializados."""
        params = []
        token = self.current_token()
        if token is not None and token.tipo == "RBRACK":
            return params

        while True:
            tipo = self.especificador_tipo()
            if not tipo or tipo == "void":
                self.error_sintatico("Esperado tipo do parâmetro (não pode ser void).")

            if not self.match("ID_VAR"):
                self.error_sintatico("Esperado identificador do parâmetro.")

            param_name = self.tokens[self.current - 1].lexema
            self.add_symbol(param_name, tipo, is_param=True)
            params.append({"type": tipo})

            if self.match("COMMA"):
                continue
            break

        return params
    def declaracao_parametro(self):
        """Processa a declaração de um parâmetro."""
        tipo = self.especificador_tipo()
        if not tipo:
            self.error_sintatico("Esperado tipo do parâmetro.")

        if self.match("ID_VAR"):
            param_name = self.tokens[self.current - 1].lexema
            self.add_symbol(param_name, tipo)
            return True
        return False

    def expressao(self):
        """Processa uma expressão."""
        return self.expressao_logica()

    def expressao_logica(self):
        """Processa uma expressão lógica com verificação de tipos comparáveis."""
        left_type, left_temp = self.expressao_aditiva()
        token = self.current_token()

        if token and token.tipo in ["EQUAL", "NOTEQUAL", "LESS", "LESSEQUAL", "GREAT", "GREATEQUAL"]:
            op = token.tipo
            self.match(token.tipo)
            right_type, right_temp = self.expressao_aditiva()

            # Verificação explícita de tipos comparáveis
            if left_type != right_type:
                self.error_semantico(f"Tipos incompatíveis na expressão: '{left_type}' e '{right_type}'.")

            # Verificação de operadores específicos para tipos numéricos
            if op in ["LESS", "LESSEQUAL", "GREAT", "GREATEQUAL"]:
                if left_type not in ["int", "float", "char"]:
                    self.error_semantico(f"Operador '{op}' requer operandos do tipo 'int', 'float' ou 'char', encontrado '{left_type}'.")

            # Operadores de igualdade/diferença podem ser usados com booleanos ou inteiros
            elif op in ["EQUAL", "NOTEQUAL"]:
                if left_type not in ["int", "bool", "float", "char"]:
                    self.error_semantico(f"Operador '{op}' requer operandos compatíveis, encontrado '{left_type}'.")

            op_map = {
                "EQUAL": "==",
                "NOTEQUAL": "!=",
                "LESS": "<",
                "LESSEQUAL": "<=",
                "GREAT": ">",
                "GREATEQUAL": ">="
            }
            return "bool", None
        return left_type, None

    def expressao_aditiva(self):
        """Processa uma expressão aditiva (+, -)."""
        left_type, _ = self.expressao_multiplicativa()
        token = self.current_token()
        while token and token.tipo in ["SUM", "SUB"]:
            op = token.tipo
            self.match(token.tipo)
            right_type, _ = self.expressao_multiplicativa()
            if left_type not in ["int", "float"] or right_type not in ["int", "float"]:
                self.error_semantico(f"Operação aritmética requer operandos numéricos ('int' ou 'float'), encontrado '{left_type}' e '{right_type}'.")

            op_map = {"SUM": "+", "SUB": "-"}
            left_type = "float" if "float" in (left_type, right_type) else "int"
            token = self.current_token()
        return left_type, None

    def expressao_multiplicativa(self):
        """Processa uma expressão multiplicativa (*, /)."""
        left_type, _ = self.termo()
        token = self.current_token()
        while token and token.tipo in ["MUL", "DIV"]:
            op = token.tipo
            self.match(token.tipo)
            right_type, _ = self.termo()
            if left_type not in ["int", "float"] or right_type not in ["int", "float"]:
                self.error_semantico(f"Operação multiplicativa requer operandos numéricos ('int' ou 'float'), encontrado '{left_type}' e '{right_type}'.")

            op_map = {"MUL": "*", "DIV": "/"}
            left_type = "float" if "float" in (left_type, right_type) else "int"
            token = self.current_token()
        return left_type, None

    def termo(self):
        """Processa um termo (número, variável, chamada de função ou valor booleano)."""
        token = self.current_token()
        if token is None:
            self.error_sintatico("Esperado número, variável ou chamada de função, mas a entrada terminou.")

        if token.tipo == "NUMBER":
            self.match("NUMBER")
            return "int", None
        elif token.tipo == "FLOAT_NUMBER":
            self.match("FLOAT_NUMBER")
            return "float", None
        elif token.tipo == "CHAR_CONST":
            self.match("CHAR_CONST")
            return "char", None
        elif token.tipo == "TRUE" or token.tipo == "FALSE":
            self.match(token.tipo)
            return "bool", None
        elif token.tipo == "ID_VAR":
            var_name = token.lexema
            var_type = self.get_symbol_type(var_name)
            self.match("ID_VAR")
            return var_type, None
        elif token.tipo == "ID_FUNC":
            # Chamada de função como parte de uma expressão
            result = self.chamada_funcao()
            if result is not None:
                func_type, _ = result
                return func_type, None
        self.error_sintatico(f"Esperado número, variável ou chamada de função, encontrado '{token.lexema}'.")

    def chamada_funcao(self) -> tuple[str, None] | None:
        """Processa uma chamada de função e retorna o tipo de retorno e o temporário."""
        if self.match("ID_FUNC"):
            func_name = self.tokens[self.current - 1].lexema
            if func_name in self.function_params:
                func_info = self.function_params[func_name]
                if self.match("LBRACK"):
                    expected_params = func_info["param_types"]
                    actual_args = self.lista_argumentos()

                    # Verificação semântica: número de parâmetros
                    if len(actual_args) != len(expected_params):
                        self.error_semantico(f"Número incorreto de argumentos para '{func_name}'. Esperado {len(expected_params)}, encontrado {len(actual_args)}")

                    # Verificação semântica: tipos dos parâmetros
                    for i, ((arg_type, _), expected_type) in enumerate(zip(actual_args, expected_params)):
                        if arg_type != expected_type:
                            self.error_semantico(f"Tipo incorreto para argumento {i+1} em '{func_name}'. Esperado {expected_type}, encontrado {arg_type}")

                    if not self.match("RBRACK"):
                        self.error_sintatico("Esperado ')' após argumentos da função")

                    # Verificação semântica: resultado não utilizado
                    next_token = self.current_token()
                    if next_token and next_token.tipo != "SEMICOLON":
                        print(f"[Aviso Semântico] Resultado da função '{func_name}' não utilizado")

                    return func_info["return_type"], None
                else:
                    self.error_sintatico("Esperado '(' após nome da função")
            else:
                self.error_semantico(f"Função '{func_name}' não declarada")
        return None

    def lista_argumentos(self) -> list[tuple[str, None]]:
        """Processa a lista de argumentos de uma função e retorna uma lista de tuplas (tipo, temp)."""
        token = self.current_token()
        if token is not None and token.tipo == "RBRACK":  # Caso não haja argumentos
            return []

        args = []
        expr_type, expr_temp = self.expressao()
        args.append((expr_type, expr_temp))
        while self.match("COMMA"):
            expr_type, expr_temp = self.expressao()
            args.append((expr_type, expr_temp))
        return args

    def declaracao_procedimento(self):
        """Processa a declaração de um procedimento."""
        if self.match("PROC"):
            if self.match("ID_PROC"):
                proc_name = self.tokens[self.current - 1].lexema

                # Sem sobrecarga: não permite procedimento com mesmo nome já declarado
                if proc_name in self.procedure_params or proc_name in self.function_params:
                    self.error_semantico(f"Função/procedimento '{proc_name}' já declarado.")

                self.enter_scope()  # Entra no escopo do procedimento

                if self.match("LBRACK"):
                    params = self.lista_parametros()
                    self.procedure_params[proc_name] = [param["type"] for param in params]
                    if self.match("RBRACK"):
                        if self.match("LCBRACK"):
                            # Processa o bloco até encontrar RCBRACK
                            while True:
                                token = self.current_token()
                                if token is None or token.tipo == "RCBRACK":
                                    break

                                if not (self.declaracao_variavel() or
                                        self.comando_condicional() or
                                        self.comando_enquanto() or
                                        self.comando_impressao() or
                                        self.atribuicao_variavel() or
                                        self.desvio_incondicional()):
                                    self.error_sintatico(f"Comando inválido no procedimento: {token.lexema}")

                            if self.match("RCBRACK"):
                                self.exit_scope()
                                return True
                            else:
                                self.error_sintatico("Esperado '}' para fechar o corpo do procedimento.")
                        else:
                            self.error_sintatico("Esperado '{' para iniciar o corpo do procedimento.")
                    else:
                        self.error_sintatico("Esperado ')' para fechar a lista de parâmetros.")
                else:
                    self.error_sintatico("Esperado '(' para iniciar a lista de parâmetros.")
            else:
                self.error_sintatico("Esperado identificador do procedimento.")
        return False

    def chamada_procedimento(self):
        """Processa uma chamada de procedimento."""
        if self.match("ID_PROC"):
            proc_name = self.tokens[self.current - 1].lexema
            if self.match("LBRACK"):
                expected_params = self.get_procedure_params(proc_name)
                actual_args = self.lista_argumentos()
                if len(actual_args) != len(expected_params):
                    self.error_semantico(f"Número incorreto de argumentos para o procedimento '{proc_name}'. Esperado {len(expected_params)}, encontrado {len(actual_args)}.")

                # Correção: Extrai apenas o tipo (arg_type) de cada tupla em actual_args
                for i, ((arg_type, _), param_type) in enumerate(zip(actual_args, expected_params)):
                    if arg_type != param_type:
                        self.error_semantico(f"Tipo incorreto para o argumento {i + 1} no procedimento '{proc_name}'. Esperado '{param_type}', encontrado '{arg_type}'.")

                if self.match("RBRACK"):
                    return True
                else:
                    self.error_sintatico("Esperado ')' para fechar os argumentos do procedimento.")
            else:
                self.error_sintatico("Esperado '(' para iniciar os argumentos do procedimento.")
        return False

    def desvio_incondicional(self):
        """Processa comandos de desvio incondicional (break, continue)."""
        if self.match("BREAK") or self.match("CONTINUE"):
            if self.loop_depth == 0:
                self.error_sintatico("'break' e 'continue' só podem ser usados dentro de loops.")
            if self.match("SEMICOLON"):
                return True
            else:
                self.error_sintatico("Esperado ';' após 'break' ou 'continue'.")
        return False


    def get_procedure_params(self, proc_name):
        """Retorna uma lista com os tipos dos parâmetros do procedimento."""
        if proc_name in self.procedure_params:
            return self.procedure_params[proc_name]
        self.error_semantico(f"Procedimento '{proc_name}' não declarado.")
        return []

    def get_function_params(self, func_name):
        """Retorna uma lista com os tipos dos parâmetros da função."""
        if func_name in self.function_params:
            return self.function_params[func_name]
        self.error_semantico(f"Função '{func_name}' não declarada.")
        return []
