from lexer.scanner import Scanner
from parser.parser import Parser

def Main():
    try:
        with open('teste.txt', 'r') as file:
            codigo_exemplo = file.read()
    except FileNotFoundError:
        print("Arquivo 'teste.txt' não encontrado!")
        return


    scanner = Scanner(codigo_exemplo)

    try:
        tokens = scanner.scan()
    except Exception as e:
        print(f"Erro ao escanear o código: {e}")
        return

    # print("=== Tokens Gerados ===")
    # for token in tokens:
    #     print(f"Tipo: {token.tipo}, Lexema: '{token.lexema}', Linha: {token.linha}")
    # print("======================")

    try:
        parser = Parser(tokens)
        success = parser.parse()

        if success:
            print("Análise sintática e semântica concluída sem erros.")

    except SyntaxError as e:
        print(f"Erro de sintaxe: {e}")
        return
    except Exception as e:
        print(f"Erro semântico: {e}")
        return

if __name__ == "__main__":
    Main()

