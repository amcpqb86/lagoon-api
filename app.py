from io import BytesIO
import hashlib
import os
import matplotlib
import matplotlib.pyplot as plt
from flask import Flask, request, send_file, abort
from starplot import MapPlot, Mercator, settings, _
from starplot.styles import PlotStyle, extensions

matplotlib.use("Agg")

API_TOKEN = os.environ.get("API_TOKEN", "")
CACHE_DIR = "/app/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

SUPPORTED_LANGUAGES = ["en-us", "es", "fa", "fr", "lt", "zh-cn", "zh-tw"]

def resolve_lang(lang: str) -> str:
    if lang in SUPPORTED_LANGUAGES:
        return lang
    if lang == "en":
        return "en-us"
    if lang == "zh":
        return "zh-cn"
    return "en-us"

def cache_key(ra, dec, fov, theme, lang) -> str:
    raw = f"{ra:.2f}_{dec:.2f}_{fov:.1f}_{theme}_{lang}"
    return hashlib.md5(raw.encode()).hexdigest()

def get_cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f"{key}.png")

def check_token():
    token = request.args.get("token") or request.headers.get("X-API-Token")
    if not token or token != API_TOKEN:
        abort(401)

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

@app.route("/star-chart")
def star_chart():
    check_token()
    plt.close("all")

    ra    = float(request.args.get("ra",  83.82))
    dec   = float(request.args.get("dec", -5.39))
    fov   = float(request.args.get("fov", 30.0))
    theme = request.args.get("theme", "dark")
    lang  = request.args.get("lang", "en")
    lang  = resolve_lang(lang)
    settings.language = lang

    key        = cache_key(ra, dec, fov, theme, lang)
    cache_path = get_cache_path(key)

    if os.path.exists(cache_path):
        print(f"✅ Cache hit: {key}")
        return send_file(cache_path, mimetype="image/png")

    ra_min  = ra - fov / 2
    ra_max  = ra + fov / 2
    dec_min = max(-90, dec - fov / 2)
    dec_max = min(90,  dec + fov / 2)

    style = PlotStyle().extend(
        extensions.BLUE_DARK if theme == "dark" else extensions.BLUE_LIGHT,
        extensions.MAP,
    )

    p = MapPlot(
        projection=Mercator(),
        ra_min=ra_min,
        ra_max=ra_max,
        dec_min=dec_min,
        dec_max=dec_max,
        style=style,
        resolution=1200,
        autoscale=True,
    )

    p.gridlines()
    p.constellations()
    p.constellation_borders()
    p.stars(
        where=[_.magnitude < 8],
        where_labels=[_.magnitude < 4],
        bayer_labels=True,
    )
    p.nebula(
        where=[(_.magnitude < 9) | (_.magnitude.isnull())],
        where_labels=[(_.magnitude < 9) | (_.magnitude.isnull())]
    )
    p.galaxies(
        where=[(_.magnitude < 9) | (_.magnitude.isnull())],
        where_labels=[(_.magnitude < 9) | (_.magnitude.isnull())]
    )

    try:
        p.open_clusters(
            where=[(_.magnitude < 9) | (_.magnitude.isnull())],
            where_labels=[False]
        )
    except Exception as e:
        print(f"⚠️ open_clusters ignoré: {e}")

    try:
        p.milky_way()
    except Exception as e:
        print(f"⚠️ milky_way ignoré: {e}")
    p.constellation_labels()

    buf = BytesIO()
    p.export(buf, format="png", padding=0.1)
    image_bytes = buf.getvalue()

    with open(cache_path, "wb") as f:
        f.write(image_bytes)
    print(f"💾 Cache saved: {key}")

    return send_file(BytesIO(image_bytes), mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)