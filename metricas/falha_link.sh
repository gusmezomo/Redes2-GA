#!/usr/bin/env bash
# =============================================================
# Metrica 4: comportamento com mudanca na topologia
#
# ITENS DO PDF ATENDIDOS:
#   [PDF] criterio 6: "etc." (outras metricas de roteamento)
#   [PDF] definicao: "analise do comportamento dos protocolos diante de
#         alteracoes na conectividade" / "comportamento em situacoes de
#         mudanca da topologia"  -> coluna interrupcao_s
#
# 1. PC1 pinga o PC5 10x por segundo (caminho normal: R1-R3-R5)
# 2. apos 5 s, a interface do R3 que liga ao R5 e desligada
# 3. o protocolo precisa desviar o trafego (ex.: R3-R4-R5)
# 4. tempo de interrupcao = pings perdidos x 0,1 s
# Ao mesmo tempo, conta os pacotes de controle gerados na rede.
#
# Rode com a rede estavel (>= 1 min apos o rodar.sh).
# Uso: ./metricas/falha_link.sh
# Saida: resultados/falha_link_<protocolo>.csv
# =============================================================
cd "$(dirname "$0")/.."

PROTO=$(readlink configs/atual)
ARQ="resultados/falha_link_$PROTO.csv"
TMP=resultados/tmp
mkdir -p "$TMP"

ANTES=5          # segundos antes da falha
DURACAO=35       # duracao total do teste
PINGS=350        # 35 s x 10 pings/s

case $PROTO in
  ospf) FILTRO="ip proto 89" ;;
  rip)  FILTRO="udp port 520" ;;
  bgp)  FILTRO="tcp port 179" ;;
esac

# 1) capturas de controle (iguais as do controle.sh)
for r in r1 r2 r3 r4 r5; do
  docker run --rm --network container:clab-redes-$r \
    --cap-add NET_ADMIN --cap-add NET_RAW \
    --entrypoint timeout ghcr.io/hellt/network-multitool \
    -s INT $((DURACAO + 3)) \
    tcpdump -i any -Q out -n -v -l "$FILTRO" > "$TMP/$r.txt" 2>/dev/null &
done
sleep 2

# 2) ping continuo PC1 -> PC5
docker exec clab-redes-pc1 ping -i 0.1 -c $PINGS -q 192.168.5.10 > "$TMP/ping.txt" &

# ---------------------------------------------------------
# [PDF] MUDANCA NA TOPOLOGIA: desliga a interface eth3 do R3 (link R3-R5)
# ---------------------------------------------------------
sleep $ANTES
docker exec clab-redes-r3 ip link set eth3 down
echo "Link R3-R5 derrubado. Observando..."

wait   # espera o ping e as capturas terminarem

# 4) restaura o link
docker exec clab-redes-r3 ip link set eth3 up
echo "Link restaurado."

# ---------------------------------------------------------
# [PDF] COMPORTAMENTO NA MUDANCA: tempo com o trafego interrompido
# cada ping perdido = 0,1 s sem conectividade
# ---------------------------------------------------------
enviados=$(grep -oE "[0-9]+ packets transmitted" "$TMP/ping.txt" | cut -d' ' -f1)
recebidos=$(grep -oE "[0-9]+ (packets )?received" "$TMP/ping.txt" | cut -d' ' -f1)
perdidos=$((enviados - recebidos))
interrupcao=$(awk "BEGIN {print $perdidos * 0.1}")

# complemento: pacotes de controle gerados para reagir a falha
pacotes=$(cat "$TMP"/r*.txt | grep -c " IP (tos")
bytes=$(cat "$TMP"/r*.txt | grep " IP (tos" \
        | sed -E 's/.*length ([0-9]+)\)$/\1/' | awk '{s += $1} END {print s + 0}')

echo "Pings: $enviados enviados, $perdidos perdidos -> interrupcao de ~$interrupcao s"
echo "Controle durante o teste: $pacotes pacotes, $bytes bytes"

echo "protocolo,duracao_s,pings_enviados,pings_perdidos,interrupcao_s,pacotes_controle,bytes_controle" > "$ARQ"
echo "$PROTO,$DURACAO,$enviados,$perdidos,$interrupcao,$pacotes,$bytes" >> "$ARQ"

rm -rf "$TMP"
echo "Salvo em $ARQ"
