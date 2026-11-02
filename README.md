# Kindle weather display

Landscape weather dashboard for a jailbroken Kindle Paperwhite 3.

- `render.py` draws the picture from the free Open-Meteo forecast (`python render.py --sample` for a test image).
- `.github/workflows/render.yml` redraws it every 15 minutes and publishes it with GitHub Pages.
- `kindle/weather/` is a KUAL extension: copy it to the Kindle's `extensions` folder and set `IMAGE_URL` in `bin/config.sh`.

To exit the display on the Kindle, hold the power button and restart.

Fonts: Inter (SIL Open Font License, see `fonts/OFL.txt`).
