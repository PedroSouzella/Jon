# -*- coding: utf-8 -*-
"""
Controle de filmes e vídeos por voz: tela cheia, play/pausa, avançar/voltar, volume, próximo episódio.
Funciona com o Stremio, VLC e os streamings no navegador (Netflix, YouTube, Prime Video, Disney+, Max...).
O Jon acha a janela do vídeo, traz pra frente e aperta o atalho de teclado que o próprio player usa.
"""
import ctypes
import re
import time
from ctypes import wintypes

# programas que são players
PLAYERS = {"stremio.exe": "stremio", "vlc.exe": "vlc", "mpc-hc64.exe": "mpc", "mpc-hc.exe": "mpc",
           "mpc-be64.exe": "mpc", "potplayermini64.exe": "potplayer", "potplayermini.exe": "potplayer",
           "kodi.exe": "kodi", "plex.exe": "plex"}
NAVEGADORES = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "vivaldi.exe"}
# título da aba -> site
SITES = [("netflix", "netflix"), ("youtube", "youtube"), ("prime video", "prime"), ("primevideo", "prime"),
         ("disney+", "disney"), ("disney plus", "disney"), ("| max", "max"), ("hbo max", "max"), ("max -", "max"),
         ("globoplay", "globoplay"), ("crunchyroll", "crunchyroll"), ("twitch", "twitch"), ("paramount", "paramount"),
         ("apple tv", "appletv"), ("star+", "disney"), ("pluto tv", "pluto"), ("mubi", "mubi")]
# o que a pessoa fala -> qual player/site ela quer
FALADO = {"stremio": "stremio", "netflix": "netflix", "youtube": "youtube", "prime": "prime", "amazon": "prime",
          "disney": "disney", "max": "max", "hbo": "max", "globoplay": "globoplay", "crunchyroll": "crunchyroll",
          "twitch": "twitch", "paramount": "paramount", "vlc": "vlc", "apple tv": "appletv", "pluto": "pluto"}

ALVO = (r"\b(filme|filmes|video|videos|serie|series|episodio|episodios|anime|desenho|documentario|"
        r"stremio|netflix|youtube|prime|amazon prime|disney|hbo|globoplay|crunchyroll|twitch|paramount|vlc|"
        r"pluto|apple tv|player|streaming)\b|\bno max\b|\ba max\b|\bo max\b")


ultimo = None            # (tipo, quando) do último player aberto/controlado — pra "e dá play" logo depois


def _janelas():
    """[(hwnd, exe_minusculo, titulo)] das janelas visíveis, a de cima primeiro."""
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    lista = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd) or u32.GetWindow(hwnd, 4):
            return True
        n = u32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        b = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(hwnd, b, n + 1)
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = ""
        h = k32.OpenProcess(0x1000, False, pid.value)
        if h:
            buf = ctypes.create_unicode_buffer(520)
            sz = wintypes.DWORD(520)
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz)):
                exe = buf.value.rsplit("\\", 1)[-1].lower()
            k32.CloseHandle(h)
        lista.append((hwnd, exe, b.value))
        return True
    u32.EnumWindows(cb, 0)
    return lista


def _tipo(exe, titulo):
    """Que player é essa janela (ou None)."""
    if exe in PLAYERS:
        return PLAYERS[exe]
    if exe in NAVEGADORES:
        t = titulo.lower()
        for chave, site in SITES:
            if chave in t:
                return site
    return None


def em_foco():
    """Tipo do player que está na frente agora (ou None)."""
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = u32.GetForegroundWindow()
    for h, exe, titulo in _janelas():
        if h == hwnd:
            return _tipo(exe, titulo)
    return None


def achar(desejado=None):
    """(hwnd, tipo) do player: o pedido pelo nome, senão o que está na frente, senão o primeiro aberto."""
    janelas = [(h, _tipo(e, t)) for h, e, t in _janelas()]
    janelas = [(h, tp) for h, tp in janelas if tp]
    if desejado:
        for h, tp in janelas:
            if tp == desejado:
                return h, tp
        return None, None
    fg = ctypes.windll.user32.GetForegroundWindow()
    for h, tp in janelas:
        if h == fg:
            return h, tp
    prefer = ["stremio", "netflix", "prime", "disney", "max", "globoplay", "youtube"]
    janelas.sort(key=lambda x: prefer.index(x[1]) if x[1] in prefer else 99)
    return janelas[0] if janelas else (None, None)


# atalhos de teclado de cada player
def _teclas(tipo, acao):
    yt = tipo == "youtube"
    vlc = tipo == "vlc"
    mpc = tipo in ("mpc", "potplayer")
    if acao == "tela_cheia":
        return "alt+enter" if mpc else "f"
    if acao == "sair_tela_cheia":
        return "esc"
    if acao == "play_pausa":
        return "k" if yt else "space"
    if acao == "avancar":
        return "l" if yt else ("alt+right" if vlc else "right")
    if acao == "voltar":
        return "j" if yt else ("alt+left" if vlc else "left")
    if acao == "volume_mais":
        return "ctrl+up" if vlc else "up"
    if acao == "volume_menos":
        return "ctrl+down" if vlc else "down"
    if acao == "inicio":
        return "0" if yt else "home"
    if acao == "mudo":
        return "m"
    if acao == "proximo":
        return "shift+n" if tipo in ("youtube", "netflix") else ("n" if vlc else None)
    if acao == "pular_abertura":
        return "s" if tipo == "netflix" else None
    return None


