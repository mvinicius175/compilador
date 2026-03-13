class Token:
    def __init__(self, tipo, lexema, linha):
        self.tipo = tipo
        self.lexema = lexema
        self.linha = linha

    def __str__(self):
        return f"Tipo: {self.tipo}\nLexema: {self.lexema}\nLinha: {self.linha}\n"
