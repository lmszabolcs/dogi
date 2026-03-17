# dogi
DOGZILLA mods

## PoC quick start (ball detection dashboard)

Ez a PoC stream kepet fogad, labdat detektal, majd bekeretezve mutatja a dashboardon.

1. Inditas:

```bash
cd cloud/control
docker compose up -d --build
```

2. Dashboard:

- http://localhost:5055

3. Kamera nelkuli teszt stream (RealSense helyett):

```bash
ffmpeg -re -stream_loop -1 -i /path/to/ball_video.mp4 -an -vf scale=640:480 -c:v libx264 -preset veryfast -pix_fmt yuv420p -f rtp rtp://127.0.0.1:5100
```

4. Eredmeny:

- A labda a kovesd nezetben bekeretezve jelenik meg.
