#!/usr/bin/env bash
# Metrica 3: pacotes de roteamento e taxa de transmissao
# "quantidade de pacotes de roteamento enviados na rede" -> coluna pacotes
# "taxa de transmissao utilizada pelo protocolo"          -> coluna bytes
#         (o graficos.py converte bytes em kbit/s)
#
# Captura por DURACAO segundos os pacotes do protocolo que cada
# roteador ENVIA, e conta pacotes e bytes.
# Rode com a rede estavel (>= 1 min apos o rodar.sh).
#
# O tcpdump roda num container auxiliar que compartilha a rede
# do roteador (--network container:...), pois a imagem do FRR
# nao tem tcpdump.

cd "$(dirname "$0")/.."

PROTO=$(readlink configs/atual)
ARQ="resultados/controle_$PROTO.csv"
DURACAO=120
TMP=resultados/tmp
mkdir -p "$TMP"

# "assinatura" de cada protocolo no pacote
case $PROTO in
  ospf) FILTRO="ip proto 89" ;;     # OSPF tem numero de protocolo IP proprio
  rip)  FILTRO="udp port 520" ;;
  bgp)  FILTRO="tcp port 179" ;;
esac

echo "Capturando $DURACAO s de '$FILTRO' nos 5 roteadores..."

# 1) dispara as 5 capturas ao mesmo tempo (o & manda para segundo plano)
for r in r1 r2 r3 r4 r5; do
  docker run --rm --network container:clab-redes-$r \
    --cap-add NET_ADMIN --cap-add NET_RAW \
    --entrypoint timeout ghcr.io/hellt/network-multitool \
    -s INT $DURACAO \
    tcpdump -i any -Q out -n -v -l "$FILTRO" > "$TMP/$r.txt" 2>/dev/null &
done
wait   # espera as 5 terminarem

# 2) conta. Com -v, cada pacote tem uma linha "IP (tos ..., length N)",
#    onde N e o tamanho do pacote IP em bytes.
echo "protocolo,roteador,duracao_s,pacotes,bytes" > "$ARQ"
for r in r1 r2 r3 r4 r5; do
  # QUANTIDADE DE PACOTES DE ROTEAMENTO ENVIADOS NA REDE
  # uma linha "IP (tos" = um pacote enviado
  pacotes=$(grep -c " IP (tos" "$TMP/$r.txt")
  # TAXA DE TRANSMISSAO UTILIZADA PELO PROTOCOLO
  # soma o tamanho (length N) de todos os pacotes; a taxa e
  # bytes / DURACAO, calculada em kbit/s no graficos.py
  bytes=$(grep " IP (tos" "$TMP/$r.txt" \
          | sed -E 's/.*length ([0-9]+)\)$/\1/' \
          | awk '{s += $1} END {print s + 0}')
  echo "$r: $pacotes pacotes, $bytes bytes"
  echo "$PROTO,$r,$DURACAO,$pacotes,$bytes" >> "$ARQ"
done

rm -rf "$TMP"
echo "Salvo em $ARQ"
