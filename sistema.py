# -*- coding: utf-8 -*-
"""Monitor do PC (CPU, RAM, discos, GPU NVIDIA, rede) + alertas."""
import shutil
import subprocess
import time

try:
    import psutil
except ImportError:  # instalado pelo 1_instalar.bat
    psutil = None

_rede_antes = None
_discos_cache = (0.0, [])


_gpu_ultimo = None
_gpu_iniciado = False


def _ler_gpu_continuo():
    """Deixa o nvidia-smi aberto mandando uma linha por segundo (abrir ele toda vez era lento)."""
    global _gpu_ultimo
    import threading
    def loop():
        global _gpu_ultimo
        while True:
            try:
                p = subprocess.Popen(["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,"
                                      "memory.total", "--format=csv,noheader,nounits", "-lms", "1000"],
                                     stdout=subprocess.PIPE, text=True, creationflags=0x08000000)
                for linha in p.stdout:
                    try:
                        nome, uso, temp, usada, total = [x.strip() for x in linha.split(",")]
                        _gpu_ultimo = {"nome": nome.replace("NVIDIA GeForce ", ""), "uso": int(uso),
                                       "temp": int(temp), "mem_usada": int(usada) / 1024,
                                       "mem_total": int(total) / 1024}
                    except ValueError:
                        pass
            except Exception:
                _gpu_ultimo = None
            time.sleep(10)          # se o nvidia-smi fechar, tenta de novo
    threading.Thread(target=loop, daemon=True).start()


def gpu():
    """Uso, temperatura e memória da placa NVIDIA. None se não tiver."""
    global _gpu_iniciado
    if not _gpu_iniciado:
        _gpu_iniciado = True
        _ler_gpu_continuo()
        time.sleep(0.3)
    return _gpu_ultimo


def rede():
    """Velocidade de download/upload em MB/s desde a última chamada."""
    global _rede_antes
    if not psutil:
        return 0.0, 0.0
    agora = (time.time(), psutil.net_io_counters())
    if not _rede_antes:
        _rede_antes = agora
        return 0.0, 0.0
    dt = max(0.1, agora[0] - _rede_antes[0])
    down = (agora[1].bytes_recv - _rede_antes[1].bytes_recv) / dt / 1e6
    up = (agora[1].bytes_sent - _rede_antes[1].bytes_sent) / dt / 1e6
    _rede_antes = agora
    return down, up


def discos():
    res = []
    for letra in "CEF":
        try:
            u = shutil.disk_usage(f"{letra}:\\")
            res.append({"letra": letra, "livre": u.free / 1e9, "total": u.total / 1e9,
                        "pct": 100 * (u.total - u.free) / u.total})
        except OSError:
            pass
    return res


def leitura():
    d = {"cpu": 0.0, "ram_usada": 0.0, "ram_total": 0.0, "ram_pct": 0.0}
    if psutil:
        d["cpu"] = psutil.cpu_percent(interval=None)
        m = psutil.virtual_memory()
        d.update(ram_usada=m.used / 1e9, ram_total=m.total / 1e9, ram_pct=m.percent)
    global _discos_cache
    if time.time() - _discos_cache[0] > 5:
        _discos_cache = (time.time(), discos())
    d["discos"] = _discos_cache[1]
    d["down"], d["up"] = rede()
    return d


def alertas(d) -> list:
    a = []
    for disco in d.get("discos", []):
        if disco["letra"] == "C" and disco["livre"] < 10:
            a.append(f"Disco C: com só {disco['livre']:.1f} GB livres")
    if d.get("ram_pct", 0) > 90:
        a.append(f"Memória RAM em {d['ram_pct']:.0f}%")
    g = d.get("gpu")
    if g and g["temp"] >= 83:
        a.append(f"Placa de vídeo quente: {g['temp']} °C")
    return a


def resumo_falado() -> str:
    d = leitura()
    time.sleep(0.5)
    d["cpu"] = psutil.cpu_percent(interval=0.5) if psutil else 0
    partes = [f"Processador em {d['cpu']:.0f} por cento",
              f"memória em {d['ram_pct']:.0f} por cento"]
    for disco in d["discos"]:
        partes.append(f"disco {disco['letra']} com {disco['livre']:.0f} gigas livres")
    g = gpu()
    if g:
        partes.append(f"placa de vídeo a {g['temp']} graus")
    al = alertas({**d, "gpu": g})
    txt = ", ".join(partes) + "."
    if al:
        txt += " Atenção: " + "; ".join(al) + "."
    else:
        txt += " Tudo funcionando bem."
    return txt
