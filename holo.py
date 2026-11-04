# -*- coding: utf-8 -*-
"""
Geometria da esfera holográfica do Jon (independente de interface, dá pra testar sem Windows).
Fragmentos de luz espalhados em camadas de uma esfera, girando em 3D com perspectiva.
"""
import math
import random


def gerar_fragmentos(n=260, semente=7):
    rnd = random.Random(semente)
    frags = []
    ouro = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i + 0.5) / n * 2
        r = math.sqrt(1 - y * y)
        th = i * ouro
        p = (math.cos(th) * r, y, math.sin(th) * r)
        # direção do traço: ao longo do "meridiano" ou do "paralelo"
        if rnd.random() < 0.6:
            t = (-math.sin(th), 0.0, math.cos(th))                       # paralelo (horizontal)
        else:
            t = (-math.cos(th) * y, r, -math.sin(th) * y)                  # meridiano (vertical)
        camada = 1.0 if rnd.random() < 0.55 else rnd.uniform(0.55, 0.95)  # casca + volume interno
        frags.append({
            "p": p, "t": t, "camada": camada,
            "tam": rnd.uniform(0.03, 0.16) * (1.4 if rnd.random() < 0.12 else 1.0),
            "bloco": rnd.random() < 0.18,                                  # "blocos de dados" mais grossos
            "fase": rnd.uniform(0, math.tau),
        })
    return frags


def _rot(v, ay, ax):
    x, y, z = v
    c, s = math.cos(ay), math.sin(ay)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(ax), math.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    return x, y, z


def projetar(frags, cx, cy, R, ang, inclinacao=0.32, nivel=0.0, fase=0.0, varredura=None):
    """Devolve lista de (x1, y1, x2, y2, profundidade 0..1, bloco, brilho_extra)."""
    d = 3.2
    saida = []
    for f in frags:
        k = f["camada"] * (1 + nivel * 0.22 + math.sin(fase * 7 + f["fase"]) * nivel * 0.06)
        p = tuple(c * k for c in f["p"])
        q = tuple(p[i] + f["t"][i] * f["tam"] for i in range(3))
        a = _rot(p, ang, inclinacao)
        b = _rot(q, ang, inclinacao)
        sa, sb = d / (d - a[2]), d / (d - b[2])
        prof = (a[2] + 1.25) / 2.5
        extra = 0.0
        if varredura is not None:
            extra = max(0.0, 1 - abs(a[1] - varredura) * 6)
        saida.append((cx + a[0] * R * sa, cy - a[1] * R * sa, cx + b[0] * R * sb, cy - b[1] * R * sb,
                      max(0.0, min(1.0, prof)), f["bloco"], extra))
    return saida


def orbita(cx, cy, R, ang, inclinacao, giro, pontos=56):
    """Anel inclinado (polilinha) — devolve coords planas e profundidades."""
    d = 3.2
    coords, profs = [], []
    for i in range(pontos + 1):
        t = i / pontos * math.tau
        v = (math.cos(t), 0.0, math.sin(t))
        # inclina o anel no próprio eixo, depois aplica a rotação da esfera
        c, s = math.cos(giro), math.sin(giro)
        v = (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])
        x, y, z = _rot(v, ang, inclinacao)
        sc = d / (d - z)
        coords += [cx + x * R * sc, cy - y * R * sc]
        profs.append((z + 1) / 2)
    return coords, profs
