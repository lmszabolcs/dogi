#!/bin/bash

# Builds the onboard docker image (named "onboard") 
# and runs the container (also named "onboard") with 
# the specified IP address as an environment variable.

if [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Valid IP format for parameter running with IP: $1"
else
    echo "Invalid IP format for parameter: '$1' (Please provide X.X.X.X address)"
    exit 1
fi

# Build docker image in the current directory
docker build -t onboard .

# Run the docker container with specified IP address
docker run \
    --name onboard \
    --device /dev/video0:/dev/video4 \
    --device /dev/serial0:/dev/serial0 \
    --network host \
    -e VIDEO_DST=$1 \
    -e VIDEO_PORT=5100 \
    -d \
    onboard