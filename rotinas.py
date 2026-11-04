# -*- coding: utf-8 -*-
"""
Lembretes, timers e rotinas agendadas do Jon (salvos em rotinas.json).
- Lembrete: "me lembra em 10 minutos de tirar o bolo" / "me lembra às 18h de ligar pra mãe"
- Timer:    "timer de 5 minutos"
- Rotina:   "todo dia às 8 horas toca minhas músicas curtidas" (roda um comando de voz no horário)
Se o PC estava desligado no horário de uma rotina, ela roda UMA vez quando o Jon abrir (até 12 h depois).
"""
import datetime as dt
import json
import os
import re
import threading
import time
import uuid

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(PASTA, "rotinas.json")
_trava = threading.Lock()

# o app/assistente troca estas funções
executar_comando = lambda texto: None   # noqa: E731
avisar = lambda texto: None             # noqa: E731

NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
           "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
           "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20,
           "trinta": 30, "quarenta": 40, "quarenta e cinco": 45, "cinquenta": 50, "sessenta": 60, "meia": 0.5}
DIAS = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}


# ---------------------- arquivo ----------------------

def carregar():
    try:
        with open(ARQ, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("lembretes", [])
    d.setdefault("rotinas", [])
    return d


def salvar(d):
    tmp = ARQ + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARQ)


# ---------------------- entender frases ----------------------

def _num(txt):
    txt = txt.strip()
    if re.fullmatch(r"\d+([.,]\d+)?", txt):
        return float(txt.replace(",", "."))
    return NUMEROS.get(txt)


def _duracao(f):
    """'10 minutos', 'meia hora', '1 hora e 30 minutos', '30 segundos' -> segundos."""
    total = 0
    if re.search(r"\bmeia hora\b", f):
        total += 1800
    for qtd, uni in re.findall(r"(\d+(?:[.,]\d+)?|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|"
                               r"quinze|vinte|trinta|quarenta|cinquenta)\s*(hora|horas|h|minuto|minutos|min|"
                               r"segundo|segundos|seg|s)\b", f):
        n = _num(qtd) or 0
        total += n * (3600 if uni.startswith("h") else 60 if uni.startswith("m") else 1)
    return int(total)


def _horario(f):
    """'às 18h', 'as 7:30', 'às 8 horas', 'às 9 da noite', 'meio dia' -> (h, m) ou None."""
    if re.search(r"\bmeio dia\b", f):
        return 12, 0
    if re.search(r"\bmeia noite\b", f):
        return 0, 0
    m = re.search(r"\b(?:as|a|das|para as|pras|pra)\s+(\d{1,2})(?:\s*(?:h|horas?|:)\s*(\d{2})?|\s+e\s+(\d{1,2}))?"
                  r"(?:\s+(?:da|de)\s+(manha|tarde|noite))?\b", f)
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2) or m.group(3) or 0)
    periodo = m.group(4)
    if periodo in ("tarde", "noite") and h < 12:
        h += 12
    if h > 23 or mi > 59:
        return None
    return h, mi


def _com_acentos(trecho, original):
    """Devolve 'trecho' (sem acento) com a grafia original da frase falada, se der pra achar."""
    if not original or not trecho:
        return trecho
    import unicodedata
    orig = re.sub(r"[^\w\s:']", " ", original).split()
    sem = ["".join(c for c in unicodedata.normalize("NFKD", w.lower()) if not unicodedata.combining(c)) for w in orig]
    alvo = trecho.split()
    for i in range(len(sem) - len(alvo) + 1):
        if sem[i:i + len(alvo)] == alvo:
            return " ".join(orig[i:i + len(alvo)])
    return trecho


def interpretar(f: str, original: str = ""):
    """Recebe frase normalizada (sem acento) e a original. Retorna dict com o que fazer, ou None."""
    p = _interpretar(f)
    if p and original:
        for k in ("texto", "lembrete"):
            if p.get(k):
                p[k] = _com_acentos(p[k], original)
    return p


