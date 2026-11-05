# -*- coding: utf-8 -*-
"""
Servidor do Jon para o celular.
Escuta SÓ no próprio PC (127.0.0.1:8765). Quem leva até o celular, com HTTPS e de forma privada,
é o Tailscale ("tailscale serve"). Nada fica aberto para a internet.
"""
import asyncio
import json
import re
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PASTA = os.path.dirname(os.path.abspath(__file__))
PORTA = 8765
_trava = threading.Lock()          # um comando por vez
_tts_cache = {}                    # cache de áudio neural JARVIS (texto -> bytes mp3)
av = None                          # o módulo assistente_voz (o app passa)
ao_pedido = None                   # callback do app (mostra no registro / anima o núcleo)


def _gerar_tts_jarvis(texto: str) -> bytes:
    texto = (texto or "").strip()[:450]
    if not texto:
        return b""
    if texto in _tts_cache:
        return _tts_cache[texto]
    try:
        import edge_tts

        async def _sintetizar():
            com = edge_tts.Communicate(texto, voice="pt-BR-AntonioNeural", rate="+6%", pitch="-4Hz")
            partes = []
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    partes.append(chunk["data"])
            return b"".join(partes)

        audio = asyncio.run(_sintetizar())
        if audio:
            if len(_tts_cache) > 80:
                _tts_cache.clear()
            _tts_cache[texto] = audio
        return audio
    except Exception:
        return b""


def _arquivo(nome):
    with open(os.path.join(PASTA, "web", nome), "rb") as f:
        return f.read()


