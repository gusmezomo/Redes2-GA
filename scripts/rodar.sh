#!/usr/bin/env bash
# Sobe o laboratorio com o protocolo escolhido: ./scripts/rodar.sh ospf|rip|bgp
set -euo pipefail
cd "$(dirname "$0")/.."

PROTO="${1:-}"
if [[ ! -d "configs/$PROTO" || -z "$PROTO" ]]; then
  echo "uso: $0 ospf|rip|bgp"; exit 1
fi

echo ">> Derrubando laboratorio anterior (se existir)..."
sudo containerlab destroy -t topologia.clab.yml --cleanup >/dev/null 2>&1 || true

echo ">> Selecionando cenario: $PROTO"
ln -sfn "$PROTO" configs/atual

echo ">> Subindo laboratorio..."
sudo containerlab deploy -t topologia.clab.yml
