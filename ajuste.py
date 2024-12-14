import pandas as pd

# Caminho do arquivo
file_path = r"C:\Users\maria.santos\Documents\Christopher\autoversi\capitulos e versiculos.xlsx"

# Ler o arquivo Excel
# Substitua 'Sheet1' pelo nome da aba, se necessário
df = pd.read_excel(file_path, sheet_name="Planilha1")

# Filtrar as linhas que NÃO contêm "Total" em qualquer coluna
df_filtered = df[~df.apply(lambda row: row.astype(str).str.contains('Total', case=False, na=False).any(), axis=1)]

# Salvar o resultado de volta no arquivo original ou em um novo arquivo
output_file = r"C:\Users\maria.santos\Documents\Christopher\autoversi\capitulos_e_versiculos_limpo.xlsx"
df_filtered.to_excel(output_file, index=False)

print(f"Arquivo salvo com sucesso em: {output_file}")
