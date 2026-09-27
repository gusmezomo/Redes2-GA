#!/usr/bin/env bash
# Metrica 2: delay entre os PCs
# Para cada par de PCs (20 pares), envia 10 pings e guarda o
# tempo de ida e volta (RTT) minimo, medio e maximo, e a perda.
cd "$(dirname "$0")/.."

PROTO=$(readlink configs/atual)
ARQ="resultados/delay_$PROTO.csv"
mkdir -p resultados

echo "protocolo,origem,destino,rtt_min_ms,rtt_medio_ms,rtt_max_ms,perda_pct" > "$ARQ"

for o in 1 2 3 4 5; do
  for d in 1 2 3 4 5; do
    [ $o = $d ] && continue

    # 10 pings entre o par de PCs
    saida=$(docker exec clab-redes-pc$o ping -c 10 -i 0.2 -q 192.168.$d.10)

    # o valor usado e o do meio (avg = rtt medio)
    # ultima linha do ping: "rtt min/avg/max/mdev = 0.061/0.089/0.181/0.030 ms"
    rtt=$(echo "$saida" | tail -n 1 | cut -d= -f2 | cut -d/ -f1-3 | tr -d ' ' | tr / ,)
    # complemento: perda de pacotes
    # linha de resumo: "10 packets transmitted, 10 received, 0% packet loss ..."
    perda=$(echo "$saida" | grep -oE "[0-9.]+% packet loss" | cut -d% -f1)

    echo "pc$o -> pc$d: rtt min,medio,max = $rtt ms, perda $perda%"
    echo "$PROTO,pc$o,pc$d,$rtt,$perda" >> "$ARQ"
  done
done

echo "Salvo em $ARQ"
