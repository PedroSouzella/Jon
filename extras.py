# -*- coding: utf-8 -*-
"""Hora/data, clima (Open-Meteo, grátis e sem chave), briefing do dia e ações da área de trabalho."""
import datetime as dt
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

import perfil


def cidade_padrao():
    return perfil.cidade()

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
TEMPO_COD = {0: "céu limpo", 1: "quase limpo", 2: "parcialmente nublado", 3: "nublado", 45: "neblina", 48: "neblina",
             51: "garoa fraca", 53: "garoa", 55: "garoa forte", 61: "chuva fraca", 63: "chuva", 65: "chuva forte",
             71: "neve fraca", 73: "neve", 75: "neve forte", 80: "pancadas de chuva fracas", 81: "pancadas de chuva",
             82: "pancadas de chuva fortes", 95: "trovoadas", 96: "trovoadas com granizo", 99: "trovoadas com granizo"}


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Jon-assistente/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------- hora / data ----------------------

def hora_texto():
    a = dt.datetime.now()
    return f"São {a.hour} horas e {a.minute} minutos." if a.minute else f"São {a.hour} horas em ponto."


def data_texto():
    a = dt.date.today()
    return f"Hoje é {SEMANA[a.weekday()]}, {a.day} de {MESES[a.month - 1]} de {a.year}."


def saudacao():
    h = dt.datetime.now().hour
    return "Bom dia" if 5 <= h < 12 else "Boa tarde" if 12 <= h < 18 else "Boa noite"


# ---------------------- clima ----------------------

def _geocodificar(cidade):
    r = _get("https://geocoding-api.open-meteo.com/v1/search?count=1&language=pt&name=" + urllib.parse.quote(cidade))
    res = (r.get("results") or [None])[0]
    if not res:
        return None
    return res["name"], res["latitude"], res["longitude"]


def clima(cidade: str = "", amanha: bool = False) -> str:
    local = cidade_padrao()
    if cidade:
        g = _geocodificar(cidade)
        if not g:
            return f"Não encontrei a cidade {cidade}."
        local = g
    nome, lat, lon = local
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,apparent_temperature,weather_code,relative_humidity_2m"
           "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
           "&timezone=America%2FSao_Paulo&forecast_days=2")
    d = _get(url)
    i = 1 if amanha else 0
    mx, mn = round(d["daily"]["temperature_2m_max"][i]), round(d["daily"]["temperature_2m_min"][i])
    chuva = d["daily"]["precipitation_probability_max"][i]
    cond = TEMPO_COD.get(d["daily"]["weather_code"][i], "tempo variável")
    if amanha:
        return f"Amanhã em {nome}: {cond}, mínima de {mn} e máxima de {mx} graus, {chuva}% de chance de chuva."
    c = d["current"]
    agora = TEMPO_COD.get(c["weather_code"], "tempo variável")
    return (f"Agora em {nome}: {round(c['temperature_2m'])} graus, {agora}. "
            f"Hoje mínima de {mn} e máxima de {mx}, {chuva}% de chance de chuva.")


# ---------------------- área de trabalho ----------------------

def _pasta_conhecida(nome):
    guid = {"downloads": "{374DE290-123F-4565-9164-39C4925E467B}"}
    if nome in guid:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                return os.path.expandvars(winreg.QueryValueEx(k, guid[nome])[0])
        except Exception:
            pass
    r = subprocess.run(["powershell", "-NoProfile", "-Command", f"[Environment]::GetFolderPath('{nome}')"],
                       capture_output=True, text=True, creationflags=0x08000000)
    return r.stdout.strip()


PASTAS = {
    "downloads": "downloads", "download": "downloads", "baixados": "downloads",
    "documentos": "MyDocuments", "documento": "MyDocuments",
    "imagens": "MyPictures", "fotos": "MyPictures", "musicas": "MyMusic", "videos": "MyVideos",
    "area de trabalho": "Desktop", "desktop": "Desktop",
}


def abrir_pasta(nome: str) -> str:
    n = nome.strip().lower()
    m = re.match(r"^(disco|drive|unidade)\s+([a-z])$", n) or re.match(r"^([a-z])$", n)
    if m:
        letra = m.groups()[-1].upper()
        os.startfile(f"{letra}:\\")
        return f"Abrindo o disco {letra}."
    if n in ("jon", "do jon", "assistente"):
        os.startfile(os.path.dirname(os.path.abspath(__file__)))
        return "Abrindo a pasta do Jon."
    for chave, especial in PASTAS.items():
        if n == chave or n.endswith(" " + chave):
            os.startfile(_pasta_conhecida(especial))
            return f"Abrindo {chave}."
    return ""


def print_tela() -> str:
    import keyboard
    keyboard.send("windows+print screen")
    return "Print salvo na pasta Imagens, em Capturas de Tela."


PROCESSOS = {"spotify": "Spotify.exe", "discord": "Discord.exe", "steam": "steam.exe", "chrome": "chrome.exe",
             "google chrome": "chrome.exe", "edge": "msedge.exe", "bloco de notas": "notepad.exe",
             "calculadora": "CalculatorApp.exe", "obs": "obs64.exe", "word": "WINWORD.EXE", "excel": "EXCEL.EXE",
             "powerpoint": "POWERPNT.EXE", "vs code": "Code.exe", "vscode": "Code.exe", "hydra": "Hydra.exe",
             "obsidian": "Obsidian.exe", "stremio": "stremio.exe", "utorrent": "uTorrent.exe"}


def _fechar_por_janela(n: str):
    """Acha a janela aberta com título parecido (ex.: 'assassins creed mirrage') e pede pra ela fechar."""
    import difflib
    import unicodedata
    try:
        import pygetwindow as gw
    except Exception:
        return None
    def norm(t):
        t = unicodedata.normalize("NFKD", t.lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()
    alvo = norm(n)
    melhor, nota_m = None, 0.0
    for w in gw.getAllWindows():
        t = norm(w.title or "")
        if not t or t in ("jon", "program manager"):
            continue
        nota = difflib.SequenceMatcher(None, alvo, t).ratio()
        pals = alvo.split()
        if pals and all(any(difflib.SequenceMatcher(None, p, q).ratio() >= 0.8 for q in t.split()) for p in pals):
            nota = max(nota, 0.9)
        if nota > nota_m:
            melhor, nota_m = w, nota
    if melhor is None or nota_m < 0.78:
        return None
    try:
        melhor.close()
        return f"Fechando {melhor.title}."
    except Exception:
        return None


def fechar_app(nome: str) -> str:
    n = re.sub(r"^(o|a)\s+", "", nome.strip().lower())
    n = re.sub(r"^(aplicativo|app|programa|jogo|game)\s+(do\s+|da\s+)?", "", n).strip()
    exe = PROCESSOS.get(n)
    if not exe:
        return _fechar_por_janela(n) or f"Não achei {n} aberto."
    # sem /F: pede pro programa fechar normalmente (ele pode perguntar se quer salvar)
    r = subprocess.run(["taskkill", "/IM", exe], capture_output=True, text=True, creationflags=0x08000000)
    return f"Fechando {n}." if r.returncode == 0 else f"{n.capitalize()} não estava aberto."


def minimizar_tudo() -> str:
    import keyboard
    keyboard.send("windows+d")
    return "Área de trabalho."


def bloquear_pc() -> str:
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return "Bloqueando o computador."
