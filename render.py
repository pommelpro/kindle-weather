#!/usr/bin/env python3
"""Render a landscape weather dashboard for a Kindle Paperwhite 3 (1448x1072).

Data comes from Open-Meteo (free, no API key). Output:
  out/weather.png  - rotated to the Kindle's native portrait (1072x1448), 16-level grayscale
  out/preview.png  - the same image in landscape, for looking at on a computer

Usage:
  python render.py            # fetch live forecast
  python render.py --sample   # use built-in sample data (no internet needed)
"""

import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- settings
LOCATION_NAME = "Chicago · 60618"
LATITUDE = 41.9466
LONGITUDE = -87.7045
TIMEZONE = "America/Chicago"
HOURLY_STEP = 2           # hours between columns
HOURLY_COLS = 6           # number of hourly columns
DAYS_SHOWN = 8            # today + next 7
# Front light, in percent. "Dark" = 30 min before sunset until 30 min after sunrise.
LIGHT_DAY = 50
LIGHT_NIGHT = 50
# Screen layout: "portrait" (days down the left) or "landscape"
LAYOUT = "portrait"
PORTRAIT_DAYS = 5          # today + next 4
# Portrait: 0 = charging port at the bottom (normal), 180 = port at the top
PORTRAIT_ROTATE = 0
# Landscape only - which way to turn the picture for the Kindle:
#   90  = Kindle's bottom edge (logo side) on the RIGHT when mounted
#   -90 = Kindle's bottom edge on the LEFT
ROTATE = -90

W, H = 1448, 1072          # landscape canvas
S = 2                      # supersampling for smooth edges
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

BLACK, DARK, MID, LIGHT, PALE, WHITE = 0, 70, 130, 190, 228, 255


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size * S)


F = {
    "huge": lambda: font("InterDisplay-SemiBold.otf", 250),
    "cond": lambda: font("InterDisplay-SemiBold.otf", 56),
    "head": lambda: font("Inter-SemiBold.otf", 32),
    "body": lambda: font("Inter-Medium.otf", 36),
    "bodyb": lambda: font("Inter-Bold.otf", 36),
    "small": lambda: font("Inter-Medium.otf", 26),
    "smallb": lambda: font("Inter-Bold.otf", 26),
    "day": lambda: font("Inter-Bold.otf", 44),
    "hi": lambda: font("InterDisplay-SemiBold.otf", 60),
    "lo": lambda: font("InterDisplay-Medium.otf", 48),
    "hour": lambda: font("Inter-SemiBold.otf", 34),
    "htemp": lambda: font("InterDisplay-SemiBold.otf", 64),
    "hrain": lambda: font("Inter-Medium.otf", 34),
    "hrainb": lambda: font("Inter-Bold.otf", 34),
    "drain": lambda: font("Inter-Medium.otf", 34),
    "drainb": lambda: font("Inter-Bold.otf", 34),
}
F = {k: v() for k, v in F.items()}


