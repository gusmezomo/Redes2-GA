#!/usr/bin/env python3
"""
Metrica 4: reconvergencia apos falha de link.

Experimento:
  - PC1 pinga o PC5 sem parar (10 pings por segundo). Nos 3 protocolos o
    caminho normal e R1 -> R3 -> R5.
  - Depois de alguns segundos, o link R3-R5 falha.
  - O protocolo precisa perceber a falha e desviar o trafego por outro
    caminho (ex.: R3 -> R4 -> R5). Enquanto isso, os pings se perdem.
  - Tempo de interrupcao = pings perdidos x 0,1 s.
  - Ao mesmo tempo, captura os pacotes de controle gerados na rede toda.

Dois tipos de falha:
  link        : a interface do R3 e desligada ("cabo puxado"). Os dois
                roteadores percebem na hora, pois a interface cai.
  silenciosa  : o link continua "ligado", mas descarta 100% dos pacotes
                (ex.: um equipamento no meio do caminho travou). Os
                roteadores so percebem quando param de ouvir o vizinho,
                ou seja, depende dos temporizadores de cada protocolo.

Ao final, o link e restaurado. Para o proximo teste, recomenda-se subir
o laboratorio de novo (rodar.sh) para comecar de um estado limpo.

Resultado: resultados/convergencia.csv
Uso: python3 metricas/convergencia.py link
     python3 metricas/convergencia.py silenciosa
"""
import csv
import os
import re
import struct
import subprocess
import sys
import time

MODO = sys.argv[1] if len(sys.argv) > 1 else ""
if MODO not in ("link", "silenciosa"):
    sys.exit("uso: python3 metricas/convergencia.py link|silenciosa")

ANTES = 5                                    # segundos de ping antes da falha
JANELA = 30 if MODO == "link" else 240       # segundos observados apos a falha
TOTAL = ANTES + JANELA
INTERVALO = 0.1                              # intervalo entre pings

ROTEADORES = ["r1", "r2", "r3", "r4", "r5"]
FILTROS = {"ospf": "ip proto 89", "rip": "udp port 520", "bgp": "tcp port 179"}
IMAGEM = "ghcr.io/hellt/network-multitool"
ARQUIVO = "resultados/convergencia.csv"
CAMPOS = ["protocolo", "modo", "pings_enviados", "pings_perdidos", "interrupcao_s",
          "janela_s", "pacotes_controle", "bytes_controle"]

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
protocolo = os.readlink("configs/atual")


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def contar_pcap(dados):
    if len(dados) < 24:
        return 0, 0
    tipo_link = struct.unpack("<I", dados[20:24])[0]
    cabecalho = {113: 16, 276: 20, 1: 14}.get(tipo_link, 0)
    pos, pacotes, total = 24, 0, 0
    while pos + 16 <= len(dados):
        _, _, incl, orig = struct.unpack("<IIII", dados[pos:pos + 16])
        pacotes += 1
        total += orig - cabecalho
        pos += 16 + incl
    return pacotes, total


def tc(no, *args):
    """Roda o 'tc' (controle de trafego do Linux) na rede do roteador,
    usando um container auxiliar, como o tcpdump da metrica 3."""
    return sh("docker", "run", "--rm", "--network", f"container:{no}",
              "--cap-add", "NET_ADMIN", "--entrypoint", "tc", IMAGEM, *args)


def perda(no, iface, ligar):
    if ligar:
        r = tc(no, "qdisc", "replace", "dev", iface, "root", "netem", "loss", "100%")
    else:
        r = tc(no, "qdisc", "del", "dev", iface, "root")
    if r.returncode == 0:
        return r
    # plano B: ferramenta do containerlab (o erro 'unsupported kind: netem'
    # aparece so ao listar as regras depois de aplicar, e pode ser ignorado)
    r = sh("sudo", "containerlab", "tools", "netem", "set", "-n", no, "-i", iface,
           "--loss", "100" if ligar else "0")
    if "unsupported kind: netem" in r.stderr + r.stdout:
        r.returncode = 0
    return r


def falhar():
    if MODO == "link":
        return sh("docker", "exec", "clab-redes-r3", "ip", "link", "set", "eth3", "down")
    r = perda("clab-redes-r3", "eth3", True)
    r5 = perda("clab-redes-r5", "eth1", True)
    return r if r.returncode != 0 else r5


def restaurar():
    if MODO == "link":
        sh("docker", "exec", "clab-redes-r3", "ip", "link", "set", "eth3", "up")
    else:
        perda("clab-redes-r3", "eth3", False)
        perda("clab-redes-r5", "eth1", False)


print(f"Cenario: {protocolo} | falha: {MODO} | duracao: ~{TOTAL} s")

# 1) capturas de controle nos 5 roteadores
capturas = {r: subprocess.Popen(
    ["docker", "run", "--rm", "--network", f"container:clab-redes-{r}",
     "--cap-add", "NET_ADMIN", "--cap-add", "NET_RAW",
     "--entrypoint", "timeout", IMAGEM, "-s", "INT", str(TOTAL + 3),
     "tcpdump", "-i", "any", "-Q", "out", "-U", "-w", "-", FILTROS[protocolo]],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE) for r in ROTEADORES}
time.sleep(2)

# 2) ping continuo do PC1 para o PC5
ping = subprocess.Popen(
    # -c (contagem fixa) em vez de -w: com -w o ping encerra ao receber
    # qualquer aviso de erro da rede (ex.: "destino inalcancavel")
    ["docker", "exec", "clab-redes-pc1", "ping", "-i", str(INTERVALO),
     "-c", str(int(TOTAL / INTERVALO)), "-q", "192.168.5.10"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# 3) falha
time.sleep(ANTES)
r = falhar()
if r.returncode != 0:
    print("ERRO ao aplicar a falha:", r.stderr.strip())
print(f">> Link R3-R5 falhou ({MODO}). Observando por {JANELA} s...")

# 4) espera terminar
saida_ping, _ = ping.communicate()
m = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", saida_ping)
enviados, recebidos = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
perdidos = enviados - recebidos

pac = byt = 0
for proc in capturas.values():
    dados, _ = proc.communicate()
    p, b = contar_pcap(dados)
    pac += p
    byt += b

restaurar()
print(">> Link restaurado.")

linha = {"protocolo": protocolo, "modo": MODO, "pings_enviados": enviados,
         "pings_perdidos": perdidos, "interrupcao_s": round(perdidos * INTERVALO, 1),
         "janela_s": TOTAL, "pacotes_controle": pac, "bytes_controle": byt}
print(f"\nPings: {enviados} enviados, {perdidos} perdidos")
print(f"Interrupcao do trafego: ~{linha['interrupcao_s']} s")
print(f"Controle na rede durante o teste: {pac} pacotes, {byt} bytes")
if perdidos >= enviados - ANTES / INTERVALO:
    print("ATENCAO: o trafego nao voltou dentro da janela observada.")

os.makedirs("resultados", exist_ok=True)
antigas = []
if os.path.exists(ARQUIVO):
    with open(ARQUIVO) as f:
        antigas = [l for l in csv.DictReader(f)
                   if not (l["protocolo"] == protocolo and l["modo"] == MODO)]
with open(ARQUIVO, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS)
    w.writeheader()
    w.writerows(antigas + [linha])
print(f"Salvo em {ARQUIVO}")