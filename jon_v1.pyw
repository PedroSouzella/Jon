# -*- coding: utf-8 -*-
"""
J O N  —  V 1   (a primeira cara do Jon, recriada pra mostrar aos amigos)
Janelinha "Assistente de Voz": botão de microfone, mini player do Spotify e histórico.
Usa o mesmo "cérebro" do Jon atual (assistente_voz.py), então funciona de verdade.
Abra pelo atalho "Jon V1" (o Jon atual precisa estar fechado — os dois usam o mesmo microfone e a tecla F9).
"""
import ctypes
import json
import math
import os
import queue
import sys
import threading
import time
import traceback

PASTA = os.path.dirname(os.path.abspath(__file__))
os.chdir(PASTA)
sys.path.insert(0, PASTA)

# um Jon por vez (mesmo "cadeado" do Jon atual)
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "JonAssistente_Mutex")
if ctypes.windll.kernel32.GetLastError() == 183 or not _mutex:
    ctypes.windll.user32.MessageBoxW(0, "Feche o Jon (versão atual) antes de abrir o Jon V1.\n"
                                        "Os dois usam o mesmo microfone e a mesma tecla.", "Jon V1", 0x40)
    sys.exit(0)
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Jon.V1")
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

FILA = queue.Queue()


class Saida:
    """Tudo que o assistente 'printa' vira linha no histórico."""

    def __init__(self):
        self.buf = ""

    def write(self, txt):
        self.buf += txt
        while "\n" in self.buf:
            linha, self.buf = self.buf.split("\n", 1)
            if linha.strip():
                FILA.put(("linha", linha))

    def flush(self):
        pass


sys.stdout = sys.stderr = Saida()


def _anotar_erro(tipo, valor, tb):
    try:
        with open(os.path.join(PASTA, "jon_v1_erro.txt"), "w", encoding="utf-8") as f:
            f.write("Python: " + sys.version + "\n")
            traceback.print_exception(tipo, valor, tb, file=f)
    except Exception:
        pass


sys.excepthook = _anotar_erro

import customtkinter as ctk  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import assistente_voz as av  # noqa: E402
import spotify_api  # noqa: E402

av.ao_status = lambda estado: FILA.put(("status", estado))

# ---------- cores da V1 ----------
BG = "#121216"
CARTAO = "#1c1c22"
CARTAO2 = "#24242c"
TEXTO = "#f2f2f5"
MUDO = "#8b8b96"
VERDE = "#22c55e"
ROXO = "#8b5cf6"
ROSA = "#ec4899"
SANS = "Segoe UI"
SIMB = "Segoe UI Symbol"

STATUS = {"pronto": ("Pronto", MUDO), "ouvindo": ("Ouvindo… pode falar", ROSA),
          "processando": ("Processando…", ROXO), "erro": ("Não entendi — tente de novo", "#f87171")}


def criar_atalho():
    """Na primeira vez, cria o atalho "Jon V1" na Área de Trabalho."""
    import subprocess
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                           capture_output=True, text=True, creationflags=0x08000000)
        lnk = os.path.join(r.stdout.strip(), "Jon V1.lnk")
        if os.path.exists(lnk):
            return
        pyw = sys.executable
        if pyw.lower().endswith("python.exe"):
            pyw = pyw[:-len("python.exe")] + "pythonw.exe"
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');$s.TargetPath='{alvo}';"
              "$s.Arguments='\"{app}\"';$s.WorkingDirectory='{pasta}';$s.IconLocation='{ico}';"
              "$s.Description='Jon V1 - a primeira versão do Jon';$s.Save()").format(
            lnk=lnk, alvo=pyw, app=os.path.join(PASTA, "jon_v1.pyw"), pasta=PASTA,
            ico=os.path.join(PASTA, "assistente.ico"))
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
    except Exception:
        pass


def carregar_tecla():
    try:
        with open(os.path.join(PASTA, "config.json"), encoding="utf-8") as f:
            return json.load(f).get("tecla", "f9")
    except Exception:
        return "f9"


