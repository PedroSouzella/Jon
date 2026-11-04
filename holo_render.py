# -*- coding: utf-8 -*-
"""
Renderizador orgânico da esfera do Jon (numpy + Pillow).
- Partículas são "borrões" de luz suaves (sem serrilhado).
- O quadro anterior desbota em vez de sumir -> rastros curvos naturais seguindo a rotação.
- Brilho é acumulado e depois mapeado numa paleta (escuro -> roxo -> lilás -> branco).
"""
import math

import numpy as np

import holo


def _sprite(raio):
    t = int(raio * 6) | 1                       # ±3 desvios: o brilho some antes da borda (sem "quadrado")
    c = t // 2
    y, x = np.mgrid[0:t, 0:t]
    return np.exp(-((x - c) ** 2 + (y - c) ** 2) / (2 * raio ** 2)).astype(np.float32)


def _hex(c):
    return np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def paleta(fundo, escuro, cor, claro):
    """LUT de 256 cores: fundo -> escuro -> cor -> claro -> branco."""
    pts = [(0.0, _hex(fundo)), (0.18, _hex(escuro)), (0.5, _hex(cor)), (0.8, _hex(claro)),
           (1.0, np.array([255, 255, 255], np.float32))]
    lut = np.zeros((256, 3), np.float32)
    for i in range(256):
        t = i / 255
        for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
            if t <= t1:
                k = (t - t0) / (t1 - t0)
                lut[i] = c0 + (c1 - c0) * k
                break
    return lut


class Renderizador:
    def __init__(self, tam, n_frag=260):
        self.tam = int(tam)
        self.buf = np.zeros((self.tam, self.tam), np.float32)
        self.sp = {r: _sprite(r) for r in (0.75, 1.0, 1.4, 2.0)}   # pontos menores = mais nítido
        self.brilho_centro = _sprite(self.tam * 0.032)
        self.ponto_centro = _sprite(self.tam * 0.012)
        # "atmosfera": disco de brilho bem fraco que dá corpo à esfera
        y, x = np.mgrid[0:self.tam, 0:self.tam]
        d = np.sqrt((x - self.tam / 2) ** 2 + (y - self.tam / 2) ** 2) / (self.tam * 0.36)
        self.atmosfera = (np.clip(1 - d, 0, 1) ** 1.8 * 0.022 + np.exp(-((d - 1.0) / 0.025) ** 2) * 0.03).astype(np.float32)
        self.frags = holo.gerar_fragmentos(n_frag, semente=11)
        self.ultimas = None
        self.lut = None
        self.lut_alvo = None

    def definir_paleta(self, lut):
        self.lut_alvo = lut
        if self.lut is None:
            self.lut = lut.copy()

    def _soma(self, x, y, sp, ganho):
        h = sp.shape[0] // 2
        xi, yi = int(x) - h, int(y) - h
        x0, y0 = max(xi, 0), max(yi, 0)
        x1, y1 = min(xi + sp.shape[1], self.tam), min(yi + sp.shape[0], self.tam)
        if x1 <= x0 or y1 <= y0:
            return
        self.buf[y0:y1, x0:x1] += sp[y0 - yi:y1 - yi, x0 - xi:x1 - xi] * ganho

    def quadro(self, ang, fase, nivel=0.0, varredura=None, estado="pronto"):
        T = self.tam
        cx = cy = T / 2
        R = T * 0.34
        # desbota o quadro anterior (rastro orgânico)
        self.buf *= 0.70 if estado != "processando" else 0.62   # rastro mais curto = menos borrado

        self.buf += self.atmosfera
        # fragmentos viram partículas: frente forte e nítida, fundo fraco e difuso.
        # Entre o quadro anterior e o atual desenha passos intermediários -> cauda contínua.
        segs = holo.projetar(self.frags, cx, cy, R, ang, nivel=nivel, fase=fase, varredura=varredura)
        atuais = [((x1 + x2) / 2, (y1 + y2) / 2) for x1, y1, x2, y2, *_ in segs]
        antes = self.ultimas if self.ultimas and len(self.ultimas) == len(atuais) else atuais
        for (px, py), (qx, qy), (_, _, _, _, prof, bloco, extra) in zip(antes, atuais, segs):
            g = (0.07 + prof ** 1.8 * 0.62 + extra * 0.35) * (1.5 if bloco else 1.0)
            sp = self.sp[0.75] if prof > 0.66 else self.sp[1.0] if prof > 0.33 else self.sp[1.4]
            dist = abs(qx - px) + abs(qy - py)
            passos = 1 if dist < 1.5 else 2 if dist < 4 else 3
            for k in range(1, passos + 1):
                t = k / passos
                self._soma(px + (qx - px) * t, py + (qy - py) * t, sp, g / passos * (0.6 + 0.4 * t))
        self.ultimas = atuais

        # órbitas: poeira luminosa ao longo de anéis inclinados
        for k, (gi, rr) in enumerate(((0.5, 1.18), (-0.9, 1.08), (1.4, 0.8))):
            cs, pf = holo.orbita(cx, cy, R * rr * (1 + nivel * 0.12), ang * (1 + k * 0.3), 0.32, gi, 70)
            for j in range(0, len(pf) - 1, 1):
                if (j + int(fase * 6)) % 3:
                    continue                                   # pontilhado que "corre" no anel
                self._soma(cs[j * 2], cs[j * 2 + 1], self.sp[0.75], 0.06 + pf[j] ** 2 * 0.30)

        # arco amplo (meia espiral) girando
        ra = R * 0.62
        for j in range(26):
            a = -fase * 0.7 + j * 0.13
            r = ra * (1 - j * 0.004)
            self._soma(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.9, self.sp[1.0], 0.06 + j / 26 * 0.30)

        # centro: brilho difuso + anel suave + pulso com a voz
        g = 0.05 + nivel * 0.12 + 0.01 * math.sin(fase * 2)   # acumula ~5x com o desbotamento
        self._soma(cx, cy, self.brilho_centro, g)
        self._soma(cx, cy, self.ponto_centro, 0.09 + nivel * 0.1)       # miolo nítido
        rc = R * 0.19 + nivel * 10
        for j in range(36):
            a = j / 36 * math.tau + fase * 0.4  # anel do centro
            self._soma(cx + math.cos(a) * rc, cy + math.sin(a) * rc, self.sp[0.75], 0.10)

        # transição suave de cor entre estados
        if self.lut_alvo is not None:
            self.lut += (self.lut_alvo - self.lut) * 0.15
        # mapeia brilho -> cor (curva suave, sem estourar)
        v = 1.0 - np.exp(-self.buf * 2.0)
        idx = (v * 255).astype(np.uint8)
        return self.lut[idx].astype(np.uint8)
