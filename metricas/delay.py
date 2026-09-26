#!/usr/bin/env python3
"""
Metrica 2: delay (atraso) e caminho entre os PCs.

Para cada par de PCs (origem -> destino):
  - envia 10 pings e guarda o tempo de ida e volta (RTT) minimo, medio
    e maximo, alem da perda de pacotes;
  - roda um traceroute para registrar por quais roteadores o trafego
    passou (o caminho escolhido pelo protocolo).

O protocolo e descoberto pelo link configs/atual (criado pelo rodar.sh).
Resultado: resultados/delay.csv (uma linha por par de PCs e protocolo).

Uso: python3 metricas/delay.py
"""
import csv
import os
import re
import subprocess

PCS = [1, 2, 3, 4, 5]
PINGS = 10
ARQUIVO = "resultados/delay.csv"
CAMPOS = ["protocolo", "origem", "destino", "roteadores_no_caminho", "caminho",
          "rtt_min_ms", "rtt_medio_ms", "rtt_max_ms", "perda_pct"]

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
protocolo = os.readlink("configs/atual")
print(f"Cenario atual: {protocolo}\n")


def no_pc(pc, *comando):
    """Executa um comando dentro do container do PC e devolve a saida."""
    return subprocess.run(["docker", "exec", f"clab-redes-pc{pc}", *comando],
                          capture_output=True, text=True).stdout


def medir_ping(origem, ip):
    saida = no_pc(origem, "ping", "-c", str(PINGS), "-i", "0.2", "-q", ip)
    perda = re.search(r"(\d+(?:\.\d+)?)% packet loss", saida)
    rtt = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)", saida)
    return (float(perda.group(1)) if perda else 100.0,
            [float(x) for x in rtt.groups()] if rtt else [None, None, None])


def medir_caminho(origem, ip):
    saida = no_pc(origem, "traceroute", "-n", "-q", "1", "-w", "1", ip)
    saltos = []
    for linha in saida.splitlines():
        partes = linha.split()
        if partes and partes[0].isdigit():
            saltos.append(partes[1] if len(partes) > 1 else "*")
    # o ultimo salto e o proprio destino; os anteriores sao os roteadores
    roteadores = saltos[:-1] if saltos and saltos[-1] == ip else saltos
    return len(roteadores), " > ".join(roteadores)


linhas = []
for o in PCS:
    for d in PCS:
        if o == d:
            continue
        ip = f"192.168.{d}.10"
        perda, (rmin, rmed, rmax) = medir_ping(o, ip)
        n, caminho = medir_caminho(o, ip)
        linhas.append({"protocolo": protocolo, "origem": f"pc{o}", "destino": f"pc{d}",
                       "roteadores_no_caminho": n, "caminho": caminho,
                       "rtt_min_ms": rmin, "rtt_medio_ms": rmed, "rtt_max_ms": rmax,
                       "perda_pct": perda})
        print(f"pc{o} -> pc{d}: rtt medio {rmed} ms, perda {perda}%, "
              f"{n} roteadores ({caminho})")

validos = [l["rtt_medio_ms"] for l in linhas if l["rtt_medio_ms"] is not None]
if validos:
    print(f"\nRTT medio geral: {sum(validos) / len(validos):.3f} ms")

os.makedirs("resultados", exist_ok=True)
antigas = []
if os.path.exists(ARQUIVO):
    with open(ARQUIVO) as f:
        antigas = [l for l in csv.DictReader(f) if l["protocolo"] != protocolo]
with open(ARQUIVO, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS)
    w.writeheader()
    w.writerows(antigas + linhas)
print(f"Salvo em {ARQUIVO}")