#!/usr/bin/env bash
# Mostra a tabela de rotas de cada roteador e testa ping entre todos os PCs
cd "$(dirname "$0")/.."

for r in r1 r2 r3 r4 r5; do
  echo "================ $r: show ip route ================"
  docker exec clab-redes-$r vtysh -c "show ip route"
done

echo
echo "================ Matriz de ping entre PCs ================"
for s in 1 2 3 4 5; do
  linha="pc$s ->"
  for d in 1 2 3 4 5; do
    [[ $s == $d ]] && { linha+="   -  "; continue; }
    if docker exec clab-redes-pc$s ping -c 1 -W 1 192.168.$d.10 >/dev/null 2>&1; then
      linha+="  OK  "
    else
      linha+=" FALHA"
    fi
  done
  echo "$linha"
done
