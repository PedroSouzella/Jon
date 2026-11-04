# -*- coding: utf-8 -*-
"""
Pesquisa na internet de verdade (sem chave de API):
1) busca no DuckDuckGo  2) lê o começo das 2 melhores páginas  3) a IA local resume em português.
Se a IA estiver desligada, devolve os trechos dos resultados.
"""
import html
import time
import json
import re
import threading
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0 Safari/537.36")


def _get(url, timeout=6, dados=None):
    req = urllib.request.Request(url, data=dados, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        bruto = r.read(600_000)
        cs = r.headers.get_content_charset() or "utf-8"
    return bruto.decode(cs, "ignore")


def _limpo(t):
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def buscar(consulta, n=5):
    """Lista de {titulo, url, trecho}."""
    pag = _get("https://html.duckduckgo.com/html/", dados=urllib.parse.urlencode(
        {"q": consulta, "kl": "br-pt"}).encode())
    res = []
    blocos = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)',
                        pag, flags=re.S)
    for href, titulo, resto in blocos:
        m = re.search(r"uddg=([^&]+)", href)
        url = urllib.parse.unquote(m.group(1)) if m else href
        if "duckduckgo.com/y.js" in url or url.startswith("/"):
            continue                                        # anúncio
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', resto, flags=re.S)
        res.append({"titulo": _limpo(titulo), "url": url, "trecho": _limpo(sn.group(1)) if sn else ""})
        if len(res) >= n:
            break
    return res


def _texto_pagina(url, limite=1000):
    try:
        pag = _get(url, timeout=3)
    except Exception:
        return ""
    pag = re.sub(r"(?is)<(script|style|nav|header|footer|aside|noscript|svg)[^>]*>.*?</\1>", " ", pag)
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", pag)
    txt = " ".join(_limpo(p) for p in paras if len(_limpo(p)) > 60)
    return txt[:limite]


def pesquisar(consulta, ia_local=None) -> dict:
    """Retorna {'resposta': texto curto pra falar, 'fontes': [{titulo,url}]}."""
    t0 = time.time()
    resultados = buscar(consulta)
    t_busca = time.time() - t0
    if not resultados:
        return {"resposta": f"Não achei nada sobre {consulta}.", "fontes": []}

    # lê a 1ª página (com limite de tempo curto) — os trechos da busca já ajudam muito
    t1 = time.time()
    textos = [""] * min(2, len(resultados))
    def ler(i):
        textos[i] = _texto_pagina(resultados[i]["url"])
    ths = [threading.Thread(target=ler, args=(i,)) for i in range(len(textos))]
    for t in ths:
        t.start()
    for t in ths:
        t.join(3)
    t_pag = time.time() - t1

    fontes = [{"titulo": r["titulo"], "url": r["url"]} for r in resultados[:4]]
    if ia_local is None or not ia_local.disponivel():
        resumo = " ".join(r["trecho"] for r in resultados[:2] if r["trecho"])
        return {"resposta": resumo or resultados[0]["titulo"], "fontes": fontes}

    material = ""
    for i, r in enumerate(resultados):
        material += f"\n[{i + 1}] {r['titulo']}\n{r['trecho'][:350]}\n"
        if i < len(textos) and textos[i]:
            material += f"Trecho da página: {textos[i]}\n"
    import datetime as _dt
    hoje = _dt.date.today().strftime("%d/%m/%Y")
    prompt = (f"Hoje é {hoje}. Pergunta do usuário: {consulta}\n\nResultados da internet (atuais):{material}\n\n"
              "Regras: responda SÓ com base nos resultados acima, mesmo que contradigam o que você acha que sabe — "
              "seu conhecimento pode estar desatualizado e os resultados são de hoje. Se houver informação mais "
              "recente (ano maior), ela vale mais. Não invente números nem nomes que não estejam nos resultados. "
              "Responda em português do Brasil, em no máximo 3 frases curtas e diretas, pra ser FALADO em voz alta "
              "(sem markdown, sem listas, sem links). Se os resultados não responderem, diga isso.")
    dados = {"model": ia_local.MODELO, "stream": False, "think": False, "keep_alive": ia_local.MANTER,
             "messages": [{"role": "user", "content": prompt}],
             "options": {"temperature": 0.1, "num_ctx": 4096, "num_predict": 140}}
    t2 = time.time()
    try:
        r = ia_local._post("/api/chat", dados, timeout=60)
    except Exception:
        dados.pop("think", None)
        r = ia_local._post("/api/chat", dados, timeout=60)
    texto = re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S).strip()
    texto = re.sub(r"[*#`_]+", "", texto)
    print(f"  (tempo: busca {t_busca:.1f}s • página {t_pag:.1f}s • IA {time.time() - t2:.1f}s)")
    return {"resposta": texto, "fontes": fontes}
