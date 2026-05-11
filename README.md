# dogi
DOGZILLA — control modules and quick start

## Demo quick start

Follow these minimal steps to run the controller.

1) Start (NVIDIA / CUDA):

```bash
cd cloud/control
./docker-run.sh <robot_ip> [mode]
```

2) Start (AMD / ROCm):

```bash
cd cloud/control
./docker-run-amd.sh <robot_ip> [mode]
```

Modes:

- `keresd` — only detector view
- `kovesd` — only follower view
- `fsm` — unified state-machine mode (central detection + motion logic)

Quick examples:

```bash
./docker-run.sh <robot_ip> keresd
./docker-run.sh <robot_ip> kovesd
./docker-run.sh <robot_ip> fsm
```

## Dashboard / web UI

Accessible local ports (Flask apps):

- Keresd (detect): http://localhost:5053
- Kovesd (follow): http://localhost:5055
- FSM (state machine): http://localhost:5056

## Logging

Controller logs are written to a single file: `/tmp/dogi_logs/dogi.log` inside the container.

Tail the full log live:

```bash
docker exec dogi tail -f /tmp/dogi_logs/dogi.log
```

Filter a minimal useful set (example: MOTOR + KERESD):

```bash
docker exec dogi tail -f /tmp/dogi_logs/dogi.log | grep -E '\[MOTOR\]|\[KERESD\]'
```

Log prefixes (short):

- **[FSM]** — state machine / state changes
- **[KERESD]** — detection / search logic
- **[KOVESD]** — follow logic
- **[MOTOR]** — motor commands (start/stop/turn)
- **[PERF]** — YOLO/video performance and latency

## Camera-less test stream

You can feed a looped video (ball sample) instead of a camera feed:

```bash
ffmpeg -re -stream_loop -1 -i /path/to/ball_video.mp4 -an -vf scale=640:480 -c:v libx264 -preset veryfast -pix_fmt yuv420p -f rtp rtp://127.0.0.1:5100
```

## Expected behaviour / results

Brief (FSM and modes):

- FSM: central state machine handling DETECT/FOLLOW transitions. It issues a safe stop command to halt the previous state's motions, waits for those motions to stop, then activates the new motion logic, ensures no overlapping. Mode change happens when the ball is no longer detected for about 5 seconds (FOLLOW -> DETECT) or when a ball is detected. (DETECT -> FOLLOW)
- Standalone: `keresd` and `kovesd` can run independently (they perform detection + movement). In FSM mode detection is centralized and FSM commands the motion modules.

## Stop

```bash
cd cloud/control
./docker-stop.sh
```