def _config():
    try:
        with open(os.path.join(PASTA, "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def rede_local() -> bool:
    """Só abre o servidor pra rede da casa se você ligar isso no config.json ("servidor_rede_local": true)."""
    return bool(_config().get("servidor_rede_local"))


def modo_carro() -> bool:
    """Central multimídia do carro. Desligue com "modo_carro": false no config.json."""
    return _config().get("modo_carro", True) is not False


def _host_ok(h: str) -> bool:
    """Só aceita pedidos endereçados ao próprio PC ou ao Tailscale (bloqueia sites tentando mandar comandos)."""
    h = (h or "").lower().split(":")[0].strip("[]")
    if h in ("127.0.0.1", "localhost", "::1") or h.endswith(".ts.net"):
        return True
    if rede_local() and re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", h):
        return True
    return False


class Handler(BaseHTTPRequestHandler):
    server_version = "Jon/1.0"

    def log_message(self, *a):
        pass                       # sem poluir o registro

    def _resp(self, codigo, corpo, tipo="application/json; charset=utf-8", cache=False):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        elif isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        origem = self.headers.get("Origin", "")
        if origem and _host_ok(urllib.parse.urlsplit(origem).netloc):     # nada de "*": só as páginas do próprio Jon
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-store")
        self.end_headers()
        try:
            self.wfile.write(corpo)
        except OSError:
            pass

    def _seguro(self) -> bool:
        """Bloqueia pedidos de outros sites (CSRF) e de nomes estranhos (DNS rebinding)."""
        if not _host_ok(self.headers.get("Host", "")):
            return False
        origem = self.headers.get("Origin", "")
        if origem and origem != "null" and not _host_ok(urllib.parse.urlsplit(origem).netloc):
            return False
        return True

    def do_OPTIONS(self):
        if not self._seguro():
            return self._resp(403, {"erro": "origem não permitida"})
        self._resp(200, b"", "text/plain")

    def do_GET(self):
        caminho = self.path.split("?")[0]
        if not self._seguro():
            return self._resp(403, {"erro": "origem não permitida"})
        rotas = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/carro": ("carro.html", "text/html; charset=utf-8"),
                 "/carro.html": ("carro.html", "text/html; charset=utf-8"),
                 "/manifest.json": ("manifest.json", "application/manifest+json"),
                 "/manifest-carro.json": ("manifest-carro.json", "application/manifest+json"),
                 "/bem_vindo.mp3": ("bem_vindo.mp3", "audio/mpeg"),
                 "/camera_re.mp3": ("camera_re.mp3", "audio/mpeg"),
                 "/icone-192.png": ("icone-192.png", "image/png"),
                 "/icone-512.png": ("icone-512.png", "image/png"),
                 "/icone-esfera-180.png": ("icone-esfera-180.png", "image/png"),
                 "/icone-esfera-192.png": ("icone-esfera-192.png", "image/png"),
                 "/icone-esfera-512.png": ("icone-esfera-512.png", "image/png"),
                 "/apple-touch-icon.png": ("icone-esfera-180.png", "image/png"),
                 "/favicon.ico": ("icone-esfera-192.png", "image/png")}
        if not modo_carro() and ("carro" in caminho or caminho in ("/bem_vindo.mp3", "/camera_re.mp3")):
            return self._resp(404, {"erro": "modo carro desligado"})
        if caminho in rotas:
            nome, tipo = rotas[caminho]
            if nome == "index.html" and not modo_carro():
                try:                      # tira o botão do modo carro da página do celular
                    html = _arquivo(nome).decode("utf-8")
                    html = re.sub(r'<a href="/carro"[^>]*>.*?</a>', "", html, flags=re.S)
                    return self._resp(200, html, tipo)
                except OSError:
                    return self._resp(404, {"erro": "arquivo não encontrado"})
            try:
                return self._resp(200, _arquivo(nome), tipo, cache=nome.endswith((".png", ".mp3")))
            except OSError:
                return self._resp(404, {"erro": "arquivo não encontrado"})
        if caminho == "/api/tts":
            qs = urllib.parse.parse_qs( urllib.parse.urlsplit(self.path).query )
            txt = (qs.get("texto") or [""])[0]
            audio = _gerar_tts_jarvis(txt)
            if audio:
                return self._resp(200, audio, "audio/mpeg", cache=False)
            return self._resp(404, {"erro": "tts indisponível"})
        if self.path == "/api/acordar":
            try:
                av.ia_local.aquecer_async()
            except Exception:
                pass
            return self._resp(200, {"ok": True})
        if self.path == "/api/estado":
            info = {"hora": time.strftime("%H:%M"), "ia": False, "tocando": ""}
            try:
                info["ia"] = av.ia_local.disponivel()
            except Exception:
                pass
            try:
                info["tocando"] = av.spotify_api.tocando_agora() if av.spotify_api.disponivel() else ""
            except Exception:
                pass
            return self._resp(200, info)
        self._resp(404, {"erro": "não existe"})

    def do_POST(self):
        caminho = self.path.split("?")[0]
        if not self._seguro():
            return self._resp(403, {"erro": "origem não permitida"})
        if caminho not in ("/api/comando", "/api/atalho"):
            return self._resp(404, {"erro": "não existe"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            bruto = self.rfile.read(min(n, 4000)).decode("utf-8", "ignore")
            tipo = self.headers.get("Content-Type", "")
            if "json" in tipo:
                corpo = json.loads(bruto or "{}")
            elif "form" in tipo:
                corpo = {k: v[0] for k, v in urllib.parse.parse_qs(bruto).items()}
            else:                                   # texto puro (app Atalhos)
                corpo = {"texto": bruto}
            texto = str(corpo.get("texto", "")).strip()
            destino = "pc" if str(corpo.get("destino", "")).lower() in ("pc", "computador") else "celular"
        except Exception:
            return self._resp(400, {"erro": "pedido inválido"})
        if not texto:
            return self._resp(400, {"erro": "texto vazio"})
        with _trava:
            if ao_pedido:
                ao_pedido("processando")
            try:
                r = av.executar_remoto(texto[:500], destino)
            finally:
                if ao_pedido:
                    ao_pedido("pronto")
        if caminho == "/api/atalho":
            # formato simples pro app Atalhos do iPhone (toque duplo atrás)
            links = r.get("abrir") or []
            return self._resp(200, {"resposta": r.get("resposta", ""), "abrir": links[0]["url"] if links else ""})
        self._resp(200, r)


def iniciar():
    def rodar():
        try:
            # padrão: só o próprio PC (o celular chega pelo Tailscale). Rede da casa só se ligar no config.json.
            srv = ThreadingHTTPServer(("0.0.0.0" if rede_local() else "127.0.0.1", PORTA), Handler)
            srv.daemon_threads = True
            print(f"Servidor do Jon pronto (porta {PORTA})" + (" • modo carro ligado." if modo_carro() else "."))
            srv.serve_forever()
        except OSError as e:
            print("  Não consegui abrir o servidor:", e)
    threading.Thread(target=rodar, daemon=True).start()


if __name__ == "__main__":
    import assistente_voz
    av = assistente_voz
    av.conectar_spotify()
    iniciar()
    print(f"Jon Car OS ativo em http://127.0.0.1:{PORTA}/carro")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
