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