def _interpretar(f: str):
    # listar / cancelar
    if re.search(r"\b(quais|lista|listar|mostra|ver)\b.*\b(lembretes?|rotinas?|timers?|alarmes?)\b", f):
        return {"tipo": "listar"}
    m = re.search(r"\b(cancela|cancelar|apaga|apagar|remove|remover|tira|desliga)\b.*\b(lembretes?|rotinas?|timers?|alarmes?)\b(.*)", f)
    if m:
        return {"tipo": "cancelar", "qual": m.group(2), "filtro": m.group(3).strip()}

    # timer
    m = re.search(r"\b(timer|temporizador|cronometro|contagem)\b", f)
    if m:
        seg = _duracao(f)
        if seg:
            return {"tipo": "lembrete", "segundos": seg, "texto": "O timer acabou!", "timer": True}

    # rotina diária / semanal
    m = re.search(r"\b(todo dia|todos os dias|diariamente|toda manha|toda noite|todo santo dia|"
                  r"dias uteis|de segunda a sexta|toda (segunda|terca|quarta|quinta|sexta)|todo (sabado|domingo)|"
                  r"fim de semana|fins de semana)\b", f)
    if m:
        hm = _horario(f) or ((7, 0) if "manha" in m.group(0) else (21, 0) if "noite" in m.group(0) else None)
        if hm:
            if re.search(r"dias uteis|segunda a sexta", m.group(0)):
                dias = [0, 1, 2, 3, 4]
            elif "fim" in m.group(0) or "fins" in m.group(0):
                dias = [5, 6]
            else:
                d1 = [v for k, v in DIAS.items() if k in m.group(0)]
                dias = d1 or list(range(7))
            # o comando é o que sobra depois do horário/dia
            cmd = re.sub(m.group(0), " ", f)
            cmd = re.sub(r"\b(?:as|a|para as|pras|pra)\s+\d{1,2}(?:\s*(?:h|horas?|:)\s*(?:\d{2})?|\s+e\s+\d{1,2})?"
                         r"(?:\s+(?:da|de)\s+(?:manha|tarde|noite))?\b", " ", cmd)
            cmd = re.sub(r"^\s*(jon\s*,?\s*)?(cria uma rotina|cria rotina|agenda|programa|quero que)\s*(pra|para|de|que)?\s*",
                         "", cmd)
            cmd = re.sub(r"^\s*(voce\s+)?", "", re.sub(r"\s+", " ", cmd)).strip(" ,.")
            if cmd.startswith("me lembr"):
                txt = re.sub(r"^me lembr\w*\s+(de|do|da|que)?\s*", "", cmd)
                return {"tipo": "rotina", "hora": hm, "dias": dias, "comando": "", "lembrete": txt or "Lembrete"}
            if cmd:
                return {"tipo": "rotina", "hora": hm, "dias": dias, "comando": cmd}

    # lembrete
    m = re.search(r"\b(me lembr\w*|lembra me|me avis\w*|me alert\w*|alarme|desperta\w*)\b", f)
    if m:
        resto = f[m.end():]
        # primeiro tira as expressões de tempo, depois pega o que vem após "de/que/pra"
        semtempo = re.sub(r"\b(em|daqui a|daqui|dentro de)\s+(meia hora|[\w\s,]*?(horas?|minutos?|segundos?|h|min))\b",
                          " ", resto)
        semtempo = re.sub(r"\b(?:as|a|para as)\s+\d{1,2}(?:\s*(?:h|horas?|:)\s*\d{0,2}|\s+e\s+\d{1,2})?"
                          r"(?:\s+(?:da|de)\s+(?:manha|tarde|noite))?\b", " ", semtempo)
        semtempo = re.sub(r"\b(amanha|hoje|meio dia|meia noite)\b", " ", semtempo)
        semtempo = re.sub(r"\s+", " ", semtempo).strip()
        texto = re.sub(r"^(de|do|da|que|pra|para)\s+", "", semtempo).strip(" ,.") or \
            "Você pediu pra eu te lembrar agora."
        seg = _duracao(resto) if re.search(r"\b(em|daqui|dentro de)\b", resto) else 0
        if seg:
            return {"tipo": "lembrete", "segundos": seg, "texto": texto}
        hm = _horario(resto)
        if hm:
            agora = dt.datetime.now()
            alvo = agora.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            if "amanha" in resto or alvo <= agora:
                alvo += dt.timedelta(days=1)
            return {"tipo": "lembrete", "quando": alvo.timestamp(), "texto": texto}
    return None


