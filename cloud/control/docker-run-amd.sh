#!/usr/bin/env bash
set -euo pipefail

docker build -f Dockerfile.amd -t dogi-control .
docker rm -f dogi >/dev/null 2>&1 || true

docker run -d \
  --name dogi \
  --device /dev/kfd --device /dev/dri \
  --group-add video --group-add render \
  --ipc=host \
  -p 6080:6080 \
  -p 5050-5059:5050-5059 \
  -p 5100:5100/udp \
  -e HSA_OVERRIDE_GFX_VERSION=12.0.1 \
  -e PYTORCH_ROCM_ARCH=gfx1201 \
  -e HIP_VISIBLE_DEVICES=0 \
  -e OLLAMA_IP=127.0.0.1 \
  -e DISPLAY=:0 \
  -v ./Ultralytics:/root/.config/Ultralytics:rw \
  -v ./cache/huggingface:/root/.cache/huggingface:rw \
  -v ./cache/debug:/root/debug:ro \
  dogi-control