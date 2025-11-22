from lexer.scanner import Scanner

def Main():
    try:
        with open('teste.txt', 'r') as file:
            codigo_exemplo = file.read()
    except FileNotFoundError:
        print("Arquivo 'teste.txt' não encontrado!")
        return

    scanner = Scanner(codigo_exemplo)
    tokens = scanner.scan()

    with open('token_list.txt', 'w', encoding='utf-8') as output_file:
        output_file.write("=== Lista de Tokens ===\n")
        for i, token in enumerate(tokens, 1):
            output_file.write(f"{i}. {token}\n")
        output_file.write("=======================\n")

    total_tokens = len(tokens)
    print(f"Total de tokens lidos: {total_tokens}")
    print(f"Lista de tokens salva em 'token_list.txt'")
if __name__ == "__main__":
    Main()
