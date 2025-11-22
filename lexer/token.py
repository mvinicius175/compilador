class Token:
    def __init__(self, type, lexeme, line):
        self.type = type
        self.lexeme = lexeme
        self.line = line

    def __str__(self):
        return f"Tipo: {self.type}\nLexema: {self.lexeme}\nLinha: {self.line}\n"
