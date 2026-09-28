#!/usr/bin/env bash
# Roteiro do video: rotas aprendidas, conectividade e queda do link R3-R5.
# Antes: ./scripts/rodar.sh <protocolo> e esperar ~1 min.
cd "$(dirname "$0")/.."
PROTO=$(readlink configs/atual)

pausa()   { read -rp "[Enter]"; echo; }
executa() { echo "\$ $1"; eval "$1"; }

# um ping do PC1 ao PC5; mostra OK com o TTL, ou "sem resposta"
testa_ping() {
  saida=$(docker exec clab-redes-pc1 ping -c 1 -W 1 192.168.5.10 2>/dev/null)
  ttl=$(echo "$saida" | grep -o "ttl=[0-9]*")
  if [ -n "$ttl" ]; then echo "OK ($ttl)"; else echo "sem resposta"; fi
}

clear
echo "Protocolo: ${PROTO^^}"
echo
pausa

echo "1. Rotas que o R1 aprendeu pelo ${PROTO^^}"
executa "docker exec clab-redes-r1 vtysh -c 'show ip route $PROTO'"
pausa

echo "2. Ping entre todos os PCs"
executa "./scripts/verificar.sh | tail -n 6"
pausa

echo "3. Queda do link R3-R5"
echo
echo "Caminho do R3 ate a rede do PC5 antes da queda:"
executa "docker exec clab-redes-r3 ip route show 192.168.5.0/24"
echo
echo "Ping PC1 -> PC5 antes da queda:"
for i in 1 2 3; do echo "  $(testa_ping)"; sleep 1; done
pausa

echo "Derrubando o link R3-R5:"
executa "docker exec clab-redes-r3 ip link set eth3 down"
echo
echo "Ping PC1 -> PC5 a cada segundo, ate a conexao voltar:"
SECONDS=0
while true; do
  r=$(testa_ping)
  echo "  ${SECONDS}s: $r"
  [[ $r == OK* ]] && break
  [ $SECONDS -ge 60 ] && { echo "  (sem conexao apos 60 s)"; break; }
  sleep 1
done
tempo=$SECONDS
for i in 1 2 3; do sleep 1; echo "  $(testa_ping)"; done
echo
echo "Conexao restabelecida em ~${tempo} s."
echo
echo "Caminho do R3 ate a rede do PC5 depois da queda:"
executa "docker exec clab-redes-r3 ip route show 192.168.5.0/24"
pausa

echo "Religando o link R3-R5:"
executa "docker exec clab-redes-r3 ip link set eth3 up"