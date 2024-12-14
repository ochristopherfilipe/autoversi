import re
import pyautogui
import subprocess
import speech_recognition as sr
import time
import tkinter as tk
from tkinter import filedialog
import threading
import json
from biblia_dicionarios import livros_biblia, numeros_por_extenso
import ler_boletim
import pygetwindow as gw
import openpyxl

# Função para carregar a estrutura da Bíblia (capítulos e versículos) a partir do XLSX
def carregar_estrutura_biblia(caminho_xlsx="capitulos-versiculos.xlsx"):
    import openpyxl
    wb = openpyxl.load_workbook(caminho_xlsx)
    ws = wb.active

    estrutura = {}
    # Supondo cabeçalho: Livro | Capítulo | Versículos
    for row in ws.iter_rows(min_row=2, values_only=True):
        livro, cap, vers = row

        # Se qualquer um destes for None ou não for número, ignorar esta linha
        if livro is None or cap is None or vers is None:
            # Você pode imprimir um aviso ou log para saber qual linha está com problema:
            # print(f"Linha ignorada por dados inválidos: {row}")
            continue

        try:
            cap_int = int(cap)
            vers_int = int(vers)
        except ValueError:
            # Caso não seja possível converter cap ou vers em inteiro, ignora esta linha
            # print(f"Linha ignorada por não converter em inteiro: {row}")
            continue

        if livro not in estrutura:
            estrutura[livro] = {}
        estrutura[livro][cap_int] = vers_int

    return estrutura


# Carrega a estrutura da Bíblia
estrutura_biblia = carregar_estrutura_biblia("capitulos-versiculos.xlsx")

# Função para converter números por extenso em números
def converter_numeros_extenso(texto):
    # Verifica números com "dois números separados" e ajusta para ":"
    texto = re.sub(r'\b(\d+)\s+(\d+)\b', r'\1:\2', texto)  # "nove sete" -> "9:7"

    # Converte números por extenso em números
    for extenso, numero in numeros_por_extenso.items():
        texto = re.sub(r'\b' + re.escape(extenso) + r'\b', numero, texto, flags=re.IGNORECASE)
    
    # Substitui espaços entre dois números novamente para ":"
    texto = re.sub(r'(\d+)\s+(\d+)', r'\1:\2', texto)
    
    return texto

# Função para garantir que números consecutivos sejam separados adequadamente
def corrigir_numero_consecutivo(texto):
    # Substitui números seguidos sem separação por um espaço entre eles
    return re.sub(r'(\d+)(\d+)', r'\1 \2', texto)

# Função para normalizar o nome do livro
def normalizar_nome_livro(nome):
    nome = nome.lower().strip()
    for chave, valores in livros_biblia.items():
        if nome in [v.lower() for v in valores]:
            return chave
    return None  # Retorna None se não encontrar

# Função de escape personalizada
def escape_book_name(name):
    # Escapa todos os caracteres especiais do regex, mas mantém os espaços
    return re.sub(r'([.^$*+?{}[\]\\|()])', r'\\\1', name)

##################################################################################################################################
# Função para corrigir erros comuns de reconhecimento de fala
def corrigir_misrecognicoes(texto):
    correcoes = {
        "na 1": "naum",
        "versículo versículo": "versículo",
        "capítulo capítulo": "capítulo",
    }
    for errado, correto in correcoes.items():
        texto = texto.lower().replace(errado, correto)
    return texto
##################################################################################################################################

