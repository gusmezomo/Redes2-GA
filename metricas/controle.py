#!/usr/bin/env python3
"""
Metrica 3: trafego de controle e memoria de cada protocolo.

Para cada roteador, captura durante DURACAO segundos todos os pacotes do
protocolo de roteamento que o roteador ENVIA (tcpdump), e mede:
  - pacotes      : quantidade de pacotes de controle enviados
  - bytes        : tamanho total desses pacotes (nivel IP)
  - pacotes_por_s / bytes_por_s : as mesmas medidas por segundo
  - memoria_kb   : memoria RAM usada pelo processo do protocolo (ospfd, ripd ou bgpd)

A captura roda num container auxiliar (imagem network-multitool, que tem o
tcpdump) "grudado" na rede do roteador, entao nada precisa ser instalado
nos roteadores. Os 5 roteadores sao capturados ao mesmo tempo.

Filtros usados (cada protocolo tem sua "assinatura" no pacote):
  OSPF -> protocolo IP 89 | RIP -> UDP porta 520 | BGP -> TCP porta 179

Rode com a rede ja estabilizada (>= 1 min depois do deploy): esta metrica
mede o custo do protocolo em regime normal, sem mudancas na topologia.

Resultado: resultados/controle.csv
Uso: python3 metricas/controle.py [duracao_em_segundos]   (padrao 120)
"""
import csv
import os
import struct
import subprocess
import sys

ROTEADORES = ["r1", "r2", "r3", "r4", "r5"]
DURACAO = int(sys.argv[1]) if len(sys.argv) > 1 else 120
FILTROS = {"ospf": "ip proto 89", "rip": "udp port 520", "bgp": "tcp port 179"}
DAEMONS = {"ospf": "ospfd", "rip": "ripd", "bgp": "bgpd"}
IMAGEM = "ghcr.io/hellt/network-multitool"
ARQUIVO = "resultados/controle.csv"
CAMPOS = ["protocolo", "roteador", "duracao_s", "pacotes", "bytes",
          "pacotes_por_s", "bytes_por_s", "memoria_kb"]

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
protocolo = os.readlink("configs/atual")
print(f"Cenario atual: {protocolo}")
print(f"Capturando {DURACAO} s de trafego '{FILTROS[protocolo]}' nos 5 roteadores...")


def contar_pcap(dados):
    """Le um arquivo pcap (em memoria) e devolve (pacotes, bytes no nivel IP)."""
    if len(dados) < 24:
        return 0, 0
    tipo_link = struct.unpack("<I", dados[20:24])[0]
    # com '-i any' o Linux usa um cabecalho proprio no lugar do Ethernet
    cabecalho = {113: 16, 276: 20, 1: 14}.get(tipo_link, 0)
    pos, pacotes, total = 24, 0, 0
    while pos + 16 <= len(dados):
        _, _, incl, orig = struct.unpack("<IIII", dados[pos:pos + 16])
        pacotes += 1
        total += orig - cabecalho
        pos += 16 + incl
    return pacotes, total


# dispara as 5 capturas em paralelo
capturas = {}
for r in ROTEADORES:
    capturas[r] = subprocess.Popen(
        ["docker", "run", "--rm",
         "--network", f"container:clab-redes-{r}",   # usa a rede do roteador
         "--cap-add", "NET_ADMIN", "--cap-add", "NET_RAW",
         "--entrypoint", "timeout", IMAGEM,
         "-s", "INT", str(DURACAO),                  # para o tcpdump apos DURACAO s
         "tcpdump", "-i", "any", "-Q", "out", "-U", "-w", "-",
         FILTROS[protocolo]],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

linhas = []
for r in ROTEADORES:
    saida, erro = capturas[r].communicate()
    pacotes, total = contar_pcap(saida)
    if pacotes == 0:
        print(f"  aviso {r}: nenhum pacote capturado. stderr do tcpdump:\n"
              f"  {erro.decode(errors='ignore').strip()}")

    mem = subprocess.run(
        ["docker", "exec", f"clab-redes-{r}", "sh", "-c",
         f"grep VmRSS /proc/$(pidof {DAEMONS[protocolo]})/status"],
        capture_output=True, text=True).stdout.split()
    memoria = int(mem[1]) if len(mem) > 1 else None

    linhas.append({"protocolo": protocolo, "roteador": r, "duracao_s": DURACAO,
                   "pacotes": pacotes, "bytes": total,
                   "pacotes_por_s": round(pacotes / DURACAO, 3),
                   "bytes_por_s": round(total / DURACAO, 1),
                   "memoria_kb": memoria})
    print(f"{r}: {pacotes} pacotes, {total} bytes "
          f"({total / DURACAO:.1f} B/s), {DAEMONS[protocolo]} usando {memoria} KB")

tp = sum(l["pacotes"] for l in linhas)
tb = sum(l["bytes"] for l in linhas)
print(f"\nTOTAL na rede: {tp} pacotes, {tb} bytes em {DURACAO} s "
      f"= {tp / DURACAO:.2f} pacotes/s, {tb / DURACAO:.1f} B/s")

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