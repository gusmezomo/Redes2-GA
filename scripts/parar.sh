#!/usr/bin/env bash
# Derruba o laboratorio e limpa tudo que o containerlab criou
set -euo pipefail
cd "$(dirname "$0")/.."
sudo containerlab destroy -t topologia.clab.yml --cleanup