def extrair_referencia_biblica(texto):
    # Corrige erros comuns de reconhecimento
    texto = corrigir_misrecognicoes(texto)

    # Converte números por extenso em números
    texto = converter_numeros_extenso(texto)

    # Extrair todas as variações de livros, excluindo as muito curtas
    book_variations = []
    for variations in livros_biblia.values():
        for var in variations:
            if len(var) >= 2:  # Exclui variações com menos de 2 caracteres
                book_variations.append(var)

    # Adiciona possíveis erros de reconhecimento ao padrão
    book_variations.extend(["na 1", "naum"])

    # Ordenar por tamanho decrescente
    book_variations = sorted(set(book_variations), key=lambda x: -len(x))

    # Construir o padrão para livros
    book_pattern = '|'.join(escape_book_name(name) for name in book_variations)

    # Modifica o padrão para aceitar números por extenso e dígitos
    numero_pattern = r'\d+|' + '|'.join(numeros_por_extenso.keys())

    patterns = [
        rf'\b({book_pattern})\b\s+({numero_pattern}):({numero_pattern})',  # Livro X:Y
        rf'\b({book_pattern})\b\s+cap[ií]tulo\s+({numero_pattern})\s+(?:vers[ií]culo|verso)\s+({numero_pattern})', 
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+({numero_pattern})',
        rf'\b({book_pattern})\b\s+cap[ií]tulo\s+({numero_pattern})\s+(?:vers[ií]culo|verso)\s+({numero_pattern})',
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+({numero_pattern})',
        rf'\b({book_pattern})\b\s+({numero_pattern}):({numero_pattern})',
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+(?:vers[ií]culo|verso)\s+({numero_pattern})',
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+verso\s+({numero_pattern})',
        rf'\b({book_pattern})\b\s+cap[ií]tulo\s+({numero_pattern})',
        rf'\b({book_pattern})\b\s+({numero_pattern})',
        rf'\b({book_pattern})\b',
    ]

    livro = capitulo = versiculo = None

    for pattern in patterns:
        matches = re.findall(pattern, texto, re.IGNORECASE)
        if matches:
            match = matches[0]
            if len(match) == 3:
                livro, capitulo, versiculo = match
            elif len(match) == 2:
                livro, capitulo = match
                versiculo = '1'
            elif len(match) == 1:
                livro = match[0]
                capitulo = '1'
                versiculo = '1'
            break

    if livro is None:
        return {'sucesso': False, 'mensagem': "Nenhuma referência bíblica encontrada."}

    # Normaliza o nome do livro
    livro_normalizado = normalizar_nome_livro(livro)
    if livro_normalizado is None or livro_normalizado not in estrutura_biblia:
        return {'sucesso': False, 'mensagem': f"Erro: Livro '{livro}' não reconhecido."}

    # Converte capítulo e versículo por extenso para dígito
    capitulo = converter_numeros_extenso(capitulo)
    versiculo = converter_numeros_extenso(versiculo)

    def validar_e_corrigir(livro, cap, vers):
        # Tenta converter para inteiro
        try:
            cap_num = int(cap)
        except:
            return None, None, False
        try:
            vers_num = int(vers)
        except:
            return None, None, False

        # Verifica se o capítulo existe no livro
        if cap_num not in estrutura_biblia[livro]:
            return None, None, False

        max_versiculos = estrutura_biblia[livro][cap_num]
        if vers_num < 1 or vers_num > max_versiculos:
            return None, None, False

        return cap_num, vers_num, True

    # Primeiro, tentar validar diretamente
    cap_num, vers_num, valido = validar_e_corrigir(livro_normalizado, capitulo, versiculo)
    if not valido:
        # Tentativa de correção: ex. "97" -> tentar "9:7"
        if capitulo.isdigit() and len(capitulo) > 1 and versiculo == '1':
            # Tentar separar capitulo em duas partes
            for i in range(1, len(capitulo)):
                part_cap = capitulo[:i]
                part_vers = capitulo[i:]
                c_num, v_num, val = validar_e_corrigir(livro_normalizado, part_cap, part_vers)
                if val:
                    capitulo = str(c_num)
                    versiculo = str(v_num)
                    cap_num = c_num
                    vers_num = v_num
                    valido = True
                    break

        # Caso não tenha valido ainda, nenhuma correção possível
        if not valido:
            return {'sucesso': False, 'mensagem': f"Erro: Não foi possível corrigir a referência {livro_normalizado} {capitulo}:{versiculo}. Verifique se o capítulo/versículo existem."}

    return {
        'sucesso': True,
        'mensagem': f"Referência encontrada: {livro_normalizado} {cap_num}:{vers_num}",
        'livro': livro_normalizado,
        'capitulo': str(cap_num),
        'versiculo': str(vers_num)
    }

