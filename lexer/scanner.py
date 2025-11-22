from lexer.token import Token

class Scanner:
    def __init__(self, program):
        self.token_list = []
        self.program = program
        self.start = 0
        self.current = 0
        self.line = 1

    def __str__(self):
        return f"Tokens: {self.token_list}, Inicio: {self.start}, Atual: {self.current}, Linha: {self.line}"

    def nextChar(self):
        self.current += 1
        return self.program[self.current - 1]

    def lookAhead(self):
        if self.current < len(self.program):
            return self.program[self.current]
        return '\0'

    def scan(self):
        self.scanTokens()
        self.token_list.append(Token("EOF", "", self.line))
        return self.token_list

    def scanTokens(self):
        keywords = {
            "if": "IF", "else": "ELSE", "while": "WHILE", "break": "BREAK",
            "continue": "CONTINUE", "print": "PRINT", "true": "TRUE",
            "false": "FALSE", "func": "FUNC", "proc": "PROC", "return": "RETURN",
            "int": "TYPE_INT", "bool": "TYPE_BOOL"
        }
        tokens_map = {
            '(': "LBRACK", ')': "RBRACK", '{': "LCBRACK", '}': "RCBRACK",
            ';': "SEMICOLON", ',': "COMMA", '+': "SUM", '-': "SUB",
            '*': "MUL", '/': "DIV"
        }

        while self.current < len(self.program):
            self.start = self.current
            char = self.nextChar()

            if char in ' \t\r':
                pass
            elif char == '\n':
                self.line += 1
            elif char in tokens_map:
                self.token_list.append(Token(tokens_map[char], char, self.line))
            elif char == '=':
                self._match_double_char('=', "EQUAL", "ATTR")
            elif char == '!':
                if self.lookAhead() == '=':
                    self.nextChar()
                    self.token_list.append(Token("NOT_EQUAL", "!=", self.line))
                else:
                    self.token_list.append(Token("NOT", "!", self.line))
            elif char == '<':
                if self.lookAhead() == '=':
                    self.nextChar()
                    self.token_list.append(Token("LESS_EQUAL", "<=", self.line))
                else:
                    self.token_list.append(Token("LESS", "<", self.line))
            elif char == '>':
                if self.lookAhead() == '=':
                    self.nextChar()
                    self.token_list.append(Token("GREATER_EQUAL", ">=", self.line))
                else:
                    self.token_list.append(Token("GREATER", ">", self.line))
            elif char.isdigit():
                self._scan_number()
            elif char.isalpha():
                self._scan_identifier_or_keyword(keywords)
            else:
                self.token_list.append(Token("ERROR", char, self.line))

    def _match_double_char(self, expected_char, double_type, single_type):
        if self.lookAhead() == expected_char:
            self.nextChar()
            self.token_list.append(Token(double_type, expected_char * 2, self.line))
        else:
            self.token_list.append(Token(single_type, expected_char, self.line))

    def _scan_number(self):
        while self.lookAhead().isdigit():
            self.nextChar()
        lexeme = self.program[self.start:self.current]
        self.token_list.append(Token("NUMBER", lexeme, self.line))

    def _scan_identifier_or_keyword(self, keywords):

        while self.lookAhead().isalpha() or self.lookAhead().isdigit():
            self.nextChar()

        lexeme = self.program[self.start:self.current]

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
            self.token_list.append(Token(keywords[lexeme], lexeme, self.line))
