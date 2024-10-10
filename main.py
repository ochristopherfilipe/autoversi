import flet as ft

def main(page: ft.Page):

    # Configuração inicial da página
    page.title = "Autoversi"
    page.padding = 20
    page.window_width = 800
    page.window_height = 600
    
    # Título e Slogan
    titulo = ft.Text("Autoversi", size=40, weight="bold", color="green")
    subtitulo = ft.Text("Seleção automática de versículos em Holyrics com tecnologia de reconhecimento de fala...", size=18)

    # Seção de falas reconhecidas (área de pregação)
    falas_reconhecidas = ft.Column(
        [
            ft.Text("E como está escrito em João capítulo 3 versículo 16...", size=14),
            ft.Text("Vamos abrir em Romanos capítulo 8 versículo 28...", size=14),
            ft.Text("Se formos a Efésios capítulo 6 versículo 12...", size=14),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        alignment="start"
    )
    falas_container = ft.Container(
        content=falas_reconhecidas, 
        width=300, 
        height=250, 
        border_radius=10, 
        bgcolor="#f0f0f0", 
        padding=ft.padding.all(10)  # Aplicando padding corretamente
    )

    # Seção de referências encontradas
    referencias = ft.Column(
        [
            ft.Text("João 3:16", size=14),
            ft.Text("1 Coríntios 10:13", size=14),
            ft.Text("Atos 2:38", size=14),
        ],
        scroll=ft.ScrollMode.AUTO
    )
    referencias_container = ft.Container(
        content=referencias,
        width=150,
        height=200,
        border_radius=10,
        bgcolor="#f8f8f8",
        padding=ft.padding.all(10)  # Aplicando padding corretamente
    )

    # Botão de ativação (reconhecimento de fala)
    btn_ativacao = ft.ElevatedButton(
        "Iniciar/Parar", 
        icon=ft.icons.POWER_SETTINGS_NEW, 
        bgcolor="green", 
        color="white", 
        width=80,
        height=80,
        border_radius=40
    )

    # Área para inserir boletim em PDF
    boletim_pdf = ft.TextButton("INSIRA O BOLETIM EM PDF", width=200, height=50)

    # Controle de volume
    controle_volume = ft.Slider(min=0, max=100, value=50, label="Volume")

    # Gráfico de ondas sonoras (apenas decorativo neste exemplo)
    ondas_sonoras = ft.Text("~~~~~~~", size=20)

    # Layout da página
    page.add(
        ft.Row(
            [
                ft.Column(
                    [
                        titulo,
                        subtitulo,
                        falas_container,
                        boletim_pdf,
                    ], 
                    expand=True, 
                    alignment="start", 
                    spacing=20
                ),
                ft.Column(
                    [
                        btn_ativacao,
                        referencias_container,
                        controle_volume,
                        ondas_sonoras
                    ], 
                    expand=True, 
                    alignment="center", 
                    spacing=20
                ),
            ],
            spacing=50
        )
    )

# Execução da aplicação
ft.app(target=main)
