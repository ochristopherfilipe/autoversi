import ezodf

# Função para ler o arquivo ODS e transformar em um dicionário
def ods_para_dicionario(arquivo_ods):
    # Carregar o arquivo ODS
    ezodf.config.set_table_expand_strategy('all')
    doc = ezodf.opendoc(arquivo_ods)
    
    # Pegar a primeira planilha
    planilha = doc.sheets[0]
    
    # Inicializar dicionário
    dados = {}

    # Iterar sobre as linhas da planilha (ignorando o cabeçalho)
    for i, linha in enumerate(planilha.rows()):
        if i == 0:  # Ignorar a primeira linha (cabeçalho)
            continue
        livro = str(linha[0].value).strip()  # Nome do livro
        qtd_cap = int(linha[1].value)  # Quantidade de capítulos
        if livro:  # Verifica se a célula não está vazia
            dados[livro] = qtd_cap
    
    return dados

# Caminho para o arquivo ODS
arquivo = "capitulos.ods"

# Chama a função e obtém o dicionário
dicionario_livros = ods_para_dicionario(arquivo)

# Salvando o dicionário em um arquivo .py
with open("dicionario_livros.py", "w") as f:
    f.write(f"dicionario_livros = {dicionario_livros}\n")

print("Dicionário salvo em dicionario_livros.py")
