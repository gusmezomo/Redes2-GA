# /// script
# dependencies = ["matplotlib"]
# ///
# Gera um grafico por metrica, comparando OSPF, RIP e BGP.
# Le os CSVs de resultados/ e salva as imagens em graficos/.
# Uso: uv run metricas/graficos.py

import csv
import os

import matplotlib
matplotlib.use("Agg")   # salva em arquivo, sem abrir janela
import matplotlib.pyplot as plt

# vai para a pasta do projeto e cria a pasta dos graficos
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.makedirs("graficos", exist_ok=True)

PROTOCOLOS = ["ospf", "rip", "bgp"]
NOMES = {"ospf": "OSPF", "rip": "RIP", "bgp": "BGP"}
CORES = {"ospf": "#2a78c7", "rip": "#e08a1e", "bgp": "#3a9a5b"}
ROTEADORES = ["r1", "r2", "r3", "r4", "r5"]

# estilo dos graficos
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "axes.grid.axis": "y", "grid.alpha": 0.3,
                     "axes.axisbelow": True})


# le um CSV, ex.: ler("delay", "ospf") -> resultados/delay_ospf.csv
def ler(metrica, proto):
    with open(f"resultados/{metrica}_{proto}.csv") as f:
        return list(csv.DictReader(f))


# escreve o valor em cima de cada barra (ou um texto no lugar do zero)
def rotular(ax, barras, fmt="{:g}", zero=None):
    for b in barras:
        h = b.get_height()
        ax.annotate(zero if (zero and h == 0) else fmt.format(h),
                    (b.get_x() + b.get_width() / 2, h), ha="center", va="bottom",
                    fontsize=9, xytext=(0, 2), textcoords="offset points")


# grafico simples: uma barra por protocolo
def por_protocolo(ax, valores, titulo, ylabel, fmt="{:g}", zero=None):
    b = ax.bar([NOMES[p] for p in PROTOCOLOS], [valores[p] for p in PROTOCOLOS],
               color=[CORES[p] for p in PROTOCOLOS], width=0.6)
    rotular(ax, b, fmt, zero)
    ax.set(title=titulo, ylabel=ylabel)
    ax.margins(y=0.15)


# coloca o titulo e salva a imagem
def salvar(fig, nome, titulo):
    fig.suptitle(titulo, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"graficos/{nome}.png", dpi=150)
    plt.close(fig)
    print(f"graficos/{nome}.png")


# ---------- 1. Tamanho da tabela de roteamento
# dois graficos lado a lado: prefixos e next-hops de cada roteador,
# com uma barra de cada protocolo por roteador
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
larg = 0.26
for i, p in enumerate(PROTOCOLOS):
    d = {l["roteador"]: l for l in ler("tabela_rotas", p)}
    xs = [x + (i - 1) * larg for x in range(5)]   # desloca a barra de cada protocolo
    for ax, campo in zip(axs, ["prefixos_total", "next_hops"]):
        b = ax.bar(xs, [int(d[r][campo]) for r in ROTEADORES], larg,
                   color=CORES[p], label=NOMES[p])
        rotular(ax, b)
axs[0].set(title="Prefixos na tabela", ylabel="prefixos")
axs[1].set(title="Next-hops instalados (> rotas = caminhos em paralelo)", ylabel="next-hops")
for ax in axs:
    ax.set_xticks(range(5), [r.upper() for r in ROTEADORES])
    ax.margins(y=0.15)
axs[1].legend()
salvar(fig, "1_tabela_rotas", "Métrica 1 — Tamanho da tabela de roteamento")


# ---------- 2. Delay
# barra = media dos RTTs medios dos 20 pares de PCs
# linha preta = vai da media dos RTTs minimos ate a dos maximos (variacao)
def media_col(dados, campo):
    return sum(float(l[campo]) for l in dados) / len(dados)

dl = {p: ler("delay", p) for p in PROTOCOLOS}
med = {p: media_col(dl[p], "rtt_medio_ms") for p in PROTOCOLOS}
mn = {p: media_col(dl[p], "rtt_min_ms") for p in PROTOCOLOS}
mx = {p: media_col(dl[p], "rtt_max_ms") for p in PROTOCOLOS}

fig, ax = plt.subplots(figsize=(7, 4.8))
xs = range(3)
ax.bar(xs, [med[p] for p in PROTOCOLOS], 0.6, color=[CORES[p] for p in PROTOCOLOS])
ax.errorbar(xs, [med[p] for p in PROTOCOLOS],
            yerr=[[med[p] - mn[p] for p in PROTOCOLOS], [mx[p] - med[p] for p in PROTOCOLOS]],
            fmt="none", ecolor="black", capsize=8, linewidth=1.2)
for x, p in zip(xs, PROTOCOLOS):
    ax.annotate(f"{med[p]:.3f}", (x + 0.32, med[p]), va="center", fontsize=9)
ax.set_xticks(list(xs), [NOMES[p] for p in PROTOCOLOS])
ax.set(title="RTT médio entre os 20 pares de PCs\n(linha: do RTT mínimo ao máximo)", ylabel="ms")
ax.margins(y=0.15)
salvar(fig, "2_delay", "Métrica 2 — Delay")


# ---------- 3. Pacotes de roteamento e taxa de transmissao
# soma os 5 roteadores e divide pela duracao da captura
pps, kbps = {}, {}
for p in PROTOCOLOS:
    d = ler("controle", p)
    dur = float(d[0]["duracao_s"])
    pps[p] = sum(int(l["pacotes"]) for l in d) / dur                 # pacotes por segundo
    kbps[p] = sum(int(l["bytes"]) for l in d) * 8 / dur / 1000       # bytes -> kbit/s
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
por_protocolo(axs[0], pps, "Pacotes de roteamento enviados na rede", "pacotes/s", "{:.2f}")
por_protocolo(axs[1], kbps, "Taxa de transmissão usada pelo protocolo", "kbit/s", "{:.2f}")
salvar(fig, "3_controle", "Métrica 3 — Tráfego de controle (rede estável, 120 s)")


# ---------- 4. Queda do link R3-R5
# esquerda: tempo sem conexao de cada protocolo
f = {p: ler("falha_link", p)[0] for p in PROTOCOLOS}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
por_protocolo(axs[0], {p: float(f[p]["interrupcao_s"]) for p in PROTOCOLOS},
              "Tempo com tráfego interrompido (PC1 → PC5)", "segundos", zero="<0.1")

# direita: pacotes de controle com a falha (colorido) x rede estavel no mesmo tempo (cinza)
normal = {p: pps[p] * float(f[p]["duracao_s"]) for p in PROTOCOLOS}
xs = range(3)
b1 = axs[1].bar([x - 0.18 for x in xs], [normal[p] for p in PROTOCOLOS], 0.36, color="#b8b8b8")
b2 = axs[1].bar([x + 0.18 for x in xs], [int(f[p]["pacotes_controle"]) for p in PROTOCOLOS],
                0.36, color=[CORES[p] for p in PROTOCOLOS])
rotular(axs[1], b1, "{:.0f}")
rotular(axs[1], b2)
axs[1].set_xticks(list(xs), [NOMES[p] for p in PROTOCOLOS])
axs[1].set(title="Pacotes de controle em 35 s\n(cinza: rede estável · colorido: com a falha)",
           ylabel="pacotes")
axs[1].margins(y=0.15)
salvar(fig, "4_falha_link", "Métrica 4 — Queda do link R3–R5")