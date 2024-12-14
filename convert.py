import pandas as pd

# Defina os nomes do arquivo de entrada (Excel) e saída (CSV)
input_file = 'capitulos-versiculos.xlsx'
output_file = 'capitulos-versiculos.csv'

try:
    # Ler o arquivo Excel
    df = pd.read_excel(input_file)

    # Salvar como CSV
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"Arquivo convertido com sucesso: {output_file}")
except FileNotFoundError:
    print(f"Erro: O arquivo {input_file} não foi encontrado.")
except Exception as e:
    print(f"Ocorreu um erro: {e}")