# Função para listar microfones disponíveis
def listar_microfones():
    microfones = sr.Microphone.list_microphone_names()
    print("Microfones disponíveis:")
    for i, mic in enumerate(microfones):
        print(f"{i}: {mic}")
    return microfones

# Função para salvar versículos encontrados em um arquivo JSON
def salvar_versiculos_arquivo(referencias, caminho_arquivo="versiculos_encontrados.json"):
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(referencias, f, ensure_ascii=False, indent=4)

def carregar_versiculos(caminho_arquivo="versiculos_encontrados.json"):
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Função para selecionar arquivo PDF usando Tkinter
def selecionar_arquivo_boletim():
    root = tk.Tk()
    root.withdraw()
    caminho_pdf = filedialog.askopenfilename(
        title="Selecione o boletim em PDF",
        filetypes=[("PDF files", "*.pdf")]
    )
    root.destroy()
    return caminho_pdf

# Classe principal da aplicação
class App:
    def __init__(self, master):
        self.master = master
        master.title("AutoVersi")

        # Variável para controlar o estado da captura de voz
        self.capturando = False

        # Inicializa o reconhecedor de voz
        self.rec = sr.Recognizer()

        # Listar microfones disponíveis
        self.microfones = listar_microfones()

        # Variable to hold selected microphone
        self.microfone_var = tk.StringVar()
        self.microfone_var.set("Selecione o microfone")

        self.dropdown_microfone = tk.OptionMenu(master, self.microfone_var, *self.microfones)
        self.dropdown_microfone.config(width=50)

        # Criação dos widgets
        self.btn_iniciar = tk.Button(master, text="Iniciar Captura", command=self.iniciar_captura)
        self.btn_parar = tk.Button(master, text="Parar Captura", command=self.parar_captura, state=tk.DISABLED)
        self.btn_selecionar_boletim = tk.Button(master, text="Selecionar Boletim", command=self.processar_boletim)

        # Label para mostrar erros e status
        self.label_status = tk.Label(master, text="", fg="red")

        # Label para mostrar o texto reconhecido
        self.label_recognized_text = tk.Label(master, text="", fg="blue")

        # Listbox para mostrar os versículos encontrados
        self.listbox_versiculos = tk.Listbox(master, height=10, width=50)
        self.listbox_versiculos.config(selectmode=tk.SINGLE)

        # Slider para ajustar o tempo máximo de captura de áudio
        self.label_tempo_captura = tk.Label(master, text="Tempo máximo de captura de áudio (segundos):")
        self.slider_tempo_captura = tk.Scale(master, from_=1, to=30, orient=tk.HORIZONTAL)
        self.slider_tempo_captura.set(5)  # Valor padrão de 5 segundos

        # Layout dos widgets
        self.dropdown_microfone.pack(pady=5)
        self.btn_iniciar.pack(pady=5)
        self.btn_parar.pack(pady=5)
        self.btn_selecionar_boletim.pack(pady=5)
        self.label_tempo_captura.pack(pady=5)
        self.slider_tempo_captura.pack(pady=5)
        self.label_status.pack(pady=5)
        self.label_recognized_text.pack(pady=5)
        self.listbox_versiculos.pack(pady=5)

        # Thread para o reconhecimento de fala
        self.thread_escuta = None
        self.stop_listening = None

        # Lista de palavras para avançar e retroceder versículos
        self.palavras_proximo = [
            "próximo", 
            "próximo versículo", 
            "continuando", 
            "mais um", 
            "seguindo", 
            "depois desse", 
            "o próximo", 
            "ir para o próximo", 
            "verso seguinte", 
            "continuar", 
            "prossiga", 
            "segue", 
            "pule para o próximo", 
            "próximo texto", 
            "continua", 
            "vai para o próximo", 
            "mais um versículo", 
            "leia o próximo", 
            "avançar", 
            "passar para o próximo"
        ]

        self.palavras_anterior = [
            "anterior", 
            "versículo anterior", 
            "antes", 
            "o versículo antes desse", 
            "voltar", 
            "voltar atrás", 
            "retroceder", 
            "o anterior", 
            "volte", 
            "verso anterior", 
            "ir para o anterior", 
            "leia o anterior", 
            "pule para o anterior", 
            "retorne", 
            "retornar", 
            "volte para o anterior", 
            "recuar", 
            "rever o anterior", 
            "passar para o anterior"
        ]

        # Lista de referências carregadas do boletim
        self.referencias_boletim = []

    def verificar_comando_proximo_anterior(self, texto):
        texto = texto.lower()

        # Verifica se o texto contém alguma palavra que indica 'próximo'
        for palavra in self.palavras_proximo:
            if palavra in texto:
                print("Comando: Próximo versículo")
                self.avancar_versiculo()
                self.label_status['text'] = "Comando: Próximo versículo"
                return True  # Retorna True para indicar que um comando foi reconhecido

        # Verifica se o texto contém alguma palavra que indica 'anterior'
        for palavra in self.palavras_anterior:
            if palavra in texto:
                print("Comando: Versículo anterior")
                self.voltar_versiculo()
                self.label_status['text'] = "Comando: Versículo anterior"
                return True  # Retorna True para indicar que um comando foi reconhecido

        return False  # Nenhum comando reconhecido

    def avancar_versiculo(self):
        try:
            print("Avançando para o próximo versículo.")
            pyautogui.press('right')  # Pressiona a seta para a direita
            time.sleep(0.1)
        except Exception as e:
            self.label_status['text'] = f"Erro ao tentar avançar o versículo: {e}"

    def voltar_versiculo(self):
        try:
            print("Voltando para o versículo anterior.")
            pyautogui.press('left')  # Pressiona a seta para a esquerda
            time.sleep(0.1)
        except Exception as e:
            self.label_status['text'] = f"Erro ao tentar voltar o versículo: {e}"

    def alternar_para_holyrics(self):
        try:
            # Obtém todas as janelas abertas
            janelas = gw.getAllTitles()

            # Procura por uma janela que contenha "Holyrics" no título
            for janela in janelas:
                if "Holyrics" in janela:
                    # Alterna o foco para a janela encontrada
                    window = gw.getWindowsWithTitle(janela)[0]
                    window.activate()
                    time.sleep(1)
                    return
            
            # Se nenhuma janela com "Holyrics" foi encontrada
            self.label_status['text'] = "Janela do Holyrics não encontrada. Verifique se o programa está aberto."

        except Exception as e:
            # Mensagem de erro caso algo dê errado
            self.label_status['text'] = f"Erro ao tentar focar a janela: {e}"

    def digitar_comandos(self, livro, capitulo, versiculo):
        print(f"Digitando comandos: Livro: {livro}, Capítulo: {capitulo}, Versículo: {versiculo}")

        # Tempo de espera
        x = 0.1

        try:
            livro = livro.lower()
            time.sleep(x)

            # Digita o nome do livro no campo de pesquisa do Holyrics
            pyautogui.press('esc')
            pyautogui.press('esc')
            time.sleep(x)
            pyautogui.write(livro)
            pyautogui.press('enter')

            # Digita o capítulo
            pyautogui.write(str(capitulo))
            pyautogui.press('enter')

            # Digita o versículo
            pyautogui.write(str(versiculo))
            time.sleep(x)
            pyautogui.press('enter')

        except Exception as e:
            self.label_status['text'] = f"Erro ao digitar comandos: {e}"

    def iniciar_captura(self):
        if not self.capturando:
            # Obtém o índice do microfone selecionado
            selected_mic = self.microfone_var.get()
            if selected_mic == "Selecione o microfone":
                self.label_status['text'] = "Por favor, selecione um microfone antes de iniciar a captura."
                return
            try:
                self.indice_microfone = self.microfones.index(selected_mic)
            except ValueError:
                self.label_status['text'] = "Microfone selecionado não encontrado."
                return

            self.label_status['text'] = ""
            self.capturando = True
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_parar.config(state=tk.NORMAL)
            self.thread_escuta = threading.Thread(target=self.reconhecer_fala_continuamente)
            self.thread_escuta.start()

    def parar_captura(self):
        if self.capturando:
            self.capturando = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_parar.config(state=tk.DISABLED)
            if self.stop_listening:
                self.stop_listening(wait_for_stop=False)

    def processar_boletim(self):
        caminho_pdf = selecionar_arquivo_boletim()
        if caminho_pdf:
            texto_pdf = ler_boletim.extrair_texto_pdf(caminho_pdf)
            referencias = ler_boletim.encontrar_referencias(texto_pdf)
            salvar_versiculos_arquivo(referencias)
            self.label_status['text'] = "Referências encontradas no boletim foram salvas."
            self.referencias_boletim = referencias
            self.exibir_versiculos()
        else:
            self.label_status['text'] = "Nenhum arquivo selecionado."

    def exibir_versiculos(self):
        self.listbox_versiculos.delete(0, tk.END)
        for ref in self.referencias_boletim:
            versiculo_texto = f"{ref['livro']} {ref['capitulo']}:{ref['versiculo_inicio']}"
            if ref['versiculo_inicio'] != ref['versiculo_fim']:
                versiculo_texto += f"-{ref['versiculo_fim']}"
            self.listbox_versiculos.insert(tk.END, versiculo_texto)

    def marcar_versiculo_lido(self, referencia_str):
        indices = self.listbox_versiculos.get(0, tk.END)
        for idx, item in enumerate(indices):
            if item == referencia_str:
                # Marcar como lido (riscado)
                self.listbox_versiculos.itemconfig(idx, fg='gray')
                break

    def reconhecer_fala_continuamente(self):
        try:
            mic = sr.Microphone(device_index=self.indice_microfone)
        except Exception as e:
            self.label_status['text'] = f"Erro ao acessar o microfone: {e}"
            self.capturando = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_parar.config(state=tk.DISABLED)
            return

        # Ajusta para ruído ambiente
        with mic as source:
            self.rec.adjust_for_ambient_noise(source)
            print("Aguardando fala...")

        def callback(recognizer, audio):
            def processa_audio():
                try:
                    texto = recognizer.recognize_google(audio, language="pt-BR")
                    print("Texto reconhecido:", texto)
                    self.label_recognized_text['text'] = "Texto reconhecido: " + texto

                    comando_reconhecido = self.verificar_comando_proximo_anterior(texto)
                    if comando_reconhecido:
                        return  # Se um comando foi reconhecido, não tenta extrair referência

                    resultado = extrair_referencia_biblica(texto)
                    self.label_status['text'] = resultado['mensagem']

                    if resultado['sucesso']:
                        self.alternar_para_holyrics()
                        self.digitar_comandos(resultado['livro'], resultado['capitulo'], resultado['versiculo'])

                        # Marcar versículo como lido se estiver na lista do boletim
                        referencia_str = f"{resultado['livro']} {resultado['capitulo']}:{resultado['versiculo']}"
                        self.marcar_versiculo_lido(referencia_str)

                except sr.UnknownValueError:
                    self.label_status['text'] = "Desculpe, não entendi o que você disse."
                except sr.RequestError as e:
                    self.label_status['text'] = f"Erro ao acessar o serviço de reconhecimento de fala: {e}"

            self.master.after(0, processa_audio)

        # Obtém o tempo máximo de captura definido pelo usuário
        tempo_maximo = self.slider_tempo_captura.get()

        self.stop_listening = self.rec.listen_in_background(
            mic,
            callback,
            phrase_time_limit=tempo_maximo
        )

        while self.capturando:
            time.sleep(0.1)

        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
            self.stop_listening = None

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
