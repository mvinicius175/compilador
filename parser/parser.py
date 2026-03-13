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

    def current_token(self):
        return self.tokens[self.current] if self.current < len(self.tokens) else None

    def peek(self):
        # Retorna o próximo token sem avançar o índice.
        if self.current + 1 < len(self.tokens):
            return self.tokens[self.current + 1]
        return None

    def match(self, expected_type):
        # Verifica se o token atual corresponde ao tipo esperado.
        token = self.current_token()
        if token and token.tipo == expected_type:
            print(f"Matched {expected_type}: {token.lexema} na linha {token.linha}")
            self.current += 1
            return token
        elif token and token.tipo == "INVALID":
            self.error_sintatico(f"Caractere inválido encontrado: '{token.lexema}'")
        return None

    def error_sintatico(self, message):
        # Gera um erro de sintaxe com contexto.
        token = self.current_token()
        context = f"Na linha {token.linha} encontrou '{token.lexema}'" if token else "no final da entrada"
        raise SyntaxError(f"[Erro Sintático] {message} {context}")

    def error_semantico(self, message):
        # Gera um erro semântico com contexto.
        token = self.current_token()
        context = f"Na linha {token.linha} encontrou '{token.lexema}'" if token else "no final da entrada"
        raise ValueError(f"[Erro Semântico] {message} {context}")

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

            if self.current_token() and self.current_token().tipo != "FIM":
                self.error_sintatico("Fim inesperado do parsing")

            return True

        except (SyntaxError, ValueError) as e:
            print(f"\nErro encontrado: {e}")
            return False
