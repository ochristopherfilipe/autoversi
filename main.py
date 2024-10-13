import re
import pyautogui
import subprocess
import speech_recognition as sr
import time
import tkinter as tk
from tkinter import filedialog
import threading
import json
from biblia_dicionarios import livros_biblia, numeros_por_extenso, qtd_capitulos_biblia
import ler_boletim

# Função para converter números por extenso em números
def converter_numeros_extenso(texto):
    for extenso, numero in numeros_por_extenso.items():
        texto = re.sub(r'\b' + re.escape(extenso) + r'\b', numero, texto, flags=re.IGNORECASE)
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
        # Adicione mais correções conforme necessário
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

    # Lista de padrões regex com limites de palavra (\b), ordenados do mais específico para o menos específico
    patterns = [
        rf'\b({book_pattern})\b\s+cap[ií]tulo\s+({numero_pattern})\s+(?:vers[ií]culo|verso)\s+({numero_pattern})',  # Livro capítulo X versículo Y
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+({numero_pattern})',                                         # Livro X Y 
        rf'\b({book_pattern})\b\s+({numero_pattern}):({numero_pattern})',                                           # Livro X:Y
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+(?:vers[ií]culo|verso)\s+({numero_pattern})',                # Livro X versículo Y
        rf'\b({book_pattern})\b\s+({numero_pattern})\s+verso\s+({numero_pattern})',                                 # Livro X verso Y
        rf'\b({book_pattern})\b\s+cap[ií]tulo\s+({numero_pattern})',                                                # Livro capítulo X
        rf'\b({book_pattern})\b\s+({numero_pattern})',                                                              # Livro capítulo X
        rf'\b({book_pattern})\b',                                                                                   # Apenas o nome do livro
    ]

    # Inicializa as variáveis
    livro = capitulo = versiculo = None

    # Procurar correspondências
    for pattern in patterns:
        matches = re.findall(pattern, texto, re.IGNORECASE)
        if matches:
            # Processa as correspondências e interrompe após a primeira encontrada
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
            break  # Interrompe o loop após encontrar a primeira correspondência

    # Verifica se encontrou alguma correspondência
    if livro is None:
        return {'sucesso': False, 'mensagem': "Nenhuma referência bíblica encontrada."}

    # Normaliza o nome do livro
    livro_normalizado = normalizar_nome_livro(livro)
    if livro_normalizado is None:
        return {'sucesso': False, 'mensagem': f"Erro: Referência inválida, livro '{livro}' não reconhecido."}

    # Converte números por extenso em dígitos
    capitulo = converter_numeros_extenso(capitulo)
    versiculo = converter_numeros_extenso(versiculo)

    # Valida o número do capítulo
    try:
        capitulo_num = int(capitulo)
    except ValueError:
        return {'sucesso': False, 'mensagem': f"Erro: Capítulo '{capitulo}' não é um número válido."}

    max_chapter = qtd_capitulos_biblia.get(livro_normalizado)
    if max_chapter is None:
        return {'sucesso': False, 'mensagem': f"Erro: Não foi possível obter o número de capítulos para o livro '{livro_normalizado}'."}

    if capitulo_num < 1 or capitulo_num > max_chapter:
        return {'sucesso': False, 'mensagem': f"Erro: O livro '{livro_normalizado}' tem capítulos de 1 a {max_chapter}. Capítulo {capitulo_num} é inválido."}

    # Valida o número do versículo
    try:
        versiculo_num = int(versiculo)
    except ValueError:
        return {'sucesso': False, 'mensagem': f"Erro: Versículo '{versiculo}' não é um número válido."}

    if versiculo_num < 1:
        return {'sucesso': False, 'mensagem': f"Erro: Versículo {versiculo_num} é inválido. Deve ser um número positivo."}

    # Se tudo estiver correto, retorna sucesso e os dados extraídos
    return {
        'sucesso': True,
        'mensagem': f"Referência encontrada: {livro_normalizado} {capitulo}:{versiculo}",
        'livro': livro_normalizado,
        'capitulo': capitulo,
        'versiculo': versiculo
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
        self.palavras_proximo = ["próximo", "próximo versículo", "continuando", "mais um", "seguindo"]
        self.palavras_anterior = ["anterior", "versículo anterior", "antes", "o versículo antes desse", "voltar"]

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
            # Usa o wmctrl para encontrar a janela do Holyrics e trazê-la para o foco
            resultado = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            linhas = resultado.stdout.splitlines()
            for linha in linhas:
                if "Holyrics" in linha:
                    janela_id = linha.split()[0]
                    subprocess.run(["wmctrl", "-i", "-a", janela_id])
                    time.sleep(1)
                    return
            self.label_status['text'] = "Janela do Holyrics não encontrada. Verifique se o programa está aberto."
        except Exception as e:
            self.label_status['text'] = f"Erro ao tentar focar a janela: {e}"

    def digitar_comandos(self, livro, capitulo, versiculo):
        print(f"Digitando comandos: Livro: {livro}, Capítulo: {capitulo}, Versículo: {versiculo}")

        # Tempo de espera
        x = 0.1

        try:
            # Converte o nome do livro para minúsculas antes de digitar
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

            # Limpa qualquer mensagem de erro anterior
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

            # Agenda a execução na thread principal
            self.master.after(0, processa_audio)

        # Obtém o tempo máximo de captura definido pelo usuário
        tempo_maximo = self.slider_tempo_captura.get()

        # Inicia a escuta em segundo plano com o tempo máximo de captura
        self.stop_listening = self.rec.listen_in_background(
            mic,
            callback,
            phrase_time_limit=tempo_maximo  # Define o tempo máximo de captura
        )

        while self.capturando:
            time.sleep(0.1)

        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
            self.stop_listening = None

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

# Executa a aplicação
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
