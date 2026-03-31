# dogi
DOGZILLA mods

## Demo quick start (ball detection dashboard)

Ez a demo stream kepet fogad, labdat detektal, majd bekeretezve mutatja a dashboardon.

1. Inditas:

```bash
cd cloud/control
./docker-run.sh
```

2. Dashboard:

- Keresd: http://localhost:5053
- Kovesd: http://localhost:5055

3. Kamera nelkuli teszt stream (RealSense helyett):

```bash
ffmpeg -re -stream_loop -1 -i /path/to/ball_video.mp4 -an -vf scale=640:480 -c:v libx264 -preset veryfast -pix_fmt yuv420p -f rtp rtp://127.0.0.1:5100
```

4. Eredmeny:

- A keresd es a kovesd nezetben is megjelenik a kep.
- A labda bekeretezve latszik mindket nezetben.

5. Leallitas:

```bash
cd cloud/control
./docker-stop.sh
```