def botao_mic(tam, brilho=0.0):
    """O botão redondo: anel fino + círculo em degradê roxo→rosa + microfone branco (desenhado liso, sem serrilhado)."""
    s = tam * 3
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    # brilho em volta (pulsa enquanto ouve)
    if brilho > 0:
        halo = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        r = int(s * (0.46 + 0.03 * brilho))
        hd.ellipse((s // 2 - r, s // 2 - r, s // 2 + r, s // 2 + r), fill=(236, 72, 153, int(90 * brilho)))
        img = Image.alpha_composite(img, halo.filter(ImageFilter.GaussianBlur(s * 0.04)))
    d = ImageDraw.Draw(img)
    # anel
    m = int(s * 0.04)
    d.ellipse((m, m, s - m, s - m), outline=(139, 92, 246, 255), width=int(s * 0.012))
    # círculo em degradê suave (roxo no alto à esquerda -> rosa embaixo à direita)
    import numpy as np
    yy, xx = np.mgrid[0:s, 0:s]
    t = ((xx + yy) / (2.0 * (s - 1)))[..., None]
    a, b = np.array([124, 58, 237]), np.array([236, 72, 153])
    rgb = (a + (b - a) * t).astype("uint8")
    g = Image.fromarray(np.dstack([rgb, np.full((s, s, 1), 255, "uint8")]), "RGBA")
    mask = Image.new("L", (s, s), 0)
    pad = int(s * 0.10)
    ImageDraw.Draw(mask).ellipse((pad, pad, s - pad, s - pad), fill=255)
    img.paste(g, (0, 0), mask)
    # microfone
    d = ImageDraw.Draw(img)
    w = s * 0.11
    cx, cy = s / 2, s * 0.44
    d.rounded_rectangle((cx - w, cy - w * 1.9, cx + w, cy + w * 0.9), radius=w, fill="white")
    lw = int(s * 0.022)
    d.arc((cx - w * 1.75, cy - w * 1.6, cx + w * 1.75, cy + w * 1.9), start=20, end=160, fill="white", width=lw)
    d.line((cx, cy + w * 1.9, cx, cy + w * 2.7), fill="white", width=lw)
    d.line((cx - w * 0.9, cy + w * 2.7, cx + w * 0.9, cy + w * 2.7), fill="white", width=lw)
    return img.resize((tam, tam), Image.LANCZOS)


class JonV1(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.tecla = carregar_tecla()
        av.TECLA_FALAR = self.tecla
        self.motor = av.Motor(self.tecla)
        self.title("Jon V1 — Assistente de Voz")
        self.geometry("380x640+60+40")
        self.minsize(340, 560)
        self.configure(fg_color=BG)
        try:
            self.iconbitmap(os.path.join(PASTA, "assistente.ico"))
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.sair)
        self.estado = "pronto"
        self._fase = 0.0
        self._ultimo_bloco = None
        self._montar()
        self.motor.ligar_tecla(self.tecla)
        av.preparar_voz()
        threading.Thread(target=self._spotify, daemon=True).start()
        threading.Thread(target=criar_atalho, daemon=True).start()
        self.after(40, self._loop)

    # ---------------- tela ----------------
    def _montar(self):
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=20, pady=(16, 0))
        l = ctk.CTkFrame(topo, fg_color="transparent")
        l.pack(fill="x")
        ctk.CTkLabel(l, text="Assistente de Voz", font=(SANS, 20, "bold"), text_color=TEXTO).pack(side="left")
        ctk.CTkLabel(l, text="V1", font=(SANS, 10, "bold"), text_color=BG, fg_color=ROXO, corner_radius=8,
                     width=28, height=18).pack(side="left", padx=8, pady=(4, 0))
        ctk.CTkLabel(topo, text=f"Segure  {self.tecla.upper()}  e fale  •  ou clique no microfone", font=(SANS, 11),
                     text_color=MUDO, anchor="w").pack(fill="x")

        self.imgs = {k: ctk.CTkImage(botao_mic(120, k / 10), size=(120, 120)) for k in range(0, 11, 2)}
        self.bt_mic = ctk.CTkLabel(self, text="", image=self.imgs[0], cursor="hand2")
        self.bt_mic.pack(pady=(18, 4))
        self.bt_mic.bind("<Button-1>", lambda e: self.clicou_mic())
        self.lbl_status = ctk.CTkLabel(self, text="Pronto", font=(SANS, 13), text_color=MUDO)
        self.lbl_status.pack()
        self.nivel = ctk.CTkProgressBar(self, width=120, height=4, corner_radius=2, fg_color=CARTAO2,
                                        progress_color=ROSA)
        self.nivel.set(0.03)
        self.nivel.pack(pady=(6, 12))

        sp = ctk.CTkFrame(self, fg_color=CARTAO, corner_radius=10)
        sp.pack(fill="x", padx=14)
        l = ctk.CTkFrame(sp, fg_color="transparent")
        l.pack(fill="x", padx=12, pady=(10, 0))
        self.ponto_sp = ctk.CTkLabel(l, text="●", text_color=MUDO, font=(SANS, 10), width=12)
        self.ponto_sp.pack(side="left")
        self.lbl_sp = ctk.CTkLabel(l, text="Conectando ao Spotify…", font=(SANS, 11, "bold"), text_color=TEXTO)
        self.lbl_sp.pack(side="left", padx=4)
        self.lbl_tocando = ctk.CTkLabel(sp, text="", font=(SANS, 10), text_color=MUDO, anchor="w")
        self.lbl_tocando.pack(fill="x", padx=14)
        bts = ctk.CTkFrame(sp, fg_color="transparent")
        bts.pack(pady=(4, 10))
        for txt, acao in (("⏮", "anterior"), ("⏯", "pausa_play"), ("⏭", "proxima")):
            ctk.CTkButton(bts, text=txt, width=44, height=26, corner_radius=6, fg_color=CARTAO2, hover_color="#30303a",
                          text_color=TEXTO, font=(SIMB, 12), command=lambda a=acao: self.spotify_ctrl(a)).pack(
                side="left", padx=4)

        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(h, text="Histórico", font=(SANS, 13, "bold"), text_color=TEXTO).pack(side="left")
        ctk.CTkButton(h, text="Limpar", width=50, height=22, fg_color="transparent", hover_color=CARTAO,
                      text_color=MUDO, font=(SANS, 11), command=self.limpar).pack(side="right")
        self.hist = ctk.CTkScrollableFrame(self, fg_color=CARTAO, corner_radius=10)
        self.hist.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.dica = ctk.CTkLabel(self.hist, text=f"Segure a tecla ({self.tecla.upper()}) ou clique no microfone e fale.\n"
                                                 "Ex.: “toca Coldplay”, “abre o Discord”, “que horas são”.",
                                 font=(SANS, 11), text_color=MUDO, justify="left", anchor="w")
        self.dica.pack(fill="x", padx=6, pady=6)

    # ---------------- ações ----------------
    def clicou_mic(self):
        if self.motor.gravando():
            self.motor.soltar()
        else:
            self.motor.comecar()

    def spotify_ctrl(self, acao):
        def run():
            try:
                if acao == "pausa_play":
                    c = spotify_api.conectar().current_playback()
                    spotify_api.controle("pausa" if c and c.get("is_playing") else "continua")
                else:
                    spotify_api.controle(acao)
                time.sleep(0.6)
                self._ler_spotify()
            except Exception:
                import keyboard
                keyboard.send({"anterior": "previous track", "proxima": "next track"}.get(acao, "play/pause media"))
        threading.Thread(target=run, daemon=True).start()

    def limpar(self):
        for w in self.hist.winfo_children():
            w.destroy()
        self._ultimo_bloco = None

    def sair(self):
        try:
            self.motor.desligar_tecla()
        except Exception:
            pass
        self.destroy()
        os._exit(0)

    # ---------------- histórico ----------------
    def _novo_bloco(self, frase):
        if self.dica.winfo_exists():
            self.dica.destroy()
        b = ctk.CTkFrame(self.hist, fg_color="transparent")
        b.pack(fill="x", padx=4, pady=(6, 2))
        l = ctk.CTkFrame(b, fg_color="transparent")
        l.pack(fill="x")
        ctk.CTkLabel(l, text="🎙", font=(SIMB, 11), text_color=MUDO, width=16).pack(side="left", anchor="n")
        ctk.CTkLabel(l, text=frase, font=(SANS, 13, "bold"), text_color=TEXTO, anchor="w", justify="left",
                     wraplength=230).pack(side="left", padx=(2, 6))
        ctk.CTkLabel(l, text=time.strftime("%H:%M"), font=(SANS, 9), text_color=MUDO).pack(side="left", anchor="n",
                                                                                           pady=(3, 0))
        self._ultimo_bloco = b
        self.after(50, lambda: self.hist._parent_canvas.yview_moveto(1.0))

    def _linha(self, texto, cor):
        if self._ultimo_bloco is None:
            self._novo_bloco("…")
        ctk.CTkLabel(self._ultimo_bloco, text=texto, font=(SANS, 11), text_color=cor, anchor="w", justify="left",
                     wraplength=290).pack(fill="x", padx=(20, 0))
        self.after(50, lambda: self.hist._parent_canvas.yview_moveto(1.0))

    def _tratar(self, l):
        l = l.strip()
        if not l or l.startswith(("=", "🎙", "Conectando", "Spotify conectado", "Modo mãos", "(mãos-livres",
                                  "(ouvi", "🧠", "(IA:", "Página do", "Servidor do")):
            return
        if l.startswith("Você disse"):
            self._novo_bloco(l.split(":", 1)[1].strip().strip('"'))
        elif l.startswith("->"):
            self._linha("→ " + l[2:].strip(), VERDE)
        elif l.startswith("💬"):
            self._linha(l[1:].strip(), "#c4b5fd")
        elif l.startswith(("Traceback", "File ")):
            return
        else:
            self._linha(l.strip("() "), MUDO)

    # ---------------- spotify ----------------
    def _spotify(self):
        ok = av.conectar_spotify()
        FILA.put(("spotify", ok))
        while ok:
            self._ler_spotify()
            time.sleep(6)

    def _ler_spotify(self):
        try:
            c = spotify_api.conectar().current_playback()
            if c and c.get("item"):
                it = c["item"]
                FILA.put(("tocando", f"{'►' if c.get('is_playing') else '❚❚'}  {it['name']} — {it['artists'][0]['name']}"))
            else:
                FILA.put(("tocando", "Nada tocando agora"))
        except Exception:
            pass

    # ---------------- loop ----------------
    def _loop(self):
        try:
            while True:
                tipo, val = FILA.get_nowait()
                if tipo == "linha":
                    self._tratar(val)
                elif tipo == "status":
                    self.estado = val
                    txt, cor = STATUS.get(val, STATUS["pronto"])
                    self.lbl_status.configure(text=txt, text_color=cor)
                    if val == "erro":
                        self.after(2500, lambda: FILA.put(("status", "pronto")) if self.estado == "erro" else None)
                elif tipo == "spotify":
                    self.ponto_sp.configure(text_color=VERDE if val else "#f87171")
                    self.lbl_sp.configure(text="Spotify conectado" if val else "Spotify: só pesquisa")
                elif tipo == "tocando":
                    self.lbl_tocando.configure(text=val[:52])
        except queue.Empty:
            pass
        # botão pulsa enquanto ouve; barrinha mostra o volume da voz
        self._fase += 0.15
        if self.motor.gravando():
            nivel = min(1.0, getattr(self.motor.gravador, "nivel", 0.0) * 1.4)
            self.nivel.set(max(0.03, nivel))
            k = int(round((0.5 + 0.5 * math.sin(self._fase)) * 5)) * 2
            self.bt_mic.configure(image=self.imgs[k])
        elif self.estado == "processando":
            self.nivel.set(0.3 + 0.3 * math.sin(self._fase))
            self.bt_mic.configure(image=self.imgs[2])
        else:
            self.nivel.set(0.03)
            self.bt_mic.configure(image=self.imgs[0])
        self.after(50, self._loop)


if __name__ == "__main__":
    try:
        with open(os.path.join(PASTA, "jon_v1_erro.txt"), "w", encoding="utf-8") as f:
            f.write("iniciou " + time.strftime("%H:%M:%S") + "\n")
    except Exception:
        pass
    try:
        JonV1().mainloop()
    except Exception:
        try:
            with open(os.path.join(PASTA, "jon_v1_erro.txt"), "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        ctypes.windll.user32.MessageBoxW(0, "O Jon V1 fechou por um erro.", "Jon V1", 0x10)