# ---------------------- executar pedidos ----------------------

def _fmt_quando(ts):
    d = dt.datetime.fromtimestamp(ts)
    hoje = dt.date.today()
    dia = "hoje" if d.date() == hoje else "amanhã" if d.date() == hoje + dt.timedelta(days=1) else d.strftime("%d/%m")
    return f"{dia} às {d.strftime('%H:%M')}"


def _fmt_dur(seg):
    h, r = divmod(int(seg), 3600)
    m, s = divmod(r, 60)
    p = []
    if h:
        p.append(f"{h} hora" + ("s" if h > 1 else ""))
    if m:
        p.append(f"{m} minuto" + ("s" if m > 1 else ""))
    if s and not h:
        p.append(f"{s} segundo" + ("s" if s > 1 else ""))
    return " e ".join(p) or "0 segundos"


NOMES_DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def descrever_dias(dias):
    if sorted(dias) == list(range(7)):
        return "todo dia"
    if sorted(dias) == [0, 1, 2, 3, 4]:
        return "dias úteis"
    if sorted(dias) == [5, 6]:
        return "fim de semana"
    return ", ".join(NOMES_DIAS[i] for i in sorted(dias))


def aplicar(pedido) -> str:
    """Executa o pedido interpretado. Retorna a frase de confirmação."""
    with _trava:
        d = carregar()
        t = pedido["tipo"]
        if t == "lembrete":
            quando = pedido.get("quando") or (time.time() + pedido["segundos"])
            d["lembretes"].append({"id": uuid.uuid4().hex[:8], "quando": quando, "texto": pedido["texto"],
                                   "timer": bool(pedido.get("timer"))})
            salvar(d)
            if pedido.get("timer"):
                return f"Timer de {_fmt_dur(pedido['segundos'])} começando agora."
            if pedido.get("segundos"):
                return f"Combinado, te lembro em {_fmt_dur(pedido['segundos'])}: {pedido['texto']}."
            return f"Combinado, te lembro {_fmt_quando(quando)}: {pedido['texto']}."
        if t == "rotina":
            h, m = pedido["hora"]
            d["rotinas"].append({"id": uuid.uuid4().hex[:8], "hora": f"{h:02d}:{m:02d}", "dias": pedido["dias"],
                                 "comando": pedido.get("comando", ""), "lembrete": pedido.get("lembrete", ""),
                                 "ativo": True, "ultima": dt.datetime.now().isoformat(timespec="minutes")})
            salvar(d)
            oque = pedido.get("comando") or ("te lembrar: " + pedido.get("lembrete", ""))
            return f"Rotina criada: {descrever_dias(pedido['dias'])} às {h:02d}:{m:02d}, {oque}."
        if t == "listar":
            return listar_texto(d)
        if t == "cancelar":
            qual, filtro = pedido["qual"], pedido.get("filtro", "")
            n = 0
            if qual.startswith(("lembrete", "timer", "alarme")):
                antes = len(d["lembretes"])
                if qual.startswith("timer"):
                    d["lembretes"] = [x for x in d["lembretes"] if not x.get("timer")]
                else:
                    d["lembretes"] = [x for x in d["lembretes"] if filtro and filtro not in x["texto"].lower()]
                n = antes - len(d["lembretes"])
            else:
                antes = len(d["rotinas"])
                hm = _horario(filtro) if filtro else None
                if hm:
                    alvo = f"{hm[0]:02d}:{hm[1]:02d}"
                    d["rotinas"] = [x for x in d["rotinas"] if x["hora"] != alvo]
                elif filtro:
                    d["rotinas"] = [x for x in d["rotinas"] if filtro not in x["comando"]]
                else:
                    d["rotinas"] = []
                n = antes - len(d["rotinas"])
            salvar(d)
            return f"Cancelei {n} {qual}." if n else f"Não achei {qual} pra cancelar."
    return ""


