from lexer.token import Token

class Scanner:

    def __init__(self, program):
        # Lista de tokens gerados
        self.token_list = []
        # Programa/entrada como string
        self.program = program
        # índice do começo do lexema atual
        self.start = 0
        # índice do caractere atual sendo analisado
        self.current = 0
        # número da linha atual (começa em 1)
        self.line = 1

    def __str__(self):
        # Representação para depuração do estado atual do scanner
        return f"Tokens: {self.token_list}, Inicio: {self.start}, Atual: {self.current}, Linha: {self.line}"

    def nextChar(self):
        # Avança o ponteiro current e retorna o caractere anterior
        self.current += 1
        return self.program[self.current - 1]

    def lookAhead(self):
        if self.current < len(self.program):
            return self.program[self.current]
        return '\0'

    def scan(self):
        # Inicia a varredura e adiciona um token EOF ao final
        self.scanTokens()
        self.token_list.append(Token("EOF", "", self.line))
        return self.token_list

    def scanTokens(self):
        # Dicionário de palavras reservadas para mapear lexemas a tipos de token
        keywords = {
            "if": "IF", "else": "ELSE", "while": "WHILE", "break": "BREAK",
            "continue": "CONTINUE", "print": "PRINT", "true": "TRUE",
            "false": "FALSE", "func": "FUNC", "proc": "PROC", "return": "RETURN",
            "int": "TYPE_INT", "bool": "TYPE_BOOL"
        }
        # Mapeamento de tokens simples de caractere único
        tokens_map = {
            '(': "LBRACK", ')': "RBRACK", '{': "LCBRACK", '}': "RCBRACK",
            ';': "SEMICOLON", ',': "COMMA", '+': "SUM", '-': "SUB",
            '*': "MUL", '/': "DIV"
        }

        # Loop principal que percorre toda a entrada
        while self.current < len(self.program):
            # marca o início do próximo lexema
            self.start = self.current
            char = self.nextChar()

            # Ignora espaços e tabs e carriage return
            if char in ' \t\r':
                pass
            # Nova linha: incrementa número da linha
            elif char == '\n':
                self.line += 1
            # Tokens de caractere único (parênteses, operadores aritméticos simples, etc.)
            elif char in tokens_map:
                self.token_list.append(Token(tokens_map[char], char, self.line))
            # '=' pode ser '==' (EQUAL) ou '=' (ATTR)
            elif char == '=':
                self._match_double_char('=', "EQUAL", "ATTR")
            # '!' pode ser '!=' (NOT_EQUAL) ou '!' (NOT)
            elif char == '!':
                if self.lookAhead() == '=':
                    self.nextChar()
                    self.token_list.append(Token("NOT_EQUAL", "!=", self.line))
                else:
                    self.token_list.append(Token("NOT", "!", self.line))
            # '<' e '<='
            elif char == '<':
                if self.lookAhead() == '=':
                    self.nextChar()
                    self.token_list.append(Token("LESS_EQUAL", "<=", self.line))
                else:
                    self.token_list.append(Token("LESS", "<", self.line))
            # '>' e '>='
            elif char == '>':
                if self.lookAhead() == '=':
                    self.nextChar()
                    self.token_list.append(Token("GREATER_EQUAL", ">=", self.line))
                else:
                    self.token_list.append(Token("GREATER", ">", self.line))
            # Início de número: consome dígitos
            elif char.isdigit():
                self._scan_number()
            # Início de identificador ou palavra-chave: consome letras/dígitos
            elif char.isalpha():
                self._scan_identifier_or_keyword(keywords)
            # Qualquer outro caractere é tratado como inválido
            else:
                self.token_list.append(Token("INVALID", char, self.line))

    def _match_double_char(self, expected_char, double_type, single_type):
        """
        Verifica se o próximo caractere forma um operador duplo (por exemplo '==' ou '>=').
        Se sim, consome-o e adiciona o token do tipo duplo; caso contrário adiciona o token simples.
        """
        if self.lookAhead() == expected_char:
            self.nextChar()
            self.token_list.append(Token(double_type, expected_char * 2, self.line))
        else:
            self.token_list.append(Token(single_type, expected_char, self.line))

    def _scan_number(self):
        # Consome todos os dígitos subsequentes para formar um número inteiro
        while self.lookAhead().isdigit():
            self.nextChar()
        lexeme = self.program[self.start:self.current]
        self.token_list.append(Token("NUMBER", lexeme, self.line))

    def _scan_identifier_or_keyword(self, keywords):
        # Consome letras e dígitos que compõem o identificador ou palavra-chave
        while self.lookAhead().isalpha() or self.lookAhead().isdigit():
            self.nextChar()

        lexeme = self.program[self.start:self.current]

        # Se não for palavra reservada, classifica identificador pelo seu primeiro caractere:
        # - começa com 'f' -> função (ID_FUNC)
        # - começa com 'p' -> procedimento (ID_PROC)
        # - começa com 'v' -> variável (ID_VAR)
        # Caso contrário, marca como INVALID
        if lexeme not in keywords:
            first_char = lexeme[0].lower() if len(lexeme) > 0 else ''
            if first_char == "f":
                self.token_list.append(Token("ID_FUNC", lexeme, self.line))
            elif first_char == "p":
                self.token_list.append(Token("ID_PROC", lexeme, self.line))
            elif first_char == "v":
                self.token_list.append(Token("ID_VAR", lexeme, self.line))
            else:
                self.token_list.append(Token("INVALID", lexeme, self.line))
        else:
            # É uma palavra reservada: usa o tipo correspondente do dicionário keywords
            self.token_list.append(Token(keywords[lexeme], lexeme, self.line))