# ---------------------------------------------------------------- data
def fetch():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "forecast_days": DAYS_SHOWN + 1,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "weather_code,wind_speed_10m,wind_gusts_10m,is_day",
        "hourly": "temperature_2m,precipitation_probability,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,sunrise,sunset",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def sample():
    """Fake but realistic data shaped like Open-Meteo's response."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    start = now.replace(hour=0)
    hours = [start + timedelta(hours=i) for i in range(24 * (DAYS_SHOWN + 1))]
    temps = [55 + 8 * math.sin((h.hour - 9) / 24 * 2 * math.pi) - 0.4 * (i // 24)
             for i, h in enumerate(hours)]
    pops = [max(0, min(100, int(70 * math.sin(i / 7) ** 2 - 15))) for i in range(len(hours))]
    days = [start + timedelta(days=d) for d in range(DAYS_SHOWN + 1)]
    codes = [3, 2, 61, 3, 1, 0, 2, 80, 71]
    return {
        "current": {
            "time": now.strftime("%Y-%m-%dT%H:%M"),
            "temperature_2m": 60.2, "apparent_temperature": 58.1,
            "relative_humidity_2m": 80, "weather_code": 3,
            "wind_speed_10m": 4.3, "wind_gusts_10m": 11.0, "is_day": 0,
        },
        "hourly": {
            "time": [h.strftime("%Y-%m-%dT%H:%M") for h in hours],
            "temperature_2m": temps,
            "precipitation_probability": pops,
            "weather_code": [61 if p > 50 else 3 for p in pops],
            "is_day": [1 if 7 <= h.hour < 18 else 0 for h in hours],
        },
        "daily": {
            "time": [d.strftime("%Y-%m-%d") for d in days],
            "weather_code": codes[: len(days)],
            "temperature_2m_max": [64, 63, 71, 60, 56, 50, 50, 50, 47][: len(days)],
            "temperature_2m_min": [55, 58, 61, 53, 48, 42, 43, 44, 39][: len(days)],
            "precipitation_probability_max": [10, 20, 80, 30, 5, 0, 15, 60, 40][: len(days)],
            "sunrise": [d.strftime("%Y-%m-%dT06:28") for d in days],
            "sunset": [d.strftime("%Y-%m-%dT16:39") for d in days],
        },
    }


def describe(code):
    if code in (0,):
        return "Clear"
    if code == 1:
        return "Mostly clear"
    if code == 2:
        return "Partly cloudy"
    if code == 3:
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 66, 80, 81):
        return "Rain"
    if code in (65, 67, 82):
        return "Heavy rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorms"
    return "—"


def kind(code):
    if code in (0, 1):
        return "clear"
    if code == 2:
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    return "cloudy"


def hour_label(dt):
    h = dt.hour % 12 or 12
    return f"{h} {'AM' if dt.hour < 12 else 'PM'}"


# ---------------------------------------------------------------- drawing helpers
class Canvas:
    def __init__(self):
        self.img = Image.new("L", (W * S, H * S), WHITE)
        self.d = ImageDraw.Draw(self.img)

    def p(self, *v):
        return [x * S for x in v]

    def text(self, xy, s, f, fill=BLACK, anchor="la"):
        self.d.text((xy[0] * S, xy[1] * S), s, font=F[f], fill=fill, anchor=anchor)

    def width(self, s, f):
        return self.d.textlength(s, font=F[f]) / S

    def line(self, pts, fill=BLACK, w=2):
        self.d.line([c * S for pt in pts for c in pt], fill=fill, width=int(w * S), joint="curve")

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w=1, r=0):
        self.d.rounded_rectangle(self.p(x0, y0, x1, y1), radius=r * S, fill=fill,
                                 outline=outline, width=int(w * S))

    def circle(self, cx, cy, r, fill=None, outline=None, w=1):
        self.d.ellipse(self.p(cx - r, cy - r, cx + r, cy + r), fill=fill,
                       outline=outline, width=int(w * S))

    def poly(self, pts, fill):
        self.d.polygon([c * S for pt in pts for c in pt], fill=fill)


def draw_cloud(c, cx, cy, size, fill=PALE, edge=DARK):
    """Cloud centred at (cx, cy), roughly `size` wide."""
    u = size / 100
    parts = [(-22, 8, 22), (4, -6, 30), (28, 10, 18)]
    base = (-42, 8, 44, 28)
    lw = max(2.5, 4 * u)
    for grow, colour in ((lw, edge), (0, fill)):
        for dx, dy, r in parts:
            c.circle(cx + dx * u, cy + dy * u, r * u + grow, fill=colour)
        c.rect(cx + base[0] * u - grow, cy + base[1] * u - grow,
               cx + base[2] * u + grow, cy + base[3] * u + grow, fill=colour, r=10 * u + grow)


def draw_sun(c, cx, cy, size):
    u = size / 100
    r = 20 * u
    for i in range(8):
        a = i * math.pi / 4
        c.line([(cx + math.cos(a) * (r + 8 * u), cy + math.sin(a) * (r + 8 * u)),
                (cx + math.cos(a) * (r + 20 * u), cy + math.sin(a) * (r + 20 * u))],
               fill=DARK, w=max(2.5, 5 * u))
    c.circle(cx, cy, r, fill=MID, outline=DARK, w=max(2.5, 4 * u))


def draw_moon(c, cx, cy, size):
    u = size / 100
    c.circle(cx, cy, 24 * u, fill=MID, outline=DARK, w=max(2.5, 4 * u))
    c.circle(cx + 14 * u, cy - 10 * u, 22 * u, fill=WHITE)


def draw_icon(c, code, cx, cy, size, day=True):
    k = kind(code)
    u = size / 100
    if k == "clear":
        (draw_sun if day else draw_moon)(c, cx, cy, size)
        return
    if k == "partly":
        (draw_sun if day else draw_moon)(c, cx - 18 * u, cy - 16 * u, size * 0.75)
        draw_cloud(c, cx + 8 * u, cy + 8 * u, size * 0.8)
        return
    shift = -10 * u if k in ("rain", "snow", "storm", "fog") else 0
    draw_cloud(c, cx, cy + shift, size, fill=LIGHT if k in ("rain", "storm") else PALE)
    lw = max(2.5, 5 * u)
    if k == "rain":
        for dx in (-22, 0, 22):
            c.line([(cx + dx * u, cy + 30 * u), (cx + (dx - 8) * u, cy + 48 * u)], fill=DARK, w=lw)
    elif k == "snow":
        for dx in (-22, 0, 22):
            x, y, r = cx + dx * u, cy + 40 * u, 8 * u
            for a in (0, 60, 120):
                t = math.radians(a)
                c.line([(x - r * math.cos(t), y - r * math.sin(t)),
                        (x + r * math.cos(t), y + r * math.sin(t))], fill=DARK, w=lw * 0.7)
    elif k == "storm":
        c.poly([(cx + 4 * u, cy + 18 * u), (cx - 12 * u, cy + 42 * u), (cx, cy + 42 * u),
                (cx - 8 * u, cy + 60 * u), (cx + 16 * u, cy + 32 * u), (cx + 3 * u, cy + 32 * u)],
               fill=BLACK)
    elif k == "fog":
        for i, dy in enumerate((32, 44)):
            c.line([(cx - (36 - 8 * i) * u, cy + dy * u), (cx + (36 - 8 * i) * u, cy + dy * u)],
                   fill=DARK, w=lw)


def draw_drop(c, cx, cy, size, fill=DARK):
    r = size * 0.32
    c.circle(cx, cy + size * 0.18, r, fill=fill)
    c.poly([(cx - r * 0.95, cy + size * 0.1), (cx, cy - size * 0.42), (cx + r * 0.95, cy + size * 0.1)],
           fill=fill)


def rain_label(c, x, y, p, f, fb, drop):
    """Drop icon + percent, centred on x. Bold and dark once rain is likely."""
    likely = p >= 30
    s = f"{p}%"
    fnt = fb if p >= 50 else f
    w = drop * 0.7 + 8 + c.width(s, fnt)
    x0 = x - w / 2
    draw_drop(c, x0 + drop * 0.35, y, drop, fill=DARK if likely else LIGHT)
    c.text((x0 + drop * 0.7 + 8, y), s, fnt, fill=BLACK if likely else MID, anchor="lm")


# ---------------------------------------------------------------- layout
def render(data):
    global W, H
    W, H = 1448, 1072
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    cur = data["current"]
    hourly = data["hourly"]
    daily = data["daily"]
    c = Canvas()
    M = 48

    # --- header
    c.text((M, 44), LOCATION_NAME, "head", fill=DARK, anchor="lm")
    c.text((W - M, 44), now.strftime("%A, %b ") + str(now.day) + "  ·  Updated "
           + now.strftime("%-I:%M %p"), "head", fill=DARK, anchor="rm")
    c.line([(M, 82), (W - M, 82)], fill=LIGHT, w=2)

    # --- current conditions
    is_day = bool(cur.get("is_day", 1))
    draw_icon(c, cur["weather_code"], M + 120, 240, 210, day=is_day)
    temp = f"{round(cur['temperature_2m'])}°"
    c.text((M + 270, 240), temp, "huge", anchor="lm")
    tx = M + 270 + c.width(temp, "huge") + 50
    tx = max(tx, 760)
    c.text((tx, 132), describe(cur["weather_code"]), "cond", anchor="lm")
    hi, lo = round(daily["temperature_2m_max"][0]), round(daily["temperature_2m_min"][0])
    rows = [
        ("Feels like", f"{round(cur['apparent_temperature'])}°"),
        ("High / Low", f"{hi}° / {lo}°"),
        ("Rain today", f"{round(daily['precipitation_probability_max'][0] or 0)}%"),
        ("Wind", f"{round(cur['wind_speed_10m'])} mph"
                 + (f", gusts {round(cur['wind_gusts_10m'])}" if cur.get('wind_gusts_10m', 0) - cur['wind_speed_10m'] >= 8 else "")),
        ("Humidity", f"{round(cur['relative_humidity_2m'])}%"),
    ]
    for i, (k, v) in enumerate(rows):
        y = 196 + i * 46
        c.text((tx, y), k, "body", fill=MID, anchor="lm")
        c.text((tx + 215, y), v, "bodyb", anchor="lm")
    c.line([(M, 410), (W - M, 410)], fill=LIGHT, w=2)

    # --- hourly strip: time / temp / rain chance per column
    times = [datetime.fromisoformat(t).replace(tzinfo=tz) for t in hourly["time"]]
    # first column is ~2 hours out (e.g. at 9:05 PM it starts at 11 PM)
    start = next(i for i, t in enumerate(times) if t > now + timedelta(hours=HOURLY_STEP - 1))
    idx = [start + HOURLY_STEP * n for n in range(HOURLY_COLS)]
    colw = (W - 2 * M) / HOURLY_COLS
    for n, i in enumerate(idx):
        x = M + colw * (n + 0.5)
        t = hourly["temperature_2m"][i]
        p = round(hourly["precipitation_probability"][i] or 0)
        c.text((x, 450), hour_label(times[i]), "hour", fill=DARK, anchor="mm")
        c.text((x, 512), f"{round(t)}°", "htemp", anchor="mm")
        rain_label(c, x, 570, p, "hrain", "hrainb", 26)
        if n:
            c.line([(M + colw * n, 432), (M + colw * n, 586)], fill=PALE, w=2)
    c.line([(M, 606), (W - M, 606)], fill=LIGHT, w=2)

    # --- daily row
    dcol = (W - 2 * M) / DAYS_SHOWN
    for d in range(DAYS_SHOWN):
        x = M + dcol * (d + 0.5)
        date = datetime.fromisoformat(daily["time"][d])
        name = "Today" if d == 0 else date.strftime("%a")
        if d == 0:
            c.rect(x - dcol / 2 + 6, 622, x + dcol / 2 - 6, 1058, fill=PALE, r=16)
        c.text((x, 668), name, "day", anchor="mm")
        draw_icon(c, daily["weather_code"][d], x, 790, 120)
        hi = round(daily["temperature_2m_max"][d])
        lo = round(daily["temperature_2m_min"][d])
        c.text((x, 912), f"{hi}°", "hi", anchor="mm")
        c.text((x, 970), f"{lo}°", "lo", fill=MID, anchor="mm")
        rain_label(c, x, 1024, round(daily["precipitation_probability_max"][d] or 0),
                   "drain", "drainb", 26)

    img = c.img.resize((W, H), Image.LANCZOS)
    # e-ink shows 16 gray levels; snap to them so nothing dithers oddly
    img = img.point(lambda v: min(255, round(v / 17) * 17))
    return img


def render_portrait(data):
    global W, H
    W, H = 1072, 1448                     # Canvas reads these
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    cur, hourly, daily = data["current"], data["hourly"], data["daily"]
    c = Canvas()
    M = 40

    # header
    c.text((M, 44), LOCATION_NAME, "head", fill=DARK, anchor="lm")
    c.text((W - M, 44), now.strftime("%a, %b ") + str(now.day) + "  ·  "
           + now.strftime("%-I:%M %p"), "head", fill=DARK, anchor="rm")
    c.line([(M, 82), (W - M, 82)], fill=LIGHT, w=2)

    # left column: 5 days stacked
    LX0, LX1 = M, 400
    top, bottom = 96, H - 24
    rowh = (bottom - top) / PORTRAIT_DAYS
    cx = (LX0 + LX1) / 2
    for d in range(PORTRAIT_DAYS):
        y0 = top + rowh * d
        if d == 0:
            c.rect(LX0, y0 + 6, LX1, y0 + rowh - 6, fill=PALE, r=16)
        elif d:
            c.line([(LX0 + 20, y0), (LX1 - 20, y0)], fill=PALE, w=2)
        name = "Today" if d == 0 else datetime.fromisoformat(daily["time"][d]).strftime("%A")
        c.text((cx, y0 + 44), name, "day", anchor="mm")
        draw_icon(c, daily["weather_code"][d], cx - 80, y0 + 140, 110)
        hi = f"{round(daily['temperature_2m_max'][d])}°"
        lo = f"{round(daily['temperature_2m_min'][d])}°"
        c.text((cx + 70, y0 + 118), hi, "hi", anchor="mm")
        c.text((cx + 70, y0 + 176), lo, "lo", fill=MID, anchor="mm")
        rain_label(c, cx, y0 + rowh - 38, round(daily["precipitation_probability_max"][d] or 0),
                     "drain", "drainb", 26)
    c.line([(424, 100), (424, H - 30)], fill=LIGHT, w=2)

    # right column: current conditions
    RX0, RX1 = 452, W - M
    rc = (RX0 + RX1) / 2
    draw_icon(c, cur["weather_code"], RX0 + 80, 214, 150, day=bool(cur.get("is_day", 1)))
    temp = f"{round(cur['temperature_2m'])}°"
    tx0 = RX0 + 175
    size = 230
    while size > 120:   # shrink so even "100°" or "-10°" fits
        F["ptemp"] = font("InterDisplay-SemiBold.otf", size)
        if c.width(temp, "ptemp") <= RX1 - tx0:
            break
        size -= 10
    c.text(((tx0 + RX1) / 2, 214), temp, "ptemp", anchor="mm")
    c.text((RX0, 372), describe(cur["weather_code"]), "cond", anchor="lm")
    hi0, lo0 = round(daily["temperature_2m_max"][0]), round(daily["temperature_2m_min"][0])
    rows = [
        ("Feels like", f"{round(cur['apparent_temperature'])}°"),
        ("High / Low", f"{hi0}° / {lo0}°"),
        ("Rain today", f"{round(daily['precipitation_probability_max'][0] or 0)}%"),
        ("Wind", f"{round(cur['wind_speed_10m'])} mph"
                 + (f", gusts {round(cur['wind_gusts_10m'])}"
                    if cur.get('wind_gusts_10m', 0) - cur['wind_speed_10m'] >= 8 else "")),
        ("Humidity", f"{round(cur['relative_humidity_2m'])}%"),
    ]
    for i, (k, v) in enumerate(rows):
        y = 440 + i * 50
        c.text((RX0, y), k, "body", fill=MID, anchor="lm")
        c.text((RX0 + 220, y), v, "bodyb", anchor="lm")
    c.line([(RX0, 700), (RX1, 700)], fill=LIGHT, w=2)

    # right column: every 2 hours as rows
    times = [datetime.fromisoformat(t).replace(tzinfo=tz) for t in hourly["time"]]
    start = next(i for i, t in enumerate(times) if t > now + timedelta(hours=HOURLY_STEP - 1))
    idx = [start + HOURLY_STEP * n for n in range(HOURLY_COLS)]
    htop, hbot = 712, H - 24
    hh = (hbot - htop) / len(idx)
    for n, i in enumerate(idx):
        y = htop + hh * (n + 0.5)
        if n:
            c.line([(RX0, htop + hh * n), (RX1, htop + hh * n)], fill=PALE, w=2)
        c.text((RX0 + 10, y), hour_label(times[i]), "hour", fill=DARK, anchor="lm")
        c.text((rc + 30, y), f"{round(hourly['temperature_2m'][i])}°", "htemp", anchor="mm")
        rain_label(c, RX1 - 70, y, round(hourly["precipitation_probability"][i] or 0),
                     "hrain", "hrainb", 26)

    img = c.img.resize((W, H), Image.LANCZOS)
    return img.point(lambda v: min(255, round(v / 17) * 17))


def light_level(data):
    """Front-light percent for right now, based on today's sunrise/sunset."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    today = now.strftime("%Y-%m-%d")
    d = data["daily"]
    i = d["time"].index(today) if today in d["time"] else 0
    sunrise = datetime.fromisoformat(d["sunrise"][i]).replace(tzinfo=tz)
    sunset = datetime.fromisoformat(d["sunset"][i]).replace(tzinfo=tz)
    pad = timedelta(minutes=30)
    dark = now < sunrise + pad or now > sunset - pad
    return LIGHT_NIGHT if dark else LIGHT_DAY


def main():
    data = sample() if "--sample" in sys.argv else fetch()
    img = render_portrait(data) if LAYOUT == "portrait" else render(data)
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "light.txt"), "w") as f:
        f.write(f"{light_level(data)}\n")
    img.save(os.path.join(out, "preview.png"))
    turn = PORTRAIT_ROTATE if LAYOUT == "portrait" else ROTATE
    img.rotate(turn, expand=True).save(os.path.join(out, "weather.png"), optimize=True)
    print("wrote", os.path.join(out, "weather.png"))


if __name__ == "__main__":
    main()
