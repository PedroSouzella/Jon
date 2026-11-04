# -*- coding: utf-8 -*-
"""Quem é o dono deste Jon: nome e cidade (ficam no config.json; o Jon pergunta na primeira vez)."""
import json
import os

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_CONFIG = os.path.join(PASTA, "config.json")
CIDADE_RESERVA = ("São Paulo", -23.5505, -46.6333)


def _cfg():
    try:
        with open(ARQ_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def nome() -> str:
    return (_cfg().get("nome") or "").strip()


def cidade():
    """(nome, latitude, longitude) da cidade do dono."""
    c = _cfg().get("cidade")
    try:
        return (c["nome"], float(c["lat"]), float(c["lon"]))
    except Exception:
        return CIDADE_RESERVA


def salvar(nome_=None, cidade_=None):
    cfg = _cfg()
    if nome_ is not None:
        cfg["nome"] = nome_.strip()
    if cidade_ is not None:
        cfg["cidade"] = {"nome": cidade_[0], "lat": cidade_[1], "lon": cidade_[2]}
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
