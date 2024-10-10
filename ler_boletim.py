# Seu script principal

import re
import PyPDF2
from biblia_dicionarios import livros_biblia, numeros_por_extenso  # Importa os dicionários

def extrair_texto_pdf(caminho_pdf):
    """Função para extrair texto de um arquivo PDF"""
    with open(caminho_pdf, 'rb') as arquivo:
        leitor_pdf = PyPDF2.PdfReader(arquivo)
        texto_completo = ""
        for pagina in leitor_pdf.pages:
            texto_completo += pagina.extract_text()
        return texto_completo

def normalizar_livro(livro):
    """Normaliza o nome do livro da bíblia"""
    for nome_normalizado, variacoes in livros_biblia.items():
        if livro.lower() in variacoes:
            return nome_normalizado
    return None

def normalizar_numero(numero):
    """Normaliza números por extenso para dígitos"""
    numero = numero.lower().strip()
    return numeros_por_extenso.get(numero, numero)

def encontrar_referencias(texto):
    """Encontra referências bíblicas no texto"""
    padrao = r'(\b\w+\b)\s*(\d+)?(?:[:,.\s]+)?(\d+)?(?:[-\s]+)?(\d+)?'
    referencias_encontradas = re.findall(padrao, texto)

    referencias_normalizadas = []
    for referencia in referencias_encontradas:
        livro, capitulo, versiculo_inicio, versiculo_fim = referencia
        livro_normalizado = normalizar_livro(livro)
        if livro_normalizado:
            capitulo = normalizar_numero(capitulo) if capitulo else "N/A"
            versiculo_inicio = normalizar_numero(versiculo_inicio) if versiculo_inicio else "1"
            versiculo_fim = normalizar_numero(versiculo_fim) if versiculo_fim else versiculo_inicio
            
            if capitulo != "N/A":
                referencias_normalizadas.append({
                    'livro': livro_normalizado,
                    'capitulo': capitulo,
                    'versiculo_inicio': versiculo_inicio,
                    'versiculo_fim': versiculo_fim
                })
    return referencias_normalizadas
