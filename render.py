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
HOURS_SHOWN = 12          # hourly strip length
DAYS_SHOWN = 8            # today + next 7
# Which way to turn the landscape picture for the Kindle:
#   90  = Kindle's bottom edge (logo side) on the RIGHT when mounted
#   -90 = Kindle's bottom edge on the LEFT
ROTATE = 90

W, H = 1448, 1072          # landscape canvas
S = 2                      # supersampling for smooth edges
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

BLACK, DARK, MID, LIGHT, PALE, WHITE = 0, 70, 130, 190, 228, 255


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size * S)


F = {
    "huge": lambda: font("InterDisplay-SemiBold.otf", 250),
    "cond": lambda: font("InterDisplay-SemiBold.otf", 50),
    "head": lambda: font("Inter-SemiBold.otf", 32),
    "body": lambda: font("Inter-Medium.otf", 32),
    "bodyb": lambda: font("Inter-Bold.otf", 32),
    "small": lambda: font("Inter-Medium.otf", 26),
    "smallb": lambda: font("Inter-Bold.otf", 26),
    "day": lambda: font("Inter-Bold.otf", 34),
    "hi": lambda: font("Inter-Bold.otf", 38),
    "lo": lambda: font("Inter-Medium.otf", 34),
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
    return f"{h}{'AM' if dt.hour < 12 else 'PM'}"


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


# ---------------------------------------------------------------- layout
def render(data):
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
    c.text((tx, 140), describe(cur["weather_code"]), "cond", anchor="lm")
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
        y = 200 + i * 44
        c.text((tx, y), k, "body", fill=MID, anchor="lm")
        c.text((tx + 190, y), v, "bodyb", anchor="lm")
    c.line([(M, 410), (W - M, 410)], fill=LIGHT, w=2)

    # --- hourly strip
    times = [datetime.fromisoformat(t).replace(tzinfo=tz) for t in hourly["time"]]
    start = next(i for i, t in enumerate(times) if t > now)
    idx = list(range(start, start + HOURS_SHOWN))
    temps = [hourly["temperature_2m"][i] for i in idx]
    pops = [hourly["precipitation_probability"][i] or 0 for i in idx]

    c.text((M, 440), f"Next {HOURS_SHOWN} hours", "head", anchor="lm")
    lx = W - M
    c.rect(lx - 330, 432, lx - 316, 450, fill=DARK, r=2)
    c.text((lx - 306, 441), "chance of rain", "small", fill=MID, anchor="lm")
    c.line([(lx - 520, 441), (lx - 480, 441)], fill=BLACK, w=4)
    c.text((lx - 470, 441), "temp", "small", fill=MID, anchor="lm")

    colw = (W - 2 * M) / HOURS_SHOWN
    xs = [M + colw * (i + 0.5) for i in range(HOURS_SHOWN)]
    t_top, t_bot = 510, 610
    tmin, tmax = min(temps), max(temps)
    span = max(tmax - tmin, 6)
    mid = (tmax + tmin) / 2
    ys = [t_bot - ((t - (mid - span / 2)) / span) * (t_bot - t_top) for t in temps]
    area = [(xs[0], 650)] + list(zip(xs, ys)) + [(xs[-1], 650)]
    c.poly(area, fill=PALE)
    c.line(list(zip(xs, ys)), fill=BLACK, w=4)
    for x, y, t in zip(xs, ys, temps):
        c.circle(x, y, 6, fill=BLACK)
        c.text((x, y - 16), f"{round(t)}°", "smallb", anchor="ms")

    b_top, b_bot = 670, 760
    c.line([(M, b_bot), (W - M, b_bot)], fill=LIGHT, w=2)
    for x, p in zip(xs, pops):
        h = (b_bot - b_top) * p / 100
        if h >= 2:
            c.rect(x - 22, b_bot - h, x + 22, b_bot, fill=DARK if p >= 50 else MID, r=4)
        c.text((x, b_bot + 28), f"{round(p)}%", "smallb" if p >= 50 else "small",
               fill=BLACK if p >= 30 else MID, anchor="mm")
    for x, i in zip(xs, idx):
        c.text((x, b_bot + 66), hour_label(times[i]), "small", fill=DARK, anchor="mm")
    c.line([(M, 860), (W - M, 860)], fill=LIGHT, w=2)

    # --- daily row
    dcol = (W - 2 * M) / DAYS_SHOWN
    for d in range(DAYS_SHOWN):
        x = M + dcol * (d + 0.5)
        date = datetime.fromisoformat(daily["time"][d])
        name = "Today" if d == 0 else date.strftime("%a")
        if d == 0:
            c.rect(x - dcol / 2 + 6, 872, x + dcol / 2 - 6, 1060, fill=PALE, r=14)
        c.text((x, 900), name, "day", anchor="mm")
        draw_icon(c, daily["weather_code"][d], x, 952, 74)
        hi = round(daily["temperature_2m_max"][d])
        lo = round(daily["temperature_2m_min"][d])
        his, los = f"{hi}°", f"{lo}°"
        gap = 12
        total = c.width(his, "hi") + gap + c.width(los, "lo")
        x0 = x - total / 2
        c.text((x0, 1010), his, "hi", anchor="lm")
        c.text((x0 + c.width(his, "hi") + gap, 1010), los, "lo", fill=MID, anchor="lm")
        p = round(daily["precipitation_probability_max"][d] or 0)
        ps = f"{p}%"
        pw = c.width(ps, "small") + 22
        draw_drop(c, x - pw / 2 + 7, 1046, 20, fill=DARK if p >= 30 else LIGHT)
        c.text((x - pw / 2 + 22, 1046), ps, "smallb" if p >= 50 else "small",
               fill=BLACK if p >= 30 else MID, anchor="lm")

    img = c.img.resize((W, H), Image.LANCZOS)
    # e-ink shows 16 gray levels; snap to them so nothing dithers oddly
    img = img.point(lambda v: min(255, round(v / 17) * 17))
    return img


def main():
    data = sample() if "--sample" in sys.argv else fetch()
    img = render(data)
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    img.save(os.path.join(out, "preview.png"))
    img.rotate(ROTATE, expand=True).save(os.path.join(out, "weather.png"), optimize=True)
    print("wrote", os.path.join(out, "weather.png"))


if __name__ == "__main__":
    main()
