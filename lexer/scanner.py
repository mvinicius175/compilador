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


