# -*- coding: utf-8 -*-
"""
Atualizador do Jon: confere o GitHub e instala versões novas do código.
- Fonte: o projeto principal (ou o seu fork: config.json -> "repo_atualizacao": "usuario/Jon").
- Também avisa quando o repositório original (de onde o seu é fork) tem novidades.
- Antes de instalar, guarda uma cópia do código atual em backups/.
- NUNCA mexe nos seus dados (memória, config, e-mail, Spotify, rotinas, logs).
"""
import io
import json
import os
import shutil
import time
import urllib.request
import zipfile

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_ESTADO = os.path.join(PASTA, "atualizacao.json")
ARQ_CONFIG = os.path.join(PASTA, "config.json")
REPO_PADRAO = "Sabadini25/Jon"          # projeto principal; um fork usa config.json -> "repo_atualizacao"
EXTENSOES = (".py", ".pyw", ".bat", ".ps1", ".ico", ".png", ".jpg", ".svg", ".html", ".css", ".js", ".json", ".txt",
             ".md", ".mp3", ".wav", ".xml", ".java")
PROTEGIDOS = {"config.json", "memoria.json", "memoria.json.tmp", "rotinas.json", "recentes.json",
              "email_config.json", "spotify_client_id.txt", ".spotify_token_cache", "atualizacao.json",
              "assistente.log", "tailscale_status.txt", "tailscale_serve.txt", ".gitignore"}
UA = {"User-Agent": "Jon-atualizador", "Accept": "application/vnd.github+json"}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _json(url):
    return json.loads(_get(url).decode("utf-8"))


def repo():
    try:
        with open(ARQ_CONFIG, encoding="utf-8") as f:
            return json.load(f).get("repo_atualizacao") or REPO_PADRAO
    except Exception:
        return REPO_PADRAO


def estado():
    try:
        with open(ARQ_ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_estado(d):
    with open(ARQ_ESTADO, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def checar():
    """{'disponivel', 'sha', 'mensagem', 'data', 'repo', 'original', 'original_novo', 'original_msg'}"""
    r = repo()
    info = _json(f"https://api.github.com/repos/{r}")
    ramo = info.get("default_branch", "main")
    c = _json(f"https://api.github.com/repos/{r}/commits/{ramo}")
    sha = c["sha"]
    est = estado()
    if not est.get("sha"):                       # primeira vez: considera que a versão atual é a do GitHub
        est = {"sha": sha, "instalado_em": time.strftime("%d/%m/%Y %H:%M")}
        _salvar_estado(est)
    res = {"repo": r, "ramo": ramo, "sha": sha, "disponivel": sha != est.get("sha"),
           "mensagem": c["commit"]["message"].strip().split("\n")[0][:120],
           "data": c["commit"]["committer"]["date"][:10], "original": None, "original_novo": False,
           "original_msg": ""}
    pai = (info.get("parent") or {}).get("full_name")
    if pai:                                      # novidades no repositório original (do amigo)?
        try:
            p_info = _json(f"https://api.github.com/repos/{pai}")
            p_ramo = p_info.get("default_branch", "main")
            pc = _json(f"https://api.github.com/repos/{pai}/commits/{p_ramo}")
            res["original"] = pai
            if pc["sha"] != sha:
                try:
                    cmp_ = _json(f"https://api.github.com/repos/{pai}/compare/{sha}...{pc['sha']}")
                    res["original_novo"] = cmp_.get("ahead_by", 1) > 0
                except Exception:
                    res["original_novo"] = True
                res["original_msg"] = pc["commit"]["message"].strip().split("\n")[0][:120]
        except Exception:
            pass
    return res


def aplicar(sha=None):
    """Baixa a versão do GitHub e instala por cima do código (com backup). Devolve a lista de arquivos trocados."""
    r = repo()
    if not sha:
        info = _json(f"https://api.github.com/repos/{r}")
        sha = _json(f"https://api.github.com/repos/{r}/commits/{info.get('default_branch', 'main')}")["sha"]
    dados = _get(f"https://codeload.github.com/{r}/zip/{sha}", timeout=60)
    z = zipfile.ZipFile(io.BytesIO(dados))
    raiz = z.namelist()[0].split("/")[0] + "/"
    novos = {}
    for nome in z.namelist():
        if nome.endswith("/") or not nome.startswith(raiz):
            continue
        rel = nome[len(raiz):]
        base = os.path.basename(rel)
        if not rel or base in PROTEGIDOS or rel.startswith((".git", "backups/")) or not base.lower().endswith(EXTENSOES):
            continue
        if ".." in rel.split("/"):
            continue
        novos[rel] = z.read(nome)
    if "app.pyw" not in novos or "assistente_voz.py" not in novos:
        raise RuntimeError("o pacote do GitHub não parece ser o Jon (faltam arquivos principais)")
    # backup do código atual
    pasta_bkp = os.path.join(PASTA, "backups", time.strftime("%Y%m%d-%H%M%S"))
    trocados = []
    for rel, conteudo in novos.items():
        destino = os.path.join(PASTA, *rel.split("/"))
        antigo = None
        if os.path.exists(destino):
            with open(destino, "rb") as f:
                antigo = f.read()
            if antigo == conteudo:
                continue
            copia = os.path.join(pasta_bkp, *rel.split("/"))
            os.makedirs(os.path.dirname(copia), exist_ok=True)
            shutil.copy2(destino, copia)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        tmp = destino + ".novo"
        with open(tmp, "wb") as f:
            f.write(conteudo)
        os.replace(tmp, destino)
        trocados.append(rel)
    _salvar_estado({"sha": sha, "instalado_em": time.strftime("%d/%m/%Y %H:%M"), "backup": pasta_bkp,
                    "arquivos": trocados})
    return trocados


def reiniciar_jon():
    """Abre o Jon de novo daqui a 3 s (o app atual fecha logo depois de chamar isto)."""
    import subprocess
    import sys
    pyw = sys.executable
    if pyw.lower().endswith("python.exe"):
        pyw = pyw[:-len("python.exe")] + "pythonw.exe"
    app = os.path.join(PASTA, "app.pyw")
    subprocess.Popen(f'cmd /c timeout /t 3 /nobreak >nul & start "" "{pyw}" "{app}"', shell=True,
                     creationflags=0x08000000, cwd=PASTA)
