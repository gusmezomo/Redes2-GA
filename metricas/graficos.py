# /// script
# dependencies = ["matplotlib"]
# ///
"""
Criterio 7: graficos comparando os tres protocolos em cada metrica.

Le os CSVs de resultados/ e gera um PNG por metrica em graficos/:
  1_tabela_rotas.png  - prefixos, rotas aprendidas e next-hops por roteador
  2_delay.png         - RTT medio e roteadores atravessados
  3_controle.png      - pacotes/s, taxa (kbit/s) e memoria de cada protocolo
  4_convergencia.png  - tempo de interrupcao apos falha e controle gerado

Uso: uv run metricas/graficos.py
     (o uv instala o matplotlib automaticamente, pelo bloco "script" acima)
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")                     # gera arquivos, sem abrir janelas
import matplotlib.pyplot as plt

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.makedirs("graficos", exist_ok=True)

PROTOCOLOS = ["ospf", "rip", "bgp"]
NOMES = {"ospf": "OSPF", "rip": "RIP", "bgp": "BGP"}
CORES = {"ospf": "#2a78c7", "rip": "#e08a1e", "bgp": "#3a9a5b"}
ROTEADORES = ["r1", "r2", "r3", "r4", "r5"]

plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
                     "grid.alpha": 0.3, "axes.axisbelow": True})


def ler(nome):
    with open(f"resultados/{nome}.csv") as f:
        return list(csv.DictReader(f))


def rotular(ax, barras, fmt="{:g}", zero=None):
    for b in barras:
        texto = zero if (zero and b.get_height() == 0) else fmt.format(b.get_height())
        ax.annotate(texto,
                    (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=9,
                    xytext=(0, 2), textcoords="offset points")


def barras_por_protocolo(ax, valores, titulo, ylabel, fmt="{:g}"):
    """Uma barra por protocolo."""
    b = ax.bar([NOMES[p] for p in PROTOCOLOS], [valores[p] for p in PROTOCOLOS],
               color=[CORES[p] for p in PROTOCOLOS], width=0.6)
    rotular(ax, b, fmt)
    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.margins(y=0.15)


def barras_agrupadas(ax, grupos, valor, titulo, ylabel, zero=None):
    """Para cada grupo (ex.: roteador), uma barra de cada protocolo lado a lado."""
    largura = 0.26
    for i, p in enumerate(PROTOCOLOS):
        xs = [g + (i - 1) * largura for g in range(len(grupos))]
        b = ax.bar(xs, [valor(p, g) for g in grupos], largura,
                   label=NOMES[p], color=CORES[p])
        rotular(ax, b, zero=zero)
    ax.set_xticks(range(len(grupos)))
    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.margins(y=0.15)


def salvar(fig, nome, titulo):
    fig.suptitle(titulo, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"graficos/{nome}.png", dpi=150)
    plt.close(fig)
    print(f"graficos/{nome}.png")


# ---------------------------------------------------------------- 1. tabela
dados = ler("tabela_rotas")
v = {(l["protocolo"], l["roteador"]): l for l in dados}
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
barras_agrupadas(axs[0], ROTEADORES,
                 lambda p, r: int(v[(p, r)]["rotas_aprendidas"]),
                 "Rotas aprendidas (de 16 prefixos no total)", "rotas")
barras_agrupadas(axs[1], ROTEADORES,
                 lambda p, r: int(v[(p, r)]["next_hops"]),
                 "Next-hops instalados (> rotas = caminhos em paralelo)", "next-hops")
for ax in axs:
    ax.set_xticklabels([r.upper() for r in ROTEADORES])
axs[1].legend()
salvar(fig, "1_tabela_rotas", "Métrica 1 — Tabela de roteamento")

# ---------------------------------------------------------------- 2. delay
dados = ler("delay")
rtt = {p: [float(l["rtt_medio_ms"]) for l in dados if l["protocolo"] == p]
       for p in PROTOCOLOS}
saltos = {p: sum(int(l["roteadores_no_caminho"]) for l in dados if l["protocolo"] == p)
          for p in PROTOCOLOS}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
barras_por_protocolo(axs[0], {p: sum(rtt[p]) / len(rtt[p]) for p in PROTOCOLOS},
                     "RTT médio entre os 20 pares de PCs", "ms", "{:.3f}")
barras_por_protocolo(axs[1], saltos,
                     "Roteadores atravessados (soma dos 20 pares)", "roteadores")
salvar(fig, "2_delay", "Métrica 2 — Delay e caminhos")

# ---------------------------------------------------------------- 3. controle
dados = ler("controle")
def soma(p, campo):
    return sum(float(l[campo]) for l in dados if l["protocolo"] == p)
def media(p, campo):
    xs = [float(l[campo]) for l in dados if l["protocolo"] == p]
    return sum(xs) / len(xs)
fig, axs = plt.subplots(1, 3, figsize=(15, 4.8))
barras_por_protocolo(axs[0], {p: soma(p, "pacotes_por_s") for p in PROTOCOLOS},
                     "Pacotes de controle na rede", "pacotes/s", "{:.2f}")
barras_por_protocolo(axs[1], {p: soma(p, "bytes_por_s") * 8 / 1000 for p in PROTOCOLOS},
                     "Taxa usada pelo protocolo", "kbit/s", "{:.2f}")
barras_por_protocolo(axs[2], {p: media(p, "memoria_kb") / 1024 for p in PROTOCOLOS},
                     "Memória do processo (média/roteador)", "MB", "{:.1f}")
salvar(fig, "3_controle", "Métrica 3 — Tráfego de controle e memória (regime normal, 120 s)")

# ---------------------------------------------------------------- 4. convergencia
dados = ler("convergencia")
c = {(l["protocolo"], l["modo"]): l for l in dados}
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
modos = ["link", "silenciosa"]
barras_agrupadas(axs[0], modos,
                 lambda p, m: float(c[(p, m)]["interrupcao_s"]),
                 "Tempo com tráfego interrompido (PC1 → PC5)", "segundos",
                 zero="<0.1")
axs[0].set_xticklabels(["Cabo puxado\n(interface cai)", "Falha silenciosa\n(perda de 100%)"])
axs[0].legend()
# controle gerado na falha de link, comparado ao regime normal no mesmo intervalo
ctl = ler("controle")
normal = {p: sum(float(l["pacotes_por_s"]) for l in ctl if l["protocolo"] == p)
          * float(c[(p, "link")]["janela_s"]) for p in PROTOCOLOS}
falha = {p: int(c[(p, "link")]["pacotes_controle"]) for p in PROTOCOLOS}
largura = 0.35
xs = range(len(PROTOCOLOS))
b1 = axs[1].bar([x - largura / 2 for x in xs], [normal[p] for p in PROTOCOLOS], largura,
                label="Regime normal", color="#b8b8b8")
b2 = axs[1].bar([x + largura / 2 for x in xs], [falha[p] for p in PROTOCOLOS], largura,
                color=[CORES[p] for p in PROTOCOLOS])
rotular(axs[1], b1, "{:.0f}")
rotular(axs[1], b2, "{:.0f}")
axs[1].set_xticks(list(xs))
axs[1].set_xticklabels([NOMES[p] for p in PROTOCOLOS])
axs[1].set_title("Pacotes de controle em 35 s\n(cinza: regime normal · colorido: com falha de link)")
axs[1].set_ylabel("pacotes")
axs[1].margins(y=0.15)
salvar(fig, "4_convergencia", "Métrica 4 — Reconvergência após falha do link R3–R5")