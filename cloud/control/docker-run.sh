#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Valid IP format for parameter running with IP: $1"
else
    echo "Invalid IP format for parameter: '${1:-}' (Please provide X.X.X.X address)"
    exit 1
fi

ROBOT_IP="$1"

docker build -t dogi-control .
docker rm -f dogi >/dev/null 2>&1 || true

docker run -d \
  --name dogi \
  --gpus '"device=0"' \
  -p 5002:5002/udp \
  -p 6080:6080 \
  -p 5050-5059:5050-5059 \
  -p 5100:5100/udp \
  -e DISPLAY=:0 \
  -e ROBOT_IP="${ROBOT_IP}" \
  -v ./Ultralytics:/root/.config/Ultralytics:rw \
  -v ./cache/huggingface:/root/.cache/huggingface:rw \
  -v ./cache/debug:/root/debug:ro \
  dogi-control
