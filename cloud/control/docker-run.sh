#!/usr/bin/env bash

docker build -t dogi-control .
docker rm -f dogi >/dev/null 2>&1 || true

docker run -d \
  --name dogi \
  --gpus '"device=0"' \
  -p 6080:6080 \
  -p 5050-5059:5050-5059 \
  -p 5100:5100/udp \
  -e DISPLAY=:0 \
  -v ./Ultralytics:/root/.config/Ultralytics:rw \
  -v ./cache/huggingface:/root/.cache/huggingface:rw \
  -v ./cache/debug:/root/debug:ro \
  dogi-control
