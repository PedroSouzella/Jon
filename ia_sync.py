# -*- coding: utf-8 -*-
"""
Comunicação e Sincronização entre IAs do Jon (Sabadini & Pedro).
Analisa automaticamente as versões e commits entre Sabadini25/Jon e PedroSouzella/jon.
"""
import subprocess
import os
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))

def executar_git(args):
    cmd = ["git"] + args
    res = subprocess.run(cmd, cwd=PASTA, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout.strip(), res.stderr.strip()

def obter_versao_local():
    try:
        from versao import VERSAO, VERSAO_NOME
        return f"{VERSAO} ({VERSAO_NOME})"
    except Exception:
        return "Desconhecida"

def relatorio_sincronizacao():
    print("=" * 65)
    print("CHAT & SINCRONIZACAO DE IAs - JON (Sabadini <-> Pedro)")
    print("=" * 65)
    
    versao = obter_versao_local()
    print(f"Versao Unificada Local: v{versao}\n")
    
    # Atualiza remotes
    executar_git(["fetch", "origin"])
    executar_git(["fetch", "pedro"])
    
    # Ultimos commits
    sha_orig, _ = executar_git(["rev-parse", "--short", "origin/main"])
    msg_orig, _ = executar_git(["log", "-1", "--pretty=%s", "origin/main"])
    
    sha_pedro, _ = executar_git(["rev-parse", "--short", "pedro/main"])
    msg_pedro, _ = executar_git(["log", "-1", "--pretty=%s", "pedro/main"])
    
    sha_local, _ = executar_git(["rev-parse", "--short", "HEAD"])
    
    print(f"Local (HEAD):            [{sha_local}]")
    print(f"Sabadini25/Jon (origin): [{sha_orig}] -> {msg_orig}")
    print(f"PedroSouzella/jon:       [{sha_pedro}] -> {msg_pedro}")
    print("-" * 65)
    
    faltando_no_origin, _ = executar_git(["log", "--oneline", "origin/main..pedro/main"])
    faltando_no_pedro, _ = executar_git(["log", "--oneline", "pedro/main..HEAD"])
    
    print("[1] O QUE FALTA SUBIR PARA O PEDRO (PedroSouzella/jon):")
    if faltando_no_pedro:
        for linha in faltando_no_pedro.splitlines():
            print(f"  + {linha}")
    else:
        print("  - O repositorio do Pedro ja possui todos esses commits.")
        
    print("\n[2] O QUE FALTA SUBIR PARA O SABADINI (Sabadini25/Jon):")
    faltando_subir_sabadini, _ = executar_git(["log", "--oneline", "origin/main..HEAD"])
    if faltando_subir_sabadini:
        for linha in faltando_subir_sabadini.splitlines():
            print(f"  + {linha}")
    else:
        print("  - O repositorio do Sabadini ja esta 100% atualizado com este PC.")
        
    print("=" * 65)

if __name__ == "__main__":
    relatorio_sincronizacao()