NOMES = {"stremio": "Stremio", "netflix": "Netflix", "youtube": "YouTube", "prime": "Prime Video",
         "disney": "Disney+", "max": "Max", "globoplay": "Globoplay", "crunchyroll": "Crunchyroll",
         "twitch": "Twitch", "paramount": "Paramount+", "vlc": "VLC", "mpc": "MPC", "potplayer": "PotPlayer",
         "appletv": "Apple TV", "pluto": "Pluto TV", "kodi": "Kodi", "plex": "Plex", "mubi": "MUBI"}


def entender(f: str):
    """Frase normalizada -> (acao, vezes, player_pedido) ou None se não for controle de vídeo."""
    pedido = None
    for falado, tipo in FALADO.items():
        if re.search(r"\b" + falado + r"\b", f):
            pedido = tipo
            break
    if re.search(r"\b(proximo|proxima) (episodio|ep|video|capitulo)\b|\bpula (pro|para o) proximo\b", f):
        return "proximo", 1, pedido
    if re.search(r"\b(volta|voltar|volte|recomeca|recomecar|reinicia|reiniciar|comeca|comecar|assiste|assistir)\b.*"
                 r"\b(desde o|do|pro|para o|ao|no|de novo do) (inicio|comeco)\b|\b(desde o|do) (inicio|comeco)\b", f):
        return "inicio", 1, pedido
    if re.search(r"\b(pula|pular|pule)\b.*\b(abertura|intro|introducao)\b", f):
        return "pular_abertura", 1, pedido
    if re.search(r"\b(tela cheia|full ?screen|tela inteira|tela toda|maximiza|maximizar|aumenta a tela)\b", f):
        sair = re.search(r"\b(sai|sair|saia|tira|tirar|desliga|volta|voltar|fecha|fechar)\b", f)
        return ("sair_tela_cheia" if sair else "tela_cheia"), 1, pedido
    if re.search(r"\b(muta|mutar|mudo|tira o som|sem som|silencia)\b", f):
        return "mudo", 1, pedido
    if re.search(r"\b(aumenta|aumentar|sobe|subir|mais alto)\b.*\b(volume|som)\b|\bvolume (mais alto|pra cima)\b", f):
        return "volume_mais", 3, pedido
    if re.search(r"\b(abaixa|abaixar|diminui|diminuir|baixa|mais baixo)\b.*\b(volume|som)\b|\bvolume (mais baixo|pra baixo)\b",
                 f):
        return "volume_menos", 3, pedido
    m = re.search(r"\b(avanca|avancar|adianta|adiantar|pula|pular|passa|passar|volta|voltar|retrocede|"
                  r"retroceder|atrasa)\b(?:\D*?(\d+|um|uma|dois|tres|cinco|dez|trinta)\s*(segundos?|seg|minutos?|min))?",
                  f)
    if m and (m.group(2) or re.search(ALVO, f) or re.search(r"\b(um pouco|pouquinho|segundos?|minutos?)\b", f)):
        numeros = {"um": 1, "uma": 1, "dois": 2, "tres": 3, "cinco": 5, "dez": 10, "trinta": 30}
        n = m.group(2)
        n = int(n) if n and n.isdigit() else numeros.get(n or "", 10)
        seg = n * 60 if (m.group(3) or "").startswith("min") else n
        voltar = m.group(1).startswith(("volt", "retro", "atras"))
        return ("voltar" if voltar else "avancar"), max(1, min(30, round(seg / 10))), pedido
    if re.search(r"\b(pausa|pausar|pause|para|parar|pare|continua|continuar|continue|despausa|play|da play|dar play|"
                 r"de play|retoma|retomar|volta a passar|solta)\b", f):
        return "play_pausa", 1, pedido
    return None


def controlar(acao, vezes=1, pedido=None):
    """Executa no player. Devolve a frase do que fez (ou de por que não deu)."""
    import keyboard
    hwnd, tipo = achar(pedido)
    if not hwnd:
        return f"Não achei o {NOMES.get(pedido, pedido)} aberto." if pedido else "Não achei nenhum vídeo aberto."
    tecla = _teclas(tipo, acao)
    if not tecla:
        return f"O {NOMES.get(tipo, tipo)} não tem esse comando."
    try:
        import assistente_voz as av
        if ctypes.windll.user32.GetForegroundWindow() != hwnd:
            av.trazer_janela_pra_frente(hwnd)
            time.sleep(0.35)
    except Exception:
        pass
    for _ in range(vezes):
        keyboard.send(tecla)
        time.sleep(0.08)
    global ultimo
    ultimo = (tipo, time.time())
    nome = NOMES.get(tipo, tipo)
    return {"tela_cheia": f"{nome} em tela cheia.", "sair_tela_cheia": f"{nome} fora da tela cheia.",
            "play_pausa": f"Play/pausa no {nome}.", "avancar": f"Avancei {vezes * 10} segundos.",
            "voltar": f"Voltei {vezes * 10} segundos.", "volume_mais": "Volume do vídeo mais alto.",
            "volume_menos": "Volume do vídeo mais baixo.", "mudo": "Som do vídeo ligado/desligado.",
            "proximo": "Próximo episódio.", "pular_abertura": "Pulando a abertura.",
            "inicio": "Voltei pro começo."}[acao]
