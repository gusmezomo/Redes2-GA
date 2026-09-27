#!/usr/bin/env bash
# Metrica 1: tamanho da tabela de roteamento -> coluna prefixos_total
# Para cada roteador, le o "show ip route" do FRR e conta:
#   prefixos_total   -> redes que o roteador conhece (tamanho da tabela)
#   rotas_aprendidas -> quantas vieram do protocolo (O, R ou B)
#   next_hops        -> caminhos instalados para essas rotas
#                       (maior que rotas_aprendidas = caminhos em paralelo)

cd "$(dirname "$0")/.."

PROTO=$(readlink configs/atual)        # ospf, rip ou bgp (definido pelo rodar.sh)
ARQ="resultados/tabela_rotas_$PROTO.csv"
mkdir -p resultados

# letra que o FRR usa para as rotas de cada protocolo
case $PROTO in
  ospf) LETRA=O ;;
  rip)  LETRA=R ;;
  bgp)  LETRA=B ;;
esac

echo "protocolo,roteador,prefixos_total,rotas_aprendidas,next_hops" > "$ARQ"

for r in r1 r2 r3 r4 r5; do
  tabela=$(docker exec clab-redes-$r vtysh -c "show ip route")

  # rotas em uso (">*") conectadas (C) ou do protocolo, sem a rede de gerencia
  total=$(echo "$tabela" | grep -E "^[C$LETRA]>\*" | grep -v "172.20.20." | wc -l)

  # complemento: so as rotas vindas do protocolo
  aprendidas=$(echo "$tabela" | grep -c "^$LETRA>\*")

  # complemento: caminhos em paralelo, usados na analise
  # de "selecao de rotas". Aparecem em linhas de continuacao "  *   via ..."
  extras=$(echo "$tabela" | grep -cE "^\s+\*\s+via")
  next_hops=$((aprendidas + extras))

  echo "$r: $total prefixos, $aprendidas aprendidas via $PROTO, $next_hops next-hops"
  echo "$PROTO,$r,$total,$aprendidas,$next_hops" >> "$ARQ"
done

echo "Salvo em $ARQ"
