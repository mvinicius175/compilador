from lexer.scanner import Scanner
from parser.parser import Parser
from ir.generator import ThreeAddressGenerator


def main():
    try:
        with open("teste.txt", "r", encoding="utf-8") as file:
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

    try:
        parser = Parser(tokens)
        program_ast = parser.parse()

        symbol_table_path = parser.save_symbol_table()
        print(f"Tabela de símbolos salva em: {symbol_table_path}")

        ir_generator = ThreeAddressGenerator()
        ir_path = ir_generator.save(program_ast)
        print(f"Código de três endereços salvo em: {ir_path}")
        print("Análise sintática e semântica concluída sem erros.")

    except SyntaxError as e:
        print(f"Erro de sintaxe: {e}")
        return
    except Exception as e:
        print(f"Erro semântico: {e}")
        return


if __name__ == "__main__":
    main()
