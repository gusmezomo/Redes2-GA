#!/usr/bin/env python3
"""
Metrica 1: tamanho da tabela de rotas.

Para cada roteador, pergunta ao FRR a tabela de rotas (em formato JSON)
e conta:
  - prefixos_total : quantas redes de destino o roteador conhece
  - rotas_aprendidas: quantas dessas vieram do protocolo (OSPF, RIP ou BGP)
  - next_hops      : quantos caminhos foram instalados para as rotas aprendidas
                     (maior que rotas_aprendidas quando ha caminhos em paralelo)

A rede de gerencia do containerlab (172.20.20.0/24, eth0) e a rota padrao
dela sao ignoradas, pois nao fazem parte do trabalho.

O protocolo e descoberto pelo link configs/atual (criado pelo rodar.sh).
Resultado: resultados/tabela_rotas.csv (uma linha por roteador e protocolo).

Uso: python3 metricas/tabela_rotas.py
"""
import csv
import json
import os
import subprocess

ROTEADORES = ["r1", "r2", "r3", "r4", "r5"]
PROTOCOLOS = {"ospf", "rip", "bgp"}
ARQUIVO = "resultados/tabela_rotas.csv"
CAMPOS = ["protocolo", "roteador", "prefixos_total", "rotas_aprendidas", "next_hops"]

# vai para a raiz do projeto, independente de onde o script foi chamado
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

protocolo = os.readlink("configs/atual")
print(f"Cenario atual: {protocolo}\n")


def ignorar(prefixo):
    return prefixo.startswith("172.20.20.") or prefixo == "0.0.0.0/0"


linhas = []
for r in ROTEADORES:
    saida = subprocess.run(
        ["docker", "exec", f"clab-redes-{r}", "vtysh", "-c", "show ip route json"],
        capture_output=True, text=True, check=True,
    ).stdout
    tabela = json.loads(saida)

    total = aprendidas = next_hops = 0
    for prefixo, entradas in tabela.items():
        if ignorar(prefixo):
            continue
        # cada prefixo pode ter varias entradas (ex.: connected e ospf);
        # so conta a que foi selecionada para uso
        escolhida = next((e for e in entradas if e.get("selected")), None)
        if escolhida is None or escolhida["protocol"] == "local":
            continue
        total += 1
        if escolhida["protocol"] in PROTOCOLOS:
            aprendidas += 1
            next_hops += sum(1 for nh in escolhida.get("nexthops", []) if nh.get("fib"))

    linhas.append({"protocolo": protocolo, "roteador": r, "prefixos_total": total,
                   "rotas_aprendidas": aprendidas, "next_hops": next_hops})
    print(f"{r}: {total} prefixos, {aprendidas} aprendidos via {protocolo}, {next_hops} next-hops")

# mantem as linhas dos outros protocolos e substitui as deste
os.makedirs("resultados", exist_ok=True)
antigas = []
if os.path.exists(ARQUIVO):
    with open(ARQUIVO) as f:
        antigas = [l for l in csv.DictReader(f) if l["protocolo"] != protocolo]

with open(ARQUIVO, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS)
    w.writeheader()
    w.writerows(antigas + linhas)

print(f"\nSalvo em {ARQUIVO}")