def listar_texto(d=None) -> str:
    d = d or carregar()
    partes = []
    pend = sorted(d["lembretes"], key=lambda x: x["quando"])
    if pend:
        partes.append("Lembretes: " + "; ".join(f"{_fmt_quando(x['quando'])} {x['texto']}" for x in pend[:5]))
    if d["rotinas"]:
        partes.append("Rotinas: " + "; ".join(
            f"{descrever_dias(r['dias'])} às {r['hora']} {r['comando'] or r.get('lembrete', '')}"
            for r in d["rotinas"] if r.get("ativo", True)))
    return ". ".join(partes) + "." if partes else "Você não tem lembretes nem rotinas."


def proximos(n=4):
    """Para a interface: [(quando_ts, texto, tipo)] ordenado."""
    d = carregar()
    itens = [(x["quando"], ("⏱ " if x.get("timer") else "⏰ ") + x["texto"], "lembrete") for x in d["lembretes"]]
    agora = dt.datetime.now()
    for r in d["rotinas"]:
        if not r.get("ativo", True):
            continue
        h, m = map(int, r["hora"].split(":"))
        for k in range(8):
            dia = agora + dt.timedelta(days=k)
            alvo = dia.replace(hour=h, minute=m, second=0, microsecond=0)
            if alvo > agora and alvo.weekday() in r["dias"]:
                itens.append((alvo.timestamp(), "🔁 " + (r["comando"] or r.get("lembrete", "")), "rotina"))
                break
    return sorted(itens)[:n]


def remover(id_):
    with _trava:
        d = carregar()
        d["lembretes"] = [x for x in d["lembretes"] if x["id"] != id_]
        d["rotinas"] = [x for x in d["rotinas"] if x["id"] != id_]
        salvar(d)


# ---------------------- relógio ----------------------

def _ultima_ocorrencia(r, agora):
    h, m = map(int, r["hora"].split(":"))
    for k in range(8):
        dia = agora - dt.timedelta(days=k)
        alvo = dia.replace(hour=h, minute=m, second=0, microsecond=0)
        if alvo <= agora and alvo.weekday() in r["dias"]:
            return alvo
    return None


def _rodar_rotina(r):
    if r.get("comando"):
        avisar(f"Rotina das {r['hora']}: {r['comando']}")
        threading.Thread(target=executar_comando, args=(r["comando"],), daemon=True).start()
    else:
        avisar(f"Lembrete das {r['hora']}: {r.get('lembrete', '')}")


def verificar():
    agora = dt.datetime.now()
    disparar = []
    with _trava:
        d = carregar()
        mudou = False
        for x in list(d["lembretes"]):
            if x["quando"] <= time.time():
                d["lembretes"].remove(x)
                disparar.append(lambda x=x: avisar(x["texto"] if x.get("timer") else "Lembrete: " + x["texto"]))
                mudou = True
        for r in d["rotinas"]:
            if not r.get("ativo", True):
                continue
            ult = _ultima_ocorrencia(r, agora)
            feita = dt.datetime.fromisoformat(r.get("ultima", "2000-01-01T00:00"))
            # roda se a última ocorrência ainda não foi feita (e não faz mais de 12 h — PC desligado)
            if ult and ult > feita and (agora - ult) < dt.timedelta(hours=12):
                r["ultima"] = agora.isoformat(timespec="minutes")
                disparar.append(lambda r=dict(r): _rodar_rotina(r))
                mudou = True
        if mudou:
            salvar(d)
    for fn in disparar:
        try:
            fn()
        except Exception as e:
            print("  Erro na rotina:", e)


def iniciar_relogio():
    def loop():
        while True:
            try:
                verificar()
            except Exception as e:
                print("  Erro no relógio de rotinas:", e)
            time.sleep(5)
    threading.Thread(target=loop, daemon=True).start()
