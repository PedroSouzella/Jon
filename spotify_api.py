# -*- coding: utf-8 -*-
"""
Integração com a API oficial do Spotify (precisa de conta Premium para tocar).
O Client ID fica no arquivo spotify_client_id.txt, na mesma pasta.
Na primeira vez, abre o navegador para você autorizar; depois fica salvo.
"""
import os
import re
import threading
import time
import unicodedata

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_ID = os.path.join(PASTA, "spotify_client_id.txt")
ARQ_CACHE = os.path.join(PASTA, ".spotify_token_cache")
REDIRECT = "http://127.0.0.1:8888/callback"
ESCOPOS = ("user-read-playback-state user-modify-playback-state user-read-currently-playing "
           "user-library-modify user-library-read")

_sp = None
_alvo = threading.local()          # pedido do celular -> toca no celular


def usar_celular(sim: bool):
    _alvo.celular = bool(sim)


def no_celular() -> bool:
    return getattr(_alvo, "celular", False)


class AbrirNoCelular(Exception):
    """O Spotify do celular não está aberto: o celular precisa abrir este link (depois o Jon dá o play)."""
    def __init__(self, uri, contexto=None, faixa=None, nome=""):
        super().__init__("abrir o Spotify no celular")
        self.uri, self.contexto, self.faixa, self.nome = uri, contexto, faixa, nome


