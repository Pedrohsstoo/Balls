import os
import math
import ctypes
from ctypes import wintypes

import pygame

# -----------------------------
# Windows: pixels reais (sem escala de DPI) e janela no canto 0,0
# -----------------------------
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

pygame.init()

user32 = ctypes.windll.user32

# Assinaturas das funções da API do Windows
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080   # sem ícone na barra de tarefas
LWA_COLORKEY = 0x00000001
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SPI_GETWORKAREA = 0x0030


def posicao_cursor():
    """Posição global do cursor (funciona mesmo fora da bola)."""
    ponto = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(ponto))
    return pygame.Vector2(ponto.x, ponto.y)

# -----------------------------
# Configurações
# -----------------------------
LARGURA, ALTURA = pygame.display.get_desktop_sizes()[0]

# Área útil (tela sem a barra de tarefas) -> a bola "pousa" em cima da barra
area = wintypes.RECT()
user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(area), 0)
CHAO = area.bottom if area.bottom > 0 else ALTURA

TELA = pygame.display.set_mode((LARGURA, ALTURA), pygame.NOFRAME)
pygame.display.set_caption("Bola")

# Cor que vira "transparente" (e deixa os cliques passarem)
COR_TRANSPARENTE = (255, 0, 255)

hwnd = pygame.display.get_wm_info()["window"]
estilo = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
user32.SetWindowLongW(hwnd, GWL_EXSTYLE, estilo | WS_EX_LAYERED | WS_EX_TOOLWINDOW)

r, g, b = COR_TRANSPARENTE
user32.SetLayeredWindowAttributes(hwnd, r | (g << 8) | (b << 16), 0, LWA_COLORKEY)

# Sempre por cima das outras janelas
user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

clock = pygame.time.Clock()

# Física
GRAVIDADE = 1200          # pixels/s²
RESTITUICAO = 0.75        # quanto a bola quica
ATRITO_CHAO = 0.85
VELOCIDADE_MAX = 2500

# Bola
RAIO = 35
x = LARGURA // 2
y = 150

vx = 0
vy = 0

# Mouse
arrastando = False
ultima_pos_mouse = pygame.Vector2(0, 0)

# Colisão com o cursor
RAIO_CURSOR = 6            # "tamanho" do cursor para a colisão
RESTITUICAO_CURSOR = 0.9   # força do empurrão do cursor
cursor_anterior = posicao_cursor()
vel_cursor = pygame.Vector2(0, 0)

# Cores
VERMELHO = (220, 50, 50)
BRILHO = (255, 120, 120)


# -----------------------------
# Loop principal
# -----------------------------
rodando = True

while rodando:

    # Delta time
    dt = clock.tick(60) / 1000

    # Atalho global para fechar: Ctrl + Shift + Q
    # (funciona mesmo com outra janela em foco e fecha todas as bolas abertas)
    if (user32.GetAsyncKeyState(0x11) & 0x8000 and      # Ctrl
            user32.GetAsyncKeyState(0x10) & 0x8000 and  # Shift
            user32.GetAsyncKeyState(0x51) & 0x8000):    # Q
        rodando = False

    # Posição e velocidade do cursor neste quadro
    cursor = posicao_cursor()
    if dt > 0:
        vel_cursor = (cursor - cursor_anterior) / dt
    cursor_anterior = cursor

    for evento in pygame.event.get():

        if evento.type == pygame.QUIT:
            rodando = False

        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            rodando = False

        elif evento.type == pygame.MOUSEBUTTONDOWN:

            mouse = pygame.Vector2(evento.pos)
            na_bola = mouse.distance_to((x, y)) <= RAIO

            # Botão direito na bola: fecha o programa
            if evento.button == 3 and na_bola:
                rodando = False

            # Botão esquerdo na bola: pega a bola
            elif evento.button == 1 and na_bola:
                arrastando = True
                ultima_pos_mouse = mouse
                vx = 0
                vy = 0

        elif evento.type == pygame.MOUSEBUTTONUP:

            if evento.button == 1 and arrastando:
                arrastando = False

                # Limita velocidade
                velocidade = math.hypot(vx, vy)

                if velocidade > VELOCIDADE_MAX:
                    fator = VELOCIDADE_MAX / velocidade
                    vx *= fator
                    vy *= fator

    # -----------------------------
    # Movimento do mouse
    # -----------------------------
    if arrastando:

        mouse = cursor
        movimento = mouse - ultima_pos_mouse

        x = mouse.x
        y = mouse.y

        if dt > 0:
            vx = movimento.x / dt
            vy = movimento.y / dt

        ultima_pos_mouse = mouse

    else:

        # Gravidade
        vy += GRAVIDADE * dt

        # Movimento
        x += vx * dt
        y += vy * dt

        # Colisão com o cursor
        # (o cursor é tratado como um objeto de massa infinita)
        diferenca = pygame.Vector2(x, y) - cursor
        distancia = diferenca.length()
        distancia_min = RAIO + RAIO_CURSOR

        if distancia < distancia_min:

            if distancia > 0:
                normal = diferenca / distancia
            else:
                normal = pygame.Vector2(0, -1)

            # Empurra a bola para fora do cursor
            x = cursor.x + normal.x * distancia_min
            y = cursor.y + normal.y * distancia_min

            # Velocidade relativa na direção do contato
            vel_relativa = pygame.Vector2(vx, vy) - vel_cursor
            vel_normal = vel_relativa.dot(normal)

            # Só rebate se estiverem se aproximando
            if vel_normal < 0:
                impulso = -(1 + RESTITUICAO_CURSOR) * vel_normal
                vx += impulso * normal.x
                vy += impulso * normal.y

                velocidade = math.hypot(vx, vy)
                if velocidade > VELOCIDADE_MAX:
                    fator = VELOCIDADE_MAX / velocidade
                    vx *= fator
                    vy *= fator

        # Parede esquerda
        if x - RAIO < 0:
            x = RAIO
            vx = -vx * RESTITUICAO

        # Parede direita
        if x + RAIO > LARGURA:
            x = LARGURA - RAIO
            vx = -vx * RESTITUICAO

        # Teto
        if y - RAIO < 0:
            y = RAIO
            vy = -vy * RESTITUICAO

        # Chão (topo da barra de tarefas)
        if y + RAIO > CHAO:
            y = CHAO - RAIO
            vy = -vy * RESTITUICAO
            vx *= ATRITO_CHAO

            # Evita ficar tremendo infinitamente
            if abs(vy) < 50:
                vy = 0
            if abs(vx) < 5:
                vx = 0

    # -----------------------------
    # Desenho
    # -----------------------------
    TELA.fill(COR_TRANSPARENTE)

    pygame.draw.circle(TELA, VERMELHO, (int(x), int(y)), RAIO)
    pygame.draw.circle(
        TELA,
        BRILHO,
        (int(x - RAIO * 0.3), int(y - RAIO * 0.3)),
        int(RAIO * 0.2)
    )

    pygame.display.flip()


pygame.quit()