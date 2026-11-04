# -*- coding: utf-8 -*-
"""
Servidor do Jon para o celular.
Escuta SÓ no próprio PC (127.0.0.1:8765). Quem leva até o celular, com HTTPS e de forma privada,
é o Tailscale ("tailscale serve"). Nada fica aberto para a internet.
"""
import json
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PASTA = os.path.dirname(os.path.abspath(__file__))
PORTA = 8765
_trava = threading.Lock()          # um comando por vez
av = None                          # o módulo assistente_voz (o app passa)
ao_pedido = None                   # callback do app (mostra no registro / anima o núcleo)


def _arquivo(nome):
    with open(os.path.join(PASTA, "web", nome), "rb") as f:
        return f.read()


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
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        rotas = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/manifest.json": ("manifest.json", "application/manifest+json"),
                 "/icone-192.png": ("icone-192.png", "image/png"),
                 "/icone-512.png": ("icone-512.png", "image/png"),
                 "/icone-esfera-180.png": ("icone-esfera-180.png", "image/png"),
                 "/icone-esfera-192.png": ("icone-esfera-192.png", "image/png"),
                 "/icone-esfera-512.png": ("icone-esfera-512.png", "image/png"),
                 "/apple-touch-icon.png": ("icone-esfera-180.png", "image/png"),
                 "/favicon.ico": ("icone-esfera-192.png", "image/png")}
        if self.path.split("?")[0] in rotas:
            nome, tipo = rotas[self.path.split("?")[0]]
            try:
                return self._resp(200, _arquivo(nome), tipo, cache=nome.endswith(".png"))
            except OSError:
                return self._resp(404, {"erro": "arquivo não encontrado"})
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
            srv = ThreadingHTTPServer(("127.0.0.1", PORTA), Handler)
            srv.daemon_threads = True
            print(f"Página do celular pronta (porta {PORTA}).")
            srv.serve_forever()
        except OSError as e:
            print("  Não consegui abrir o servidor do celular:", e)
    threading.Thread(target=rodar, daemon=True).start()