def _norm(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


def client_id():
    try:
        with open(ARQ_ID, encoding="utf-8") as f:
            cid = f.read().strip()
            return cid if re.fullmatch(r"[0-9a-fA-F]{32}", cid) else None
    except OSError:
        return None


def disponivel():
    return client_id() is not None


def conectar():
    """Cria o cliente (pede login no navegador só na primeira vez)."""
    global _sp
    if _sp is not None:
        return _sp
    import spotipy
    from spotipy.oauth2 import SpotifyPKCE
    auth = SpotifyPKCE(client_id=client_id(), redirect_uri=REDIRECT, scope=ESCOPOS,
                       cache_path=ARQ_CACHE, open_browser=True)
    _sp = spotipy.Spotify(auth_manager=auth, requests_timeout=10, retries=2)
    _sp.current_user()  # força a autenticação agora
    return _sp


def _celular(sp):
    """Spotify aberto no celular (Spotify Connect), ou None."""
    devs = [d for d in sp.devices().get("devices", []) if d.get("type") == "Smartphone"]
    devs.sort(key=lambda d: not d.get("is_active"))
    return devs[0]["id"] if devs else None


def _dispositivo(sp, so_celular=False):
    """Acha o Spotify deste PC; se não estiver aberto, abre e espera aparecer.
    Pedido do celular: usa o Spotify do celular (ou, pra controles, o que estiver tocando)."""
    if no_celular():
        dev = _celular(sp)
        if dev or so_celular:
            return dev
        ativos = [d for d in sp.devices().get("devices", []) if d.get("is_active")]
        return ativos[0]["id"] if ativos else None

    def escolher():
        devs = sp.devices().get("devices", [])
        if not devs:
            return None
        for d in devs:
            if d.get("is_active"):
                return d["id"]
        for d in devs:
            if d.get("type") == "Computer":
                return d["id"]
        return devs[0]["id"]

    dev = escolher()
    if dev:
        return dev
    os.startfile("spotify:")
    for _ in range(15):
        time.sleep(1)
        dev = escolher()
        if dev:
            return dev
    return None


def tocar(busca: str, tipo: str = "auto", curtidas: bool = False) -> str:
    """
    Toca algo no Spotify. tipo: 'auto', 'musica', 'artista', 'album', 'playlist'.
    Retorna uma frase dizendo o que tocou.
    """
    sp = conectar()
    dev = _dispositivo(sp, so_celular=True)
    if not dev and not no_celular():
        raise RuntimeError("Não achei o Spotify aberto neste PC.")

    def iniciar(contexto, faixa=None, nome=""):
        if dev:
            sp.start_playback(device_id=dev, context_uri=contexto, offset={"uri": faixa} if faixa else None)
        else:
            raise AbrirNoCelular(faixa or contexto, contexto, faixa, nome)

    q = busca.strip()
    if tipo == "playlist":
        r = sp.search(q=q, type="playlist", limit=5, market="BR")
        itens = [p for p in r["playlists"]["items"] if p]
        if not itens:
            raise RuntimeError(f"Nenhuma playlist para '{q}'.")
        p = itens[0]
        iniciar(p["uri"], nome=f"playlist {p['name']}")
        return f"playlist {p['name']}"

    if tipo == "album":
        r = sp.search(q=q, type="album", limit=1, market="BR")
        itens = r["albums"]["items"]
        if not itens:
            raise RuntimeError(f"Nenhum álbum para '{q}'.")
        a = itens[0]
        iniciar(a["uri"], nome=f"álbum {a['name']}")
        return f"álbum {a['name']} - {a['artists'][0]['name']}"

    r = sp.search(q=q, type="track,artist", limit=5, market="BR")
    artistas = r["artists"]["items"]
    faixas = r["tracks"]["items"]

    # Só toca o ARTISTA se o nome bate exatamente E nenhuma música tem esse nome
    # (ex.: "Big Girls Don't Cry" é música, mesmo existindo um artista com esse nome)
    musica_com_esse_nome = any(_norm(t["name"]).startswith(_norm(q)) for t in faixas[:3])
    if tipo == "artista" or (tipo == "auto" and artistas and _norm(artistas[0]["name"]) == _norm(q)
                             and not musica_com_esse_nome):
        if artistas:
            a = artistas[0]
            if dev:
                sp.shuffle(False, device_id=dev)
            iniciar(a["uri"], nome=f"artista {a['name']}")
            return f"artista {a['name']}"

    if not faixas:
        raise RuntimeError(f"Não achei nada para '{q}'.")
    # Prefere a faixa cujo nome bate com o que você falou
    t = next((t for t in faixas if _norm(q).startswith(_norm(t["name"]).split(" (")[0])), faixas[0])

    if curtidas:
        # Toca a partir das suas Músicas Curtidas (continua nelas depois)
        try:
            uid = sp.current_user()["id"]
            iniciar(f"spotify:user:{uid}:collection", t["uri"], f"{t['name']} - {t['artists'][0]['name']}")
            return f"{t['name']} - {t['artists'][0]['name']} (nas Músicas Curtidas)"
        except AbrirNoCelular:
            raise
        except Exception as e:
            print("  (não deu pra tocar dentro das Curtidas, tocando no álbum):", e)

    # Toca a música dentro do álbum dela, assim continua tocando depois que ela acabar
    iniciar(t["album"]["uri"], t["uri"], f"{t['name']} - {t['artists'][0]['name']}")
    return f"{t['name']} - {t['artists'][0]['name']}"


def tocar_curtidas():
    """Toca as Músicas Curtidas inteiras (aleatório)."""
    sp = conectar()
    dev = _dispositivo(sp, so_celular=True)
    uid = sp.current_user()["id"]
    if not dev and no_celular():
        raise AbrirNoCelular("spotify:collection:tracks", f"spotify:user:{uid}:collection", None,
                             "Músicas Curtidas")
    sp.shuffle(True, device_id=dev)
    sp.start_playback(device_id=dev, context_uri=f"spotify:user:{uid}:collection")
    return "Músicas Curtidas (aleatório)"


def tocar_quando_celular_abrir(contexto, faixa=None, segundos=25) -> bool:
    """Espera o Spotify do celular aparecer (depois de abrir o link) e dá o play lá."""
    sp = conectar()
    for _ in range(segundos):
        time.sleep(1)
        try:
            dev = _celular(sp)
            if dev:
                if contexto and contexto.endswith(":collection") and not faixa:
                    sp.shuffle(True, device_id=dev)
                sp.start_playback(device_id=dev, context_uri=contexto, offset={"uri": faixa} if faixa else None)
                return True
        except Exception:
            pass
    return False


def controle(acao: str):
    sp = conectar()
    dev = _dispositivo(sp)
    if acao == "pausa":
        sp.pause_playback(device_id=dev)
    elif acao == "continua":
        sp.start_playback(device_id=dev)
    elif acao == "proxima":
        sp.next_track(device_id=dev)
    elif acao == "anterior":
        sp.previous_track(device_id=dev)


def volume(pct: int):
    sp = conectar()
    sp.volume(max(0, min(100, int(pct))), device_id=_dispositivo(sp))


def tocando_agora() -> str:
    sp = conectar()
    c = sp.current_playback()
    if not c or not c.get("item"):
        return "nada tocando"
    it = c["item"]
    return f"{it['name']} - {it['artists'][0]['name']}"


# ---------------------- CONTROLES EXTRAS ----------------------

def repetir(modo: str) -> str:
    """modo: 'track' (repetir a faixa), 'context' (repetir playlist/álbum) ou 'off'."""
    sp = conectar()
    sp.repeat(modo, device_id=_dispositivo(sp))
    return {"track": "Repetindo esta música", "context": "Repetindo a playlist/álbum",
            "off": "Repetição desligada"}[modo]


def aleatorio(ligar: bool) -> str:
    sp = conectar()
    sp.shuffle(bool(ligar), device_id=_dispositivo(sp))
    return "Aleatório ligado" if ligar else "Aleatório desligado"


def mudar_volume(pct=None, delta=None) -> str:
    sp = conectar()
    dev = _dispositivo(sp)
    if pct is None:
        c = sp.current_playback() or {}
        atual = (c.get("device") or {}).get("volume_percent", 50)
        pct = atual + (delta or 0)
    pct = max(0, min(100, int(pct)))
    sp.volume(pct, device_id=dev)
    return f"Volume em {pct}%"


def curtir_atual(curtir: bool = True) -> str:
    sp = conectar()
    c = sp.current_playback()
    if not c or not c.get("item"):
        return "Nada tocando agora"
    it = c["item"]
    if curtir:
        sp.current_user_saved_tracks_add([it["uri"]])
        return f"Curti {it['name']}"
    sp.current_user_saved_tracks_delete([it["uri"]])
    return f"Tirei {it['name']} das curtidas"


def adicionar_fila(busca: str) -> str:
    sp = conectar()
    r = sp.search(q=busca, type="track", limit=1, market="BR")
    itens = r["tracks"]["items"]
    if not itens:
        return f"Não achei {busca}"
    t = itens[0]
    sp.add_to_queue(t["uri"], device_id=_dispositivo(sp))
    return f"{t['name']} - {t['artists'][0]['name']} na fila"


def reiniciar_musica() -> str:
    sp = conectar()
    sp.seek_track(0, device_id=_dispositivo(sp))
    return "Do começo"


def estado():
    """Para a interface: música, tocando?, repetição, aleatório."""
    sp = conectar()
    c = sp.current_playback()
    if not c:
        return None
    return c
