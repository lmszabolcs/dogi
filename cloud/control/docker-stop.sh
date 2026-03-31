#!/usr/bin/env bash
set -euo pipefail

docker stop dogi >/dev/null 2>&1 || true
docker rm dogi >/dev/null 2>&1 || true

echo "Stopped and removed container: dogi"
