class Token:
    def __init__(self, tipo, lexema, linha):
        self.type = type
        self.lexem = lexem
        self.line = line

    def __str__(self):
        return f"Tipo: {self.type}\nLexema: {self.lexem}\nLinha: {self.line}\n"
