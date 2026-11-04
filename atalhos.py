# -*- coding: utf-8 -*-
"""Cria/remove os atalhos do Jon (Área de Trabalho e Iniciar com o Windows)."""
import os
import subprocess
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(PASTA, "app.pyw")
ICONE = os.path.join(PASTA, "assistente.ico")
NOME = "Jon.lnk"
NOME_ANTIGO = "Assistente de Voz.lnk"


def _pythonw():
    exe = sys.executable
    pw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return pw if os.path.exists(pw) else exe


def _pasta_especial(nome):
    # Desktop pode estar no OneDrive; o PowerShell devolve o caminho certo.
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"[Environment]::GetFolderPath('{nome}')"],
                       capture_output=True, text=True, creationflags=0x08000000)
    return r.stdout.strip()


def criar(destino_pasta):
    antigo = os.path.join(destino_pasta, NOME_ANTIGO)
    if os.path.exists(antigo):
        try:
            os.remove(antigo)
        except OSError:
            pass
    lnk = os.path.join(destino_pasta, NOME)
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath='{alvo}';$s.Arguments='\"{app}\"';"
        "$s.WorkingDirectory='{pasta}';$s.IconLocation='{icone}';"
        "$s.Description='Jon - assistente de voz';$s.Save()"
    ).format(lnk=lnk, alvo=_pythonw(), app=APP, pasta=PASTA, icone=ICONE)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
    return lnk


def area_de_trabalho():
    return criar(_pasta_especial("Desktop"))


def pasta_inicializar():
    return _pasta_especial("Startup")


def iniciar_com_windows(ligar: bool):
    pasta = pasta_inicializar()
    lnk = os.path.join(pasta, NOME)
    if ligar:
        criar(pasta)
    elif os.path.exists(lnk):
        os.remove(lnk)


def migrar_nome():
    """Troca atalhos antigos 'Assistente de Voz' por 'Jon' (Área de Trabalho e Inicializar)."""
    for nome in ("Desktop", "Startup"):
        try:
            pasta = _pasta_especial(nome)
            if os.path.exists(os.path.join(pasta, NOME_ANTIGO)):
                criar(pasta)
        except Exception:
            pass


def inicia_com_windows() -> bool:
    try:
        return os.path.exists(os.path.join(pasta_inicializar(), NOME))
    except Exception:
        return False


if __name__ == "__main__":
    print("Atalho criado em:", area_de_trabalho())
