"""Llibreta D+ · dashboard de trail running sobre intervals.icu (Streamlit)."""
from __future__ import annotations

import datetime as dt
import math
import os
import random

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# En redes corporativas con inspección TLS, usa los certificados de confianza del sistema
# (almacén de Windows / llavero de macOS) en lugar del paquete de certifi.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

# ─────────────────────────── Configuración ───────────────────────────
st.set_page_config(page_title="Llibreta D+", page_icon="⛰️", layout="wide")

# Tema: se elige con el interruptor de la barra lateral (clave "light_theme")
LIGHT = st.session_state.get("theme_icon") == "☀️"
PALETTES = {
    "dark": dict(GOLD="#f5c400", GLACIER="#4cc0e6", RED="#e8402f", GREEN="#3cb46a", VIOLET="#a58bd6", ORANGE="#f08a3c",
                 TEAL="#3fb8a6", INK="#f3f2ec", MUTED="#8e989f", PREV="#5d676e", LINE="#262d33", GRID="#1d2328",
                 SURFACE="#13171b", BG="#0a0c0e", SURFACE2="#1a1f24", ZEBRA="#1b2126", HOVER="#252d34", ZERO="#3a444c"),
    "light": dict(GOLD="#c99700", GLACIER="#1d86ad", RED="#cf3427", GREEN="#2b8f52", VIOLET="#7a5fc0", ORANGE="#d26a17",
                  TEAL="#1f8f81", INK="#1c2420", MUTED="#5f6b66", PREV="#9aa59f", LINE="#d3dad6", GRID="#e7ece9",
                  SURFACE="#ffffff", BG="#f3f5f2", SURFACE2="#eef1ee", ZEBRA="#f5f7f5", HOVER="#e6ece8", ZERO="#bcc6c1"),
}
_P = PALETTES["light" if LIGHT else "dark"]
GOLD, GLACIER, RED, GREEN = _P["GOLD"], _P["GLACIER"], _P["RED"], _P["GREEN"]
VIOLET, ORANGE, TEAL, INK = _P["VIOLET"], _P["ORANGE"], _P["TEAL"], _P["INK"]
MUTED, PREV, LINE, GRID, SURFACE, BG = _P["MUTED"], _P["PREV"], _P["LINE"], _P["GRID"], _P["SURFACE"], _P["BG"]
SURFACE2, ZEBRA, HOVER, ZERO = _P["SURFACE2"], _P["ZEBRA"], _P["HOVER"], _P["ZERO"]


def rgb(hex_color: str) -> str:
    return ",".join(str(int(hex_color[i:i + 2], 16)) for i in (1, 3, 5))


def rgba(hex_color: str, a: float) -> str:
    return f"rgba({rgb(hex_color)},{a})"


def on(hex_color: str) -> str:
    """Color de texto legible sobre un fondo dado."""
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return "#0a0c0e" if (0.2126 * r + 0.7152 * g + 0.0722 * b) > 0.45 else "#ffffff"




OUT, CINTA, GIM = {"Run", "TrailRun"}, {"VirtualRun"}, {"Workout", "WeightTraining", "Elliptical"}
MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
API = "https://intervals.icu/api/v1"

st.markdown(
    f"""
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
.stApp, .stMarkdown p, .stMarkdown li, .stCaption, label {{ font-family: "IBM Plex Sans", system-ui, sans-serif; }}
h1, h2, h3 {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif !important; font-weight: 600 !important; letter-spacing: .01em; }}
.block-container {{ padding-top: 2.2rem; max-width: 1240px; }}
.eyebrow {{ font: 500 11px "IBM Plex Sans", sans-serif; letter-spacing: .08em; text-transform: uppercase; color: {GOLD}; }}
.note {{ font-size: 12.5px; color: {MUTED}; }}
.cards {{ display: grid; grid-template-columns: repeat(var(--n), minmax(0,1fr)); gap: 1px; background: {LINE};
          border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; margin: 4px 0 14px; }}
@media (max-width: 900px) {{ .cards {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
.card {{ background: {SURFACE}; padding: 12px 14px; display: grid; gap: 2px; min-width: 0; }}
.card .k {{ display: flex; align-items: center; gap: 6px; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: {MUTED}; }}
.card .k::before {{ content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--c); }}
.card .v {{ font: 600 30px/1.05 "Barlow Condensed", sans-serif; color: {INK}; font-variant-numeric: tabular-nums; }}
.card .v small {{ font: 400 13px "IBM Plex Sans", sans-serif; color: {MUTED}; margin-left: 3px; }}
.card .d {{ font-size: 12px; color: {MUTED}; }}
.up {{ color: {GREEN}; }} .down {{ color: {RED}; }}
.pill {{ justify-self: start; font-size: 11px; padding: 1px 8px; border-radius: 999px; color: var(--c); border: 1px solid var(--c); }}
.big {{ font: 600 clamp(44px, 8vw, 72px)/.95 "Barlow Condensed", sans-serif; color: {INK}; }}
.big small {{ font: 400 15px "IBM Plex Sans", sans-serif; color: {MUTED}; margin-left: .3em; }}
.reading {{ background: {SURFACE}; border-left: 3px solid var(--c); padding: 10px 14px; font-size: 13.5px; margin: 6px 0 12px; }}
.day {{ display: grid; grid-template-columns: 62px 1fr; gap: 10px; padding: 7px 0; border-bottom: 1px solid {GRID}; }}
.day .dn {{ font: 12px "IBM Plex Mono", monospace; color: {MUTED}; }}
.tag {{ display: inline-block; font-size: 11px; font-weight: 500; padding: 1px 7px; border-radius: 2px; background: var(--c); color: var(--o, #0a0c0e); margin-right: 6px; }}
.m {{ color: {MUTED}; font-size: 12.5px; }}
.tblw {{ overflow: auto; border: 1px solid {LINE}; border-radius: 8px; margin: 6px 0 14px; }}
table.tbl {{ border-collapse: separate; border-spacing: 0; width: 100%; font: 13.5px "IBM Plex Sans", system-ui, sans-serif;
             font-variant-numeric: tabular-nums; color: {INK}; }}
table.tbl th {{ position: sticky; top: 0; z-index: 2; background: {SURFACE2}; color: {MUTED}; font-weight: 500; font-size: 11.5px;
               text-transform: uppercase; letter-spacing: .05em; padding: 9px 12px; text-align: right; white-space: nowrap;
               border-bottom: 1px solid {LINE}; }}
table.tbl tr.grp th {{ top: 0; text-align: center; color: {INK}; font: 600 15px "Barlow Condensed", sans-serif; letter-spacing: .04em;
                      text-transform: none; border-bottom: 1px solid {LINE}; }}
table.tbl tr.grp + tr th {{ top: 36px; }}
table.tbl tr.grp th.tot {{ color: {GOLD}; }}
table.tbl td {{ padding: 9px 12px; text-align: right; white-space: nowrap; border-bottom: 1px solid {GRID}; }}
table.tbl th.l, table.tbl td.l {{ text-align: left; }}
table.tbl th, table.tbl td {{ border-top: 0 !important; border-left: 0 !important; border-right: 0 !important; }}
table.tbl tbody tr:nth-child(odd) td {{ background-color: {SURFACE}; }}
table.tbl tbody tr:nth-child(even) td {{ background-color: {ZEBRA}; }}
table.tbl tbody tr:hover td {{ background-color: {HOVER} !important; }}
table.tbl th:first-child, table.tbl td:first-child {{ position: sticky; left: 0; z-index: 1; background: {SURFACE}; text-align: left;
                                                     font-family: "IBM Plex Mono", monospace; border-right: 1px solid {LINE} !important; }}
table.tbl th:first-child {{ z-index: 3; background: {SURFACE2}; }}
table.tbl tbody tr:nth-child(even) td:first-child {{ background: {ZEBRA}; }}
table.tbl .g {{ border-left: 2px solid {LINE} !important; }}
table.tbl td.z {{ color: {ZERO}; }}
table.tbl tr.hl td {{ color: {GOLD}; font-weight: 600; }}
table.tbl tr.cur td {{ color: {MUTED}; font-style: italic; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background: {BG}; color: {INK}; }}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background: {SURFACE2}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp li {{ color: {INK}; }}
.day {{ color: {INK}; }}
table.tbl tr.tot td {{ border-top: 2px solid {GOLD}; color: {GOLD}; font-weight: 600; background: {SURFACE}; border-bottom: 0; }}
[data-testid="stForm"] [data-testid="stVerticalBlock"]:has(> [class*="st-key-crow"]),
[data-testid="stForm"] [data-testid="stVerticalBlock"]:has(> div > [class*="st-key-crow"]) {{ gap: 0 !important; }}
[class*="st-key-crow"] [data-testid="stMarkdownContainer"] {{ display: flex; align-items: center; min-height: 2.5rem; }}
[class*="st-key-crow"] {{ padding: 4px 10px; border-bottom: 1px solid {GRID}; }}
[class*="st-key-crow"] [data-testid="stHorizontalBlock"] {{ align-items: center; }}
[class*="st-key-crow"] .stNumberInput div[data-baseweb="input"], [class*="st-key-crow"] .stNumberInput > div > div {{ border-color: {LINE} !important; }}
[class*="st-key-crowE"] {{ background: {ZEBRA}; }}
[class*="st-key-crowO"] {{ background: {SURFACE}; }}
[class*="st-key-crow"]:hover {{ background: {HOVER}; }}
[class*="st-key-crow"] p {{ margin: 0; }}
.chd {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: .05em; color: {MUTED}; }}
.ctd {{ font-size: 13.5px; color: {INK}; font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ctd.r, .chd.r {{ text-align: right; }}
[class*="st-key-crow"] [data-testid="stMarkdownContainer"] > div {{ width: 100%; }}
[data-testid="stDateInputField"] {{ position: relative; cursor: pointer; }}
[data-testid="stDateInputField"]::after {{ content: "📅"; position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
  font-size: 15px; pointer-events: none; opacity: .85; }}
.chip {{ display: inline-block; font-size: 11px; font-weight: 500; padding: 1px 7px; border-radius: 2px; background: var(--c); color: var(--o, #0a0c0e); }}
</style>
""",
    unsafe_allow_html=True,
)


# Tema claro: el tema nativo de Streamlit es oscuro (config.toml); aquí se adaptan sus widgets
if LIGHT:
    st.markdown(f"""<style>
.stSelectbox [role="group"], .stMultiSelect [role="group"], [data-baseweb="select"] > div,
.stNumberInput input, .stTextInput input, .stNumberInput [data-baseweb="input"] {{
  background: {SURFACE} !important; color: {INK} !important; border-color: {LINE} !important; }}
.stSelectbox input, .stMultiSelect input {{ color: {INK} !important; }}
[role="listbox"], [role="listbox"] [role="option"], [data-baseweb="popover"] ul {{ background: {SURFACE} !important; color: {INK} !important; }}
[role="listbox"] [role="option"]:hover, [role="listbox"] [data-focused="true"] {{ background: {HOVER} !important; }}
.stButtonGroup button {{ background: {SURFACE} !important; border-color: {LINE} !important; }}
.stButtonGroup button p, .stButtonGroup button span {{ color: {INK} !important; }}
.stButtonGroup button[data-selected="true"], .stButtonGroup button[aria-checked="true"] {{ background: {rgba(GOLD, .16)} !important; border-color: {GOLD} !important; }}
.stExpander details {{ background: {SURFACE} !important; border-color: {LINE} !important; }}
.stExpander summary, .stExpander summary p {{ color: {INK} !important; }}
.stCheckbox label:has(input:not(:checked)) > div:nth-of-type(1) {{ background: {LINE} !important; }}
.stCheckbox label:has(input:not(:checked)) > div:nth-of-type(1) > div {{ background: {SURFACE} !important; box-shadow: 0 0 0 1px {MUTED}; }}
.stTabs button p {{ color: {INK}; }}
.stSlider [data-testid="stSliderTickBarMin"], .stSlider [data-testid="stSliderTickBarMax"] {{ color: {MUTED}; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{ color: {INK}; }}
[data-testid="stSidebar"] .stButton button p {{ color: {on(GOLD)}; }}
[data-testid="stHeader"] {{ color: {INK}; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {MUTED} !important; }}
</style>""", unsafe_allow_html=True)


# ─────────────────────────── Utilidades ───────────────────────────
def fnum(v, d=0):
    """Número en formato español."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    s = f"{v:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def delta_html(cur, ref, label, invert=False):
    if ref is None or (isinstance(ref, float) and math.isnan(ref)) or ref <= 0:
        return f'<span class="up">▲ nuevo</span> vs {label}' if cur and cur > 0 else f"— vs {label}"
    x = (cur - ref) / ref
    if abs(x) < 0.005:
        return f"= vs {label}"
    good = x < 0 if invert else x > 0
    return f'<span class="{"up" if good else "down"}">{"▲" if x > 0 else "▼"} {fnum(abs(x) * 100)} %</span> vs {label}'


def cards(items):
    """items: (label, color, value, unit, [lineas html])"""
    html = [f'<div class="cards" style="--n:{len(items)}">']
    for label, color, value, unit, lines in items:
        u = f"<small>{unit}</small>" if unit else ""
        html.append(f'<div class="card" style="--c:{color}"><span class="k">{label}</span><span class="v">{value}{u}</span>')
        html += [f'<span class="d">{ln}</span>' if not ln.startswith("<span class=\"pill") else ln for ln in lines]
        html.append("</div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def html_table(df: pd.DataFrame, fmt: dict | None = None, groups: list | None = None, group_start: set | None = None,
               heat: dict | None = None, total_last: bool = False, left: set | None = None, max_height: int | None = None,
               row_classes: list | None = None):
    """Tabla HTML legible: filas alternas, cabecera fija, primera columna fija, grupos de columnas y celdas con intensidad.

    fmt: {col: callable(v)->str}; groups: [(titulo, n_columnas, clase)] para una fila de cabecera agrupada;
    group_start: columnas que abren grupo (borde izquierdo); heat: {col: (max, color_rgb)}; left: columnas alineadas a la izquierda.
    """
    fmt, group_start, heat, left = fmt or {}, group_start or set(), heat or {}, left or set()
    cols = list(df.columns)
    h = [f'<div class="tblw" style="{f"max-height:{max_height}px" if max_height else ""}"><table class="tbl"><thead>']
    if groups:
        h.append("<tr class='grp'>" + "".join(
            f'<th colspan="{n}" class="{c}">{t}</th>' for t, n, c in groups) + "</tr>")
    h.append("<tr>" + "".join(
        f'<th class="{"g " if c in group_start else ""}{"l" if c in left else ""}">{c.split("|")[-1]}</th>' for c in cols) + "</tr></thead><tbody>")
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        cls = "tot" if total_last and i == n - 1 else (row_classes[i] if row_classes else "")
        tds = []
        for c in cols:
            v = row[c]
            txt = fmt[c](v) if c in fmt else ("" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v))
            style = ""
            if c in heat and cls != "tot" and isinstance(v, (int, float, np.number)) and pd.notna(v) and v > 0:
                mx, rgb = heat[c]
                style = f' style="background:rgba({rgb},{min(.55, .08 + .47 * v / mx):.2f})"' if mx else ""
            zero = " z" if isinstance(v, (int, float, np.number)) and pd.notna(v) and v == 0 else ""
            tds.append(f'<td class="{"g " if c in group_start else ""}{"l" if c in left else ""}{zero}"{style}>{txt}</td>')
        h.append(f'<tr class="{cls}">' + "".join(tds) + "</tr>")
    h.append("</tbody></table></div>")
    st.markdown("".join(h), unsafe_allow_html=True)


def plot_layout(fig, h=300, legend=True):
    fig.update_layout(
        height=h, margin=dict(l=8, r=8, t=10, b=8), paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="IBM Plex Mono, ui-monospace, Menlo, monospace", size=11, color=MUTED),
        showlegend=legend, legend=dict(orientation="h", y=1.08, x=0, font=dict(color=MUTED)),
        hoverlabel=dict(font_family="IBM Plex Sans, system-ui, sans-serif"), bargap=0.25,
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=MUTED, zeroline=False, automargin=True, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zeroline=False, automargin=True, tickfont=dict(color=MUTED))
    return fig


# ─────────────────────────── Datos ───────────────────────────
def get_secret(name, default=""):
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


# Campo personalizado de actividad en intervals.icu donde se guarda la pendiente media (%) de la cinta
INCLINE_FIELD = str(get_secret("INCLINE_FIELD", "Pendiente")).strip() or "Pendiente"


def map_activity(a: dict) -> dict:
    dist = (a.get("distance") or a.get("icu_distance") or 0) / 1000
    mt = a.get("moving_time") or a.get("elapsed_time") or 0
    sp = a.get("average_speed") or 0
    return dict(
        id=a.get("id"), start=a.get("start_date_local"), sport=a.get("type"), name=a.get("name") or "",
        km=dist, dp=a.get("total_elevation_gain") or 0, dm=a.get("total_elevation_loss") or 0,
        secs=mt, elapsed=a.get("elapsed_time") or mt, load=a.get("icu_training_load") or 0,
        hr_avg=a.get("average_heartrate"), hr_max=a.get("max_heartrate"),
        kcal=a.get("calories"), carbs=a.get("carbs_ingested"), feel=a.get("feel"),
        pace=(1000 / sp) if sp > 0 else ((mt / dist) if dist > 0 and mt else None),
        incline=a.get(INCLINE_FIELD),
    )


@st.cache_data(ttl=600, show_spinner=False)
def fetch_year(athlete: str, key: str, year: int) -> list[dict]:
    r = requests.get(
        f"{API}/athlete/{athlete}/activities",
        params={"oldest": f"{year}-01-01", "newest": f"{year}-12-31"},
        auth=("API_KEY", key), headers={"Accept": "application/json", "User-Agent": "LlibretaD+ (Streamlit)"},
        timeout=30,
    )
    if r.status_code in (401, 403):
        raise PermissionError("intervals.icu rechazó la clave (revisa ATHLETE_ID e INTERVALS_API_KEY).")
    if r.status_code == 404:
        raise LookupError("No existe ese Athlete ID en intervals.icu.")
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("Respuesta inesperada de intervals.icu.")
    return [map_activity(a) for a in data if a and a.get("start_date_local") and a.get("type")]


def demo_year(year: int) -> list[dict]:
    """Datos de ejemplo para probar sin conexión (DEMO=1)."""
    rnd = random.Random(year)
    today = dt.date.today()
    start = dt.date(year, 1, 2) if year == today.year else dt.date(year, 6, 10)
    end = min(dt.date(year, 12, 31), today)
    out, d = [], start
    sports = ["TrailRun", "Workout", "VirtualRun", "Run", "Hike", "TrailRun"]
    while d <= end:
        s = rnd.choice(sports)
        km = 0 if s == "Workout" else rnd.uniform(4, 17)
        dp = {"TrailRun": km * rnd.uniform(35, 60), "Run": km * 8, "Hike": km * 30}.get(s, 0)
        secs = 1800 if s == "Workout" else km * (560 if s != "Hike" else 900)
        out.append(dict(id=f"demo{d}", start=f"{d}T08:00:00", sport=s, name=f"Ejemplo {s}", km=km, dp=dp, dm=dp,
                        secs=secs, elapsed=secs * 1.1, load=int(secs / 60 * (1.1 if s != "Workout" else .2)), hr_avg=140, hr_max=165,
                        kcal=int(secs / 4), carbs=None, feel=rnd.choice([2, 3]), pace=secs / km if km else None,
                        incline=rnd.choice([None, None, 3, 5, 8]) if s == "VirtualRun" else None))
        d += dt.timedelta(days=rnd.choice([1, 1, 2, 3]))
    return out


def to_frame(rows: list[dict], hike: bool, cinta_dp: bool = True, overrides: dict | None = None) -> pd.DataFrame:
    cols = ["id", "start", "sport", "name", "km", "dp", "dm", "secs", "elapsed", "load", "hr_avg", "hr_max", "kcal", "carbs", "feel", "pace", "incline"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df.assign(ts=pd.Series(dtype="datetime64[ns]"), date=pd.Series(dtype=object))
    df["ts"] = pd.to_datetime(df["start"])
    df = df.drop_duplicates(subset=["start", "sport", "secs"]).sort_values("ts").reset_index(drop=True)
    df["date"] = df["ts"].dt.date
    for c in ["km", "dp", "dm", "secs", "elapsed", "load"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["elapsed"] = df[["elapsed", "secs"]].max(axis=1)
    for c in ["hr_avg", "hr_max", "kcal", "carbs", "feel", "pace"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["incline"] = pd.to_numeric(df["incline"], errors="coerce")
    if overrides:  # pendientes guardadas en esta sesión (antes de que la caché se refresque)
        ov = df["id"].map(overrides)
        df["incline"] = ov.where(ov.notna(), df["incline"])
    is_cinta = df["sport"].isin(CINTA)
    # D+ de cinta = distancia × pendiente media
    df.loc[is_cinta, "dp"] = (df.loc[is_cinta, "km"] * 1000 * df.loc[is_cinta, "incline"].fillna(0) / 100).round(0)
    cinta_up = is_cinta & cinta_dp & (df["dp"] > 0)
    out_mask = df["sport"].isin(OUT) | (hike & (df["sport"] == "Hike"))
    df["out_km"] = np.where(out_mask, df["km"], 0.0)
    df["out_dp"] = np.where(out_mask | cinta_up, df["dp"], 0.0)
    df["ukm"] = np.where(out_mask | cinta_up, df["km"], 0.0)   # km que cuentan para el Ultra Ind
    df["cinta_km"] = np.where(df["sport"].isin(CINTA), df["km"], 0.0)
    df["gim_min"] = np.where(df["sport"].isin(GIM), df["secs"] / 60, 0.0)
    df["hours"] = df["secs"] / 3600
    return df


def totals(d: pd.DataFrame) -> dict:
    dp, km, ukm = d["out_dp"].sum(), d["out_km"].sum(), d["ukm"].sum() if "ukm" in d else d["out_km"].sum()
    return dict(dp=dp, km=km, cinta=d["cinta_km"].sum(), gim=d["gim_min"].sum(), n=len(d),
                load=d["load"].sum(), h=d["hours"].sum(), ultra=1.7 * dp / ukm if ukm > 0 else 0.0,
                kmE=km + d["cinta_km"].sum() + dp / 100)


# ─────────────────────────── Barra lateral ───────────────────────────
today = dt.date.today()
now_y = today.year

with st.sidebar:
    st.markdown("### ⛰️ Llibreta D+")
    year = st.selectbox("Temporada", list(range(now_y, 2022, -1)), index=0)
    hike = st.toggle("Sumar caminatas a D+ y Km", value=False)
    cinta_dp = st.toggle("Sumar D+ de cinta (según pendiente)", value=True,
                         help="El D+ de cinta se calcula como km × pendiente media. Se edita en la pestaña Cinta.")
    if st.button("Actualizar datos", type="primary", width="stretch"):
        st.cache_data.clear()
    demo = str(get_secret("DEMO", "")).strip() == "1"
    athlete = str(get_secret("ATHLETE_ID", "")).strip()
    key = str(get_secret("INTERVALS_API_KEY", "")).strip()
    if not demo and (not athlete or not key):
        st.info("Configura ATHLETE_ID e INTERVALS_API_KEY en los secretos de la app, o introdúcelos aquí para esta sesión.")
        athlete = st.text_input("Athlete ID", value=athlete, placeholder="i123456").strip()
        key = st.text_input("API key", value=key, type="password").strip()
    with st.expander("Objetivos de la semana"):
        st.caption("Déjalos vacíos para usar tu media de las 8 últimas semanas.")
        TARGETS = {
            "dp": st.number_input("D+ (m)", min_value=0, step=100, value=None, placeholder="media 8 sem"),
            "km": st.number_input("Km", min_value=0.0, step=5.0, value=None, placeholder="media 8 sem"),
            "kmE": st.number_input("Km-esfuerzo", min_value=0.0, step=5.0, value=None, placeholder="media 8 sem"),
            "h": st.number_input("Horas", min_value=0.0, step=0.5, value=None, placeholder="media 8 sem"),
            "load": st.number_input("Carga", min_value=0, step=25, value=None, placeholder="media 8 sem"),
            "n": st.number_input("Sesiones", min_value=0, step=1, value=None, placeholder="media 8 sem"),
        }
    st.caption("D+ y Km = Run y TrailRun (más Hike si lo activas; D+ de cinta si lo activas) · Km Cinta = VirtualRun · min Gim = Workout, WeightTraining y Elliptical.")
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.segmented_control("Tema", ["🌙", "☀️"], default="🌙", key="theme_icon", label_visibility="collapsed",
                         help="Tema oscuro / claro")

# Contraseña opcional para la app
pwd = str(get_secret("APP_PASSWORD", ""))
if pwd and not st.session_state.get("auth_ok"):
    st.title("Llibreta D+")
    p = st.text_input("Contraseña", type="password")
    if p == pwd:
        st.session_state.auth_ok = True
        st.rerun()
    elif p:
        st.error("Contraseña incorrecta.")
    st.stop()

if not demo and (not athlete or not key):
    st.title("Llibreta D+")
    st.warning("Falta la conexión con intervals.icu: añade tu Athlete ID y tu API key (intervals.icu → Settings → Developer Settings).")
    st.stop()

if athlete and athlete.isdigit():
    athlete = "i" + athlete

years_needed = sorted({year, year - 1, now_y, now_y - 1})
raw: dict[int, list[dict]] = {}
errors = {}
with st.spinner("Leyendo actividades de intervals.icu…"):
    for y in years_needed:
        try:
            raw[y] = demo_year(y) if demo else fetch_year(athlete, key, y)
        except Exception as e:  # noqa: BLE001
            errors[y] = e
            raw[y] = []

if year in errors:
    st.error(f"No se pudieron cargar las actividades de {year}: {errors[year]}")
    st.stop()

all_df = to_frame([r for y in years_needed for r in raw[y]], hike, cinta_dp, st.session_state.get("incline_overrides"))
df_y = all_df[all_df["ts"].dt.year == year] if not all_df.empty else all_df
df_p = all_df[all_df["ts"].dt.year == year - 1] if not all_df.empty else all_df
T, P = totals(df_y), totals(df_p)

# ─────────────────────────── Indicadores del año ───────────────────────────
if demo:
    st.warning("Modo de ejemplo: los datos son ficticios (DEMO=1).")

def prev_line(v, d, u=""):
    return f"{year - 1}: {fnum(v, d)} {u}".strip() if len(df_p) else "&nbsp;"

cards([
    ("D+", GOLD, fnum(T["dp"]), "m", [prev_line(P["dp"], 0, "m")]),
    ("Km", INK, fnum(T["km"], 1), "km", [prev_line(P["km"], 1, "km")]),
    ("Km Cinta", GLACIER, fnum(T["cinta"], 1), "km", [prev_line(P["cinta"], 1, "km")]),
    ("min Gim", GREEN, fnum(T["gim"]), "min", [f"{fnum(T['gim'] / 60, 1)} h · {T['n']} sesiones en total"]),
    ("Ultra Ind", RED, fnum(T["ultra"], 1), "", [prev_line(P["ultra"], 1)]),
])

# ─────────────────────────── Última semana ───────────────────────────
WKM = [("dp", "D+", GOLD, "m", 0), ("km", "Km", INK, "km", 1), ("cinta", "Km Cinta", GLACIER, "km", 1),
       ("gim", "min Gim", GREEN, "min", 0), ("ultra", "Ultra Ind", RED, "", 1), ("load", "Carga", VIOLET, "", 0),
       ("kmE", "Km-esfuerzo", ORANGE, "km", 1), ("h", "Horas", TEAL, "h", 1)]

cur_mon = today - dt.timedelta(days=today.weekday())
last_mon = cur_mon - dt.timedelta(days=7)
week_starts = [cur_mon - dt.timedelta(weeks=12 - i) for i in range(13)]  # 0..11 completas, 12 = en curso


def week_tot(ws: dt.date) -> dict:
    d = all_df[(all_df["date"] >= ws) & (all_df["date"] < ws + dt.timedelta(days=7))] if len(all_df) else all_df
    return totals(d)


W = [week_tot(ws) for ws in week_starts]
LW, PW = W[11], W[10]
AVG = {k: float(np.mean([w[k] for w in W[3:11]])) for k in ["dp", "km", "cinta", "gim", "load", "kmE", "h", "n"]}
AVG["ultra"] = 1.7 * AVG["dp"] / AVG["km"] if AVG["km"] > 0 else 0

# ─────────────────────────── Forma / fatiga (cálculo común) ───────────────────────────
fit = pd.DataFrame()
if len(all_df):
    days = pd.date_range(all_df["ts"].min().normalize(), pd.Timestamp(today), freq="D")
    load = all_df.groupby(all_df["ts"].dt.normalize())["load"].sum().reindex(days, fill_value=0)
    kc, ka = 1 - math.exp(-1 / 42), 1 - math.exp(-1 / 7)
    ctl, atl, C, A = 0.0, 0.0, [], []
    for v in load.values:
        ctl += (v - ctl) * kc
        atl += (v - atl) * ka
        C.append(ctl)
        A.append(atl)
    fit = pd.DataFrame({"load": load.values, "ctl": C, "atl": A}, index=days)
    fit["tsb"] = fit["ctl"] - fit["atl"]


def zone_tsb(v):
    return ("Fresco", GLACIER) if v > 5 else ("Neutral", MUTED) if v >= -10 else ("Carga productiva", GREEN) if v >= -30 else ("Sobrecarga", RED)


def zone_acwr(v):
    if v is None:
        return ("Sin datos", MUTED)
    return ("Carga baja", GLACIER) if v < .8 else ("Zona óptima", GREEN) if v <= 1.3 else ("Subida rápida", ORANGE) if v <= 1.5 else ("Riesgo", RED)


def zone_mono(v):
    if v is None:
        return ("Sin datos", MUTED)
    return ("Variada", GREEN) if v < 1.5 else ("Moderada", ORANGE) if v <= 2 else ("Repetitiva", RED)


tab_temp, tab_cw, tab_lw, tab_fat, tab_sets, tab_long, tab_cinta = st.tabs(
    ["Temporada", "Semana en curso", "Última semana", "Esfuerzo y fatiga", "Hoja por Sets", "Entrenamientos largos", "Cinta"])

with tab_temp:
    # Hero
    doy = (today - dt.date(year, 1, 1)).days if year == now_y else 366
    prev_same = df_p[df_p["ts"].dt.dayofyear <= doy + 1]["out_dp"].sum() if len(df_p) else 0
    cmp = ""
    if prev_same > 0:
        r = (T["dp"] - prev_same) / prev_same
        cmp = f' <b class="{"up" if r >= 0 else "down"}">{"+" if r >= 0 else "−"}{fnum(abs(r) * 100)} %</b> respecto a {year - 1} a misma fecha.'
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    with c1:
        st.markdown(f'<div class="eyebrow">Temporada {year}</div><div class="big">{fnum(T["dp"])}<small>m D+</small></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<b>{fnum(T["km"], 1)} km</b> en montaña y asfalto, <b>{fnum(T["dp"] / T["km"] if T["km"] else 0)} m</b> de D+ por km.{cmp}'
            f'<div class="note">{len(df_y)} actividades · intervals.icu {dt.datetime.now().strftime("%H:%M")}</div>',
            unsafe_allow_html=True,
        )

    # Perfil de temporada
    st.subheader("Perfil de temporada")
    st.markdown('<span class="note">km acumulados × D+ acumulado · cada punto = inicio de mes</span>', unsafe_allow_html=True)


    def cumulative(d: pd.DataFrame, y: int, until: dt.date | None = None):
        days = pd.date_range(f"{y}-01-01", until or dt.date(y, 12, 31), freq="D")
        g = d.groupby(d["ts"].dt.normalize())[["out_km", "out_dp"]].sum().reindex(days, fill_value=0).cumsum()
        return g


    fig = go.Figure()
    if len(df_p):
        gp = cumulative(df_p, year - 1)
        fig.add_scatter(x=gp["out_km"], y=gp["out_dp"], mode="lines", name=str(year - 1),
                        line=dict(color=PREV, width=1.6, dash="dash"), hovertemplate="%{x:.0f} km · %{y:.0f} m<extra></extra>")
    gy = cumulative(df_y, year, today if year == now_y else None)
    fig.add_scatter(x=gy["out_km"], y=gy["out_dp"], mode="lines", name=str(year), fill="tozeroy",
                    fillcolor=rgba(GOLD, .14), line=dict(color=GOLD, width=2.6),
                    hovertemplate="%{x:.0f} km · %{y:.0f} m<extra></extra>")
    months = gy[gy.index.day == 1].iloc[1:]
    fig.add_scatter(x=months["out_km"], y=months["out_dp"], mode="markers+text", text=[MES[m - 1] for m in months.index.month],
                    textposition="top center", textfont=dict(color=INK, family="IBM Plex Sans, system-ui, sans-serif"),
                    marker=dict(size=8, color=BG, line=dict(color=GOLD, width=2)), showlegend=False, hoverinfo="skip")
    if len(gy):
        fig.add_scatter(x=[gy["out_km"].iloc[-1]], y=[gy["out_dp"].iloc[-1]], mode="markers+text",
                        text=[f"{fnum(gy['out_dp'].iloc[-1])} m"], textposition="middle right",
                        textfont=dict(color=GOLD, family="IBM Plex Sans, system-ui, sans-serif"), marker=dict(size=11, color=GOLD), showlegend=False, hoverinfo="skip")
    fig.update_xaxes(title=None, ticksuffix=" km")
    st.plotly_chart(plot_layout(fig, 320), width="stretch", theme=None)

    # Mensual
    def monthly(d: pd.DataFrame) -> pd.DataFrame:
        m = d.groupby(d["ts"].dt.month)[["out_dp", "out_km", "ukm", "cinta_km", "gim_min"]].sum().reindex(range(1, 13), fill_value=0)
        m["ultra"] = np.where(m["ukm"] > 0, 1.7 * m["out_dp"] / m["ukm"].replace(0, np.nan), 0)
        prev = m["out_dp"].shift(1)
        m["incr"] = np.where((m["out_dp"] > 0) & (m.index > 1), (m["out_dp"] - prev) / m["out_dp"].replace(0, np.nan), 0)
        return m.fillna(0)


    My, Mp = monthly(df_y), monthly(df_p)
    c1, c2 = st.columns([3, 2])
    for col, key_, title, color, dec in [(c1, "out_dp", "D+ por mes", GOLD, 0), (c2, "ultra", "Ultra Ind por mes", RED, 1)]:
        with col:
            st.subheader(title)
            f2 = go.Figure()
            xm = MES if key_ == "out_dp" else [m[0] for m in MES]
            f2.add_bar(x=list(range(12)), y=My[key_], name=str(year), marker_color=color, customdata=MES, hovertemplate=f"%{{customdata}}: %{{y:.{dec}f}}<extra>{year}</extra>")
            if len(df_p):
                f2.add_scatter(x=list(range(12)), y=Mp[key_].where(Mp[key_] > 0), mode="markers", name=str(year - 1),
                               marker=dict(symbol="line-ew", size=26, line=dict(width=3, color=PREV)),
                               customdata=MES, hovertemplate=f"%{{customdata}}: %{{y:.{dec}f}}<extra>{year - 1}</extra>")
            f2.update_xaxes(tickvals=list(range(12)), ticktext=xm, tickangle=0)
            st.plotly_chart(plot_layout(f2, 250), width="stretch", theme=None)


with tab_cw:
    # ─────────────────────────── Semana en curso ───────────────────────────
    TRK = [("dp", "D+", GOLD, "m", 0), ("km", "Km", INK, "km", 1), ("kmE", "Km-esfuerzo", ORANGE, "km", 1),
           ("h", "Horas", TEAL, "h", 1), ("load", "Carga", VIOLET, "", 0), ("n", "Sesiones", GLACIER, "", 0)]
    dow = today.weekday()                      # 0 = lunes
    remaining = 6 - dow                        # días que quedan después de hoy
    CW = W[12]


    def span_tot(a: dt.date, b: dt.date) -> dict:
        d = all_df[(all_df["date"] >= a) & (all_df["date"] <= b)] if len(all_df) else all_df
        return totals(d)


    SAME_LW = span_tot(last_mon, last_mon + dt.timedelta(days=dow))
    SAME_AVG = {k: float(np.mean([span_tot(ws, ws + dt.timedelta(days=dow))[k] for ws in week_starts[3:11]])) for k, *_ in TRK}
    GOAL = {k: (TARGETS.get(k) or AVG[k]) for k, *_ in TRK}
    PROJ = {k: CW[k] + AVG[k] / 7 * remaining for k, *_ in TRK}

    st.markdown(f'<div class="eyebrow" style="margin-top:18px">{cur_mon.day} {MES[cur_mon.month-1].lower()} – '
                f'{(cur_mon + dt.timedelta(days=6)).day} {MES[(cur_mon + dt.timedelta(days=6)).month-1].lower()} · '
                f'día {dow + 1} de 7</div>', unsafe_allow_html=True)
    st.subheader("Semana en curso")
    st.markdown('<span class="note">De lunes a hoy, comparada con la semana pasada y con tu media de 8 semanas <b>a esta misma altura</b>. '
                'El objetivo es tu media semanal salvo que fijes otro en la barra lateral; la proyección suma a lo hecho tu media diaria en los días que quedan.</span>',
                unsafe_allow_html=True)


    def track_card(k, lab, col, unit, dec):
        cur, goal = CW[k], GOAL[k]
        pct = cur / goal * 100 if goal > 0 else 0
        bar = (f'<div style="height:6px;background:{GRID};border-radius:3px;overflow:hidden;margin:4px 0 2px">'
               f'<i style="display:block;height:100%;width:{min(pct, 100):.0f}%;background:{col}"></i></div>')
        goal_txt = f'objetivo {fnum(goal, dec)} · <b style="color:{INK}">{fnum(pct)} %</b>' if goal > 0 else "sin objetivo"
        return (lab, col, fnum(cur, dec), unit, [
            bar, goal_txt,
            delta_html(cur, SAME_LW[k], "sem. pasada a esta altura"),
            delta_html(cur, SAME_AVG[k], "media a esta altura"),
            f"proyección domingo: <b style='color:{INK}'>{fnum(PROJ[k], dec)}</b>",
        ])


    cards([track_card(*m) for m in TRK[:3]])
    cards([track_card(*m) for m in TRK[3:]])

    # Fatiga en la semana en curso
    FZ = None
    if len(fit):
        fnow = fit.iloc[-1]
        pre = fit.loc[:pd.Timestamp(cur_mon - dt.timedelta(days=1))]
        fstart = pre.iloc[-1] if len(pre) else None
        acwr_now = fnow["atl"] / fnow["ctl"] if fnow["ctl"] > 0 else None
        wk_load = fit.loc[pd.Timestamp(cur_mon):, "load"]
        mono_now = float(wk_load.mean() / wk_load.std(ddof=0)) if len(wk_load) >= 3 and wk_load.std(ddof=0) > 0 else None
        tz_, tc_ = zone_tsb(fnow["tsb"])
        az_, ac_ = zone_acwr(acwr_now)
        mz_, mc_ = zone_mono(mono_now)
        FZ = (tz_, tc_, fnow, acwr_now, az_)

        def since_mon(c, p, invert=False):
            if p is None:
                return "&nbsp;"
            x = c - p
            if abs(x) < .5:
                return "= desde el lunes"
            good = x < 0 if invert else x > 0
            return f'<span class="{"up" if good else "down"}">{"▲" if x > 0 else "▼"} {fnum(abs(x))}</span> desde el lunes'

        pill_ = lambda t, c: f'<span class="pill" style="--c:{c}">{t}</span>'  # noqa: E731
        st.markdown('<div class="eyebrow" style="margin-top:8px">Fatiga esta semana</div>', unsafe_allow_html=True)
        cards([
            ("Forma (CTL)", GLACIER, fnum(fnow["ctl"]), "", [since_mon(fnow["ctl"], fstart["ctl"] if fstart is not None else None)]),
            ("Fatiga (ATL)", RED, fnum(fnow["atl"]), "", [since_mon(fnow["atl"], fstart["atl"] if fstart is not None else None, True)]),
            ("Balance (TSB)", tc_, ("+" if fnow["tsb"] > 0 else "") + fnum(fnow["tsb"]), "",
             [since_mon(fnow["tsb"], fstart["tsb"] if fstart is not None else None), pill_(tz_, tc_)]),
            ("Ratio agudo:crónico", ac_, fnum(acwr_now, 2) if acwr_now else "—", "", ["Fatiga ÷ Forma", pill_(az_, ac_)]),
            ("Monotonía", mc_, fnum(mono_now, 2) if mono_now else "—", "",
             ["Lunes a hoy" if mono_now else "Hacen falta 3 días", pill_(mz_, mc_)]),
        ])

        # Evolución de los últimos 14 días con la semana en curso sombreada
        f14 = fit.iloc[-14:]
        fz = go.Figure()
        fz.add_vrect(x0=pd.Timestamp(cur_mon) - pd.Timedelta(hours=12), x1=f14.index[-1] + pd.Timedelta(hours=12),
                     fillcolor=GOLD, opacity=.06, line_width=0, annotation_text="semana en curso",
                     annotation_position="top left", annotation_font=dict(color=GOLD, size=11))
        fz.add_bar(x=f14.index, y=f14["tsb"], name="Balance", marker_color=[zone_tsb(v)[1] for v in f14["tsb"]], opacity=.55,
                   hovertemplate="%{x|%d/%m}: balance %{y:.0f}<extra></extra>")
        fz.add_scatter(x=f14.index, y=f14["ctl"], name="Forma", mode="lines+markers", line=dict(color=GLACIER, width=2.4),
                       hovertemplate="%{x|%d/%m}: %{y:.0f}<extra>Forma</extra>")
        fz.add_scatter(x=f14.index, y=f14["atl"], name="Fatiga", mode="lines+markers", line=dict(color=RED, width=1.8),
                       hovertemplate="%{x|%d/%m}: %{y:.0f}<extra>Fatiga</extra>")
        fz.add_hline(y=0, line_color=MUTED, line_width=1)
        fz.update_xaxes(tickvals=f14.index, ticktext=[f"{DIAS[d.weekday()]} {d.day}" for d in f14.index])
        plot_layout(fz, 260).update_layout(legend=dict(orientation="h", y=-0.2, x=0), margin=dict(t=24))
        st.plotly_chart(fz, width="stretch", theme=None)

    # Rampa de carga y lectura
    base4 = float(np.mean([w["load"] for w in W[7:11]]))
    ramp = PROJ["load"] / base4 if base4 > 0 else None
    rz, rc = (("Sin datos", MUTED) if ramp is None else ("Carga baja", GLACIER) if ramp < .8 else ("Zona óptima", GREEN) if ramp <= 1.3
              else ("Subida rápida", ORANGE) if ramp <= 1.5 else ("Riesgo", RED))
    rest_days = sum(1 for i in range(dow + 1) if not (all_df["date"] == cur_mon + dt.timedelta(days=i)).any()) if len(all_df) else dow + 1
    msg = [f"Llevas <b>{dow + 1} de 7 días</b> y <b>{rest_days}</b> de descanso."]
    for k, lab, _, unit, dec in [("dp", "D+", 0, "m", 0), ("kmE", "Km-esfuerzo", 0, "km", 1)]:
        falta = GOAL[k] - CW[k]
        if GOAL[k] > 0 and falta > 0:
            per = f" (≈ {fnum(falta / remaining, dec)} {unit}/día en los {remaining} días que quedan)" if remaining > 0 else ""
            msg.append(f"Para el objetivo de {lab} te faltan <b>{fnum(falta, dec)} {unit}</b>{per}.")
        elif GOAL[k] > 0:
            msg.append(f"Objetivo de {lab} <b>cumplido</b> ({fnum(CW[k] / GOAL[k] * 100)} %).")
    if ramp is not None:
        msg.append(f"Carga proyectada <b>{fnum(PROJ['load'])}</b> = {fnum(ramp, 2)}× tu media de las 4 últimas semanas ({rz.lower()}).")
    if FZ is not None:
        tz_, tc_, fnow, acwr_now, az_ = FZ
        tip = (" Conviene uno o varios días suaves antes de volver a cargar." if fnow["tsb"] < -30 else
               " Estás cargando; lo que hace progresar es recuperar después." if fnow["tsb"] < -10 else
               " Carga equilibrada con tu forma." if fnow["tsb"] <= 5 else
               " Llegas fresco: buen momento para una sesión exigente o larga.")
        msg.append(f"Hoy tu balance es <b>{'+' if fnow['tsb'] > 0 else ''}{fnum(fnow['tsb'])}</b> ({tz_.lower()}).{tip}")
        order = [GREEN, GLACIER, MUTED, ORANGE, RED]
        rc = max([rc, tc_], key=lambda c: order.index(c) if c in order else 0)
    st.markdown(f'<div class="reading" style="--c:{rc}">{" ".join(msg)}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Acumulado día a día")
        tl = {k: lab for k, lab, *_ in TRK}
        tm = st.segmented_control("Métrica semana en curso", list(tl), format_func=lambda k: tl[k], default="dp",
                                  label_visibility="collapsed", key="cw_metric") or "dp"
        _, tlab, tcol, tunit, tdec = next(m for m in TRK if m[0] == tm)

        def cum_week(ws: dt.date, upto: int = 6):
            return list(np.cumsum([span_tot(ws + dt.timedelta(days=i), ws + dt.timedelta(days=i))[tm] for i in range(upto + 1)]))

        cur_c = cum_week(cur_mon, dow)
        lw_c = cum_week(last_mon)
        avg_c = list(np.mean([cum_week(ws) for ws in week_starts[3:11]], axis=0))
        f6 = go.Figure()
        f6.add_scatter(x=DIAS, y=avg_c, name="Media 8 sem", mode="lines", line=dict(color=MUTED, width=1.6, dash="dot"),
                       hovertemplate=f"%{{x}}: %{{y:.{tdec}f}} {tunit}<extra>Media 8 sem</extra>")
        f6.add_scatter(x=DIAS, y=lw_c, name="Semana pasada", mode="lines", line=dict(color=PREV, width=1.6, dash="dash"),
                       hovertemplate=f"%{{x}}: %{{y:.{tdec}f}} {tunit}<extra>Semana pasada</extra>")
        f6.add_scatter(x=DIAS[: dow + 1], y=cur_c, name="Esta semana", mode="lines+markers", line=dict(color=tcol, width=3),
                       marker=dict(size=7), hovertemplate=f"%{{x}}: %{{y:.{tdec}f}} {tunit}<extra>Esta semana</extra>")
        if remaining > 0:
            f6.add_scatter(x=DIAS[dow:], y=[cur_c[-1] + AVG[tm] / 7 * i for i in range(remaining + 1)], name="Proyección",
                           mode="lines", line=dict(color=tcol, width=1.6, dash="dot"), opacity=.7,
                           hovertemplate=f"%{{x}}: %{{y:.{tdec}f}} {tunit}<extra>Proyección</extra>")
        if GOAL[tm] > 0:
            f6.add_hline(y=GOAL[tm], line=dict(color=INK, width=1, dash="dash"),
                         annotation_text=f"objetivo {fnum(GOAL[tm], tdec)}", annotation_position="top left",
                         annotation_font=dict(color=INK, size=11))
        plot_layout(f6, 320).update_layout(legend=dict(orientation="h", y=-0.18, x=0), margin=dict(t=24))
        st.plotly_chart(f6, width="stretch", theme=None)
    with c2:
        st.subheader("Esta semana")
        TAGS_CW = {"TrailRun": ("Trail", GOLD), "Run": ("Asfalto", INK), "VirtualRun": ("Cinta", GLACIER), "Hike": ("Caminata", PREV),
                   "Workout": ("Gim", GREEN), "WeightTraining": ("Gim", GREEN), "Elliptical": ("Elíptica", GREEN)}
        html = []
        for i in range(7):
            day = cur_mon + dt.timedelta(days=i)
            acts = all_df[all_df["date"] == day] if len(all_df) else all_df
            body = []
            for _, a in acts.iterrows():
                tl_, tc_ = TAGS_CW.get(a["sport"], (a["sport"], PREV))
                parts = [f"{fnum(a['km'], 1)} km"] if a["km"] else []
                if a["dp"] >= 1:
                    parts.append(f"{fnum(a['dp'])} m D+")
                parts.append(f"{int(a['secs'] // 3600)}:{int(a['secs'] % 3600 // 60):02d}")
                if a["load"]:
                    parts.append(f"carga {int(a['load'])}")
                body.append(f'<div><span class="tag" style="--c:{tc_};--o:{on(tc_)}">{tl_}</span><span class="m">{" · ".join(parts)}</span></div>')
            if body:
                content = "".join(body)
            elif i < dow:
                content = "<i class=m>Descanso</i>"
            elif i == dow:
                content = "<i class=m>Hoy, sin actividad todavía</i>"
            else:
                content = "<span class=m>—</span>"
            style = f' style="background:{rgba(GOLD, .08)}"' if i == dow else ""
            label = f'{DIAS[i]} {day.day}' + (" ·hoy" if i == dow else "")
            html.append(f'<div class="day"{style}><span class="dn">{label}</span><div>{content}</div></div>')
        st.markdown("".join(html), unsafe_allow_html=True)


with tab_lw:
    st.markdown(f'<div class="eyebrow" style="margin-top:18px">{last_mon.day} {MES[last_mon.month-1].lower()} – '
                f'{(last_mon + dt.timedelta(days=6)).day} {MES[(last_mon + dt.timedelta(days=6)).month-1].lower()} '
                f'{(last_mon + dt.timedelta(days=6)).year}</div>', unsafe_allow_html=True)
    st.subheader("Última semana")
    st.markdown('<span class="note">Semana completa de lunes a domingo, comparada con la semana anterior y con la media de las 8 semanas previas.</span>', unsafe_allow_html=True)
    cards([(lab, col, fnum(LW[k], d), u, [delta_html(LW[k], PW[k], "sem. anterior"), delta_html(LW[k], AVG[k], "media 8 sem")])
           for k, lab, col, u, d in WKM[:4]])
    cards([(lab, col, fnum(LW[k], d), u, [delta_html(LW[k], PW[k], "sem. anterior"), delta_html(LW[k], AVG[k], "media 8 sem")])
           for k, lab, col, u, d in WKM[4:]])

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Últimas 12 semanas")
        labels = {k: lab for k, lab, *_ in WKM}
        metric = st.segmented_control("Métrica", list(labels), format_func=lambda k: labels[k], default="dp",
                                      label_visibility="collapsed") or "dp"
        _, lab, colr, unit, dec = next(m for m in WKM if m[0] == metric)
        xs = [f"{ws.day}/{ws.month}" for ws in week_starts]
        vals = [w[metric] for w in W]
        opac = [0.38] * 11 + [1.0, 0.12]
        f3 = go.Figure()
        f3.add_bar(x=xs, y=vals, marker=dict(color=colr, opacity=opac, line=dict(color=colr, width=[0] * 12 + [1.5])),
                   text=[fnum(v, dec) if i == 11 else "" for i, v in enumerate(vals)], textposition="outside",
                   textfont=dict(color=INK), hovertemplate=f"Semana %{{x}}: %{{y:.{dec}f}} {unit}<extra></extra>", showlegend=False)
        if AVG[metric] > 0:
            f3.add_scatter(x=xs[3:12], y=[AVG[metric]] * 9, mode="lines", line=dict(color=INK, dash="dash", width=1.4),
                           name=f"media 8 sem: {fnum(AVG[metric], dec)}", hoverinfo="skip")
        f3.update_xaxes(ticktext=xs[:12] + [f"{xs[12]}<br>en curso"], tickvals=xs, tickangle=0, tickfont=dict(size=10))
        st.plotly_chart(plot_layout(f3, 290), width="stretch", theme=None)
    with c2:
        st.subheader("Día a día")
        TAGS = {"TrailRun": ("Trail", GOLD), "Run": ("Asfalto", INK), "VirtualRun": ("Cinta", GLACIER), "Hike": ("Caminata", PREV),
                "Workout": ("Gim", GREEN), "WeightTraining": ("Gim", GREEN), "Elliptical": ("Elíptica", GREEN)}
        html = []
        for i in range(7):
            day = last_mon + dt.timedelta(days=i)
            acts = all_df[all_df["date"] == day] if len(all_df) else all_df
            body = []
            for _, a in acts.iterrows():
                tl, tc = TAGS.get(a["sport"], (a["sport"], PREV))
                parts = []
                if a["km"]:
                    parts.append(f"{fnum(a['km'], 1)} km")
                if a["dp"] >= 1:
                    parts.append(f"{fnum(a['dp'])} m D+")
                parts.append(f"{int(a['secs'] // 3600)}:{int(a['secs'] % 3600 // 60):02d}")
                if a["load"]:
                    parts.append(f"carga {int(a['load'])}")
                body.append(f'<div><span class="tag" style="--c:{tc};--o:{on(tc)}">{tl}</span><span class="m">{" · ".join(parts)}</span></div>')
            html.append(f'<div class="day"><span class="dn">{DIAS[i]} {day.day}</span><div>{"".join(body) or "<i class=m>Descanso</i>"}</div></div>')
        st.markdown("".join(html), unsafe_allow_html=True)

    wk_rows = []
    for i in [12] + list(range(11, 2, -1)):
        ws = week_starts[i]
        name = f"{ws.day}/{ws.month}–{(ws + dt.timedelta(days=6)).day}/{(ws + dt.timedelta(days=6)).month}"
        wk_rows.append({"Semana": name + (" (en curso)" if i == 12 else " ★" if i == 11 else ""), **{lab: W[i][k] for k, lab, *_ in WKM}, "Sesiones": W[i]["n"]})
    wk_rows.append({"Semana": "Media 8 sem previas", **{lab: AVG[k] for k, lab, *_ in WKM}, "Sesiones": AVG["n"]})
    WT = pd.DataFrame(wk_rows)
    fz_ = lambda d: (lambda v: "0" if v == 0 else fnum(v, d))  # noqa: E731
    html_table(WT, fmt={**{lab: fz_(d) for k, lab, c, u, d in WKM}, "Sesiones": fz_(1)},
               heat={"D+": (float(max(1, WT["D+"].iloc[1:-1].max())), rgb(GOLD))},
               row_classes=["cur"] + ["hl"] + [""] * (len(WT) - 3) + [""], total_last=True, group_start={"Sesiones"})


with tab_fat:
    # ─────────────────────────── Esfuerzo y fatiga ───────────────────────────
    st.markdown(f'<div class="eyebrow" style="margin-top:18px">A {today.day} {MES[today.month-1].lower()} {today.year}</div>', unsafe_allow_html=True)
    st.subheader("Esfuerzo y fatiga")
    st.markdown('<span class="note">Calculado con la carga de entrenamiento de cada actividad de intervals.icu (todas las disciplinas).</span>', unsafe_allow_html=True)



    if len(fit):
        cur, wk = fit.iloc[-1], fit.iloc[-8] if len(fit) > 7 else None
        acwr = cur["atl"] / cur["ctl"] if cur["ctl"] > 0 else None
        wl = fit.loc[pd.Timestamp(last_mon):pd.Timestamp(last_mon + dt.timedelta(days=6)), "load"].reindex(
            pd.date_range(last_mon, periods=7), fill_value=0)
        mono = float(wl.mean() / wl.std(ddof=0)) if wl.std(ddof=0) > 0 else None

        def dd(c, p, invert=False):
            if p is None:
                return "&nbsp;"
            x = c - p
            if abs(x) < .5:
                return "= vs hace 7 días"
            good = x < 0 if invert else x > 0
            return f'<span class="{"up" if good else "down"}">{"▲" if x > 0 else "▼"} {fnum(abs(x))}</span> vs hace 7 días'

        tz, tc = zone_tsb(cur["tsb"])
        az, ac = zone_acwr(acwr)
        mz, mc = zone_mono(mono)
        pill = lambda t, c: f'<span class="pill" style="--c:{c}">{t}</span>'  # noqa: E731
        cards([
            ("Forma (CTL)", GLACIER, fnum(cur["ctl"]), "", [dd(cur["ctl"], wk["ctl"] if wk is not None else None)]),
            ("Fatiga (ATL)", RED, fnum(cur["atl"]), "", [dd(cur["atl"], wk["atl"] if wk is not None else None, True)]),
            ("Balance (TSB)", tc, ("+" if cur["tsb"] > 0 else "") + fnum(cur["tsb"]), "", [dd(cur["tsb"], wk["tsb"] if wk is not None else None), pill(tz, tc)]),
            ("Ratio agudo:crónico", ac, fnum(acwr, 2) if acwr else "—", "", ["Fatiga ÷ Forma", pill(az, ac)]),
            ("Monotonía sem.", mc, fnum(mono, 2) if mono else "—", "", ["Última semana completa", pill(mz, mc)]),
            ("Km-esfuerzo sem.", ORANGE, fnum(LW["kmE"], 1), "km", [delta_html(LW["kmE"], AVG["kmE"], "media 8 sem")]),
        ])
        t = f"Balance <b>{'+' if cur['tsb'] > 0 else ''}{fnum(cur['tsb'])}</b> ({tz.lower()})"
        t += (": acumulas mucha más carga de la que tu forma absorbe; conviene uno o varios días suaves." if cur["tsb"] < -30 else
              ": estás cargando por encima de tu forma, que es lo que hace progresar si luego descansas." if cur["tsb"] < -10 else
              ": carga equilibrada con tu forma actual." if cur["tsb"] <= 5 else
              ": vienes de descansar; buen momento para una sesión exigente o una carrera.")
        if acwr:
            t += f" Ratio agudo:crónico <b>{fnum(acwr, 2)}</b> ({az.lower()})."
        if AVG["kmE"] > 0:
            t += f" La última semana hiciste <b>{fnum(LW['kmE'], 1)} km-esfuerzo</b> frente a una media de {fnum(AVG['kmE'], 1)}."
        st.markdown(f'<div class="reading" style="--c:{tc}">{t}</div>', unsafe_allow_html=True)

        RANGES = {"7": "Última semana", "30": "Último mes", "120": "120 días", "year": "Año vs año anterior"}
        rng = st.segmented_control("Periodo", list(RANGES), format_func=lambda k: RANGES[k], default="120",
                                   label_visibility="collapsed") or "120"
        st.subheader("Forma, fatiga y balance · " + (f"{now_y} vs {now_y - 1}" if rng == "year" else RANGES[rng].lower()))

        f4, f5 = go.Figure(), go.Figure()
        if rng == "year":
            cy = fit[fit.index.year == now_y]
            py = fit[fit.index.year == now_y - 1]
            xc = cy.index.dayofyear
            xp = py.index.dayofyear
            for frame, x, suffix, dash, op in [(py, xp, str(now_y - 1), "dash", .6), (cy, xc, str(now_y), "solid", 1)]:
                if len(frame):
                    f4.add_scatter(x=x, y=frame["ctl"], name=f"Forma {suffix}", line=dict(color=GLACIER, width=2.4 if op == 1 else 1.6, dash=dash), opacity=op,
                                   customdata=frame.index.strftime("%d/%m"), hovertemplate="%{customdata}: %{y:.0f}<extra>Forma " + suffix + "</extra>")
                    f4.add_scatter(x=x, y=frame["atl"], name=f"Fatiga {suffix}", line=dict(color=RED, width=1.8 if op == 1 else 1.2, dash=dash), opacity=op,
                                   customdata=frame.index.strftime("%d/%m"), hovertemplate="%{customdata}: %{y:.0f}<extra>Fatiga " + suffix + "</extra>")
                    f5.add_scatter(x=x, y=frame["tsb"], name=f"Balance {suffix}", line=dict(color=INK if op == 1 else MUTED, width=1.8 if op == 1 else 1.4, dash=dash),
                                   fill="tozeroy" if op == 1 else None, fillcolor=rgba(INK, .08),
                                   customdata=frame.index.strftime("%d/%m"), hovertemplate="%{customdata}: %{y:.0f}<extra>Balance " + suffix + "</extra>")
            mstarts = [dt.date(now_y, m, 1).timetuple().tm_yday for m in range(1, 13)]
            for fig_ in (f4, f5):
                fig_.update_xaxes(tickvals=mstarts, ticktext=MES, range=[1, 367])
        else:
            sub = fit.iloc[-int(rng):]
            f4.add_bar(x=sub.index, y=sub["load"], name="Carga diaria", marker_color=PREV, opacity=.55, yaxis="y2",
                       hovertemplate="%{x|%d/%m}: carga %{y:.0f}<extra></extra>")
            mode = "lines+markers" if int(rng) <= 31 else "lines"
            f4.add_scatter(x=sub.index, y=sub["ctl"], name="Forma", mode=mode, line=dict(color=GLACIER, width=2.4), hovertemplate="%{x|%d/%m}: %{y:.0f}<extra>Forma</extra>")
            f4.add_scatter(x=sub.index, y=sub["atl"], name="Fatiga", mode=mode, line=dict(color=RED, width=1.8), hovertemplate="%{x|%d/%m}: %{y:.0f}<extra>Fatiga</extra>")
            f4.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, showticklabels=False,
                                         range=[0, max(1, sub["load"].max()) / .55]))
            f5.add_scatter(x=sub.index, y=sub["tsb"], name="Balance", mode=mode, line=dict(color=INK, width=1.8), fill="tozeroy",
                           fillcolor=rgba(INK, .08), hovertemplate="%{x|%d/%m}: %{y:.0f}<extra>Balance</extra>")
            if int(rng) <= 7:
                for fig_ in (f4, f5):
                    fig_.update_xaxes(tickvals=sub.index, ticktext=[f"{DIAS[d.weekday()]} {d.day}" for d in sub.index])
        lo, hi = min(-40, float(fit["tsb"].min())), max(20, float(fit["tsb"].max()))
        for y0, y1, c, lab in [(5, hi, GLACIER, "Fresco"), (-10, 5, MUTED, "Neutral"), (-30, -10, GREEN, "Carga productiva"), (lo, -30, RED, "Sobrecarga")]:
            f5.add_hrect(y0=y0, y1=y1, fillcolor=c, opacity=.08, line_width=0, annotation_text=lab, annotation_position="top left",
                         annotation_font=dict(color=c, size=11))
        f5.add_hline(y=0, line_color=MUTED, line_width=1)
        f5.update_yaxes(range=[lo, hi])
        st.plotly_chart(plot_layout(f4, 280), width="stretch", theme=None)
        st.plotly_chart(plot_layout(f5, 170, legend=rng == "year"), width="stretch", theme=None)

        # Esfuerzo por periodo (media semanal)
        st.subheader("Esfuerzo por periodo · media semanal")

        def period(a: dt.date, b: dt.date, label: str):
            d = all_df[(all_df["date"] >= a) & (all_df["date"] <= b)]
            span = (b - a).days + 1
            wks = span / 7
            t_ = totals(d)
            return {"Periodo": label, "Horas": t_["h"] / wks, "Km": t_["km"] / wks, "D+ m": t_["dp"] / wks,
                    "Km-esf.": t_["kmE"] / wks, "Ultra Ind": t_["ultra"], "Carga": t_["load"] / wks,
                    "Carga/h": t_["load"] / t_["h"] if t_["h"] else 0, "Sesiones": t_["n"] / wks,
                    "Días descanso": (span - d["date"].nunique()) / wks}

        first = all_df["date"].min()
        ys, pys = dt.date(now_y, 1, 1), dt.date(now_y - 1, 1, 1)
        doy0 = (today - ys).days
        periods = [(last_mon, last_mon + dt.timedelta(days=6), "★ Última semana"),
                   (last_mon - dt.timedelta(days=21), last_mon + dt.timedelta(days=6), "Últimas 4 semanas"),
                   (last_mon - dt.timedelta(days=49), last_mon + dt.timedelta(days=6), "Últimas 8 semanas"),
                   (max(ys, first), today, f"Año {now_y}"),
                   (max(pys, first), pys + dt.timedelta(days=doy0), f"{now_y - 1} a misma fecha")]
        rows = [period(a, b, lab) for a, b, lab in periods if b >= a]
        PT = pd.DataFrame(rows)
        html_table(PT, fmt={c: (lambda d: (lambda v: "0" if v == 0 else fnum(v, d)))(0 if c in ("D+ m", "Carga", "Carga/h") else 1)
                            for c in PT.columns if c != "Periodo"},
                   row_classes=["hl"] + [""] * (len(PT) - 1), group_start={"Carga"})
        with st.expander("Cómo leer estos indicadores"):
            st.markdown(
                "- **Forma (CTL)**: carga media ponderada de 42 días. Sube despacio con la constancia.\n"
                "- **Fatiga (ATL)**: carga media ponderada de 7 días.\n"
                "- **Balance (TSB)** = Forma − Fatiga. Negativo cuando cargas, positivo cuando descansas.\n"
                "- **Ratio agudo:crónico** = Fatiga ÷ Forma. Entre 0,8 y 1,3 es la zona habitual de progresión.\n"
                "- **Monotonía**: media ÷ desviación de la carga diaria de la semana. Por encima de 2, semanas muy repetitivas.\n"
                "- **Km-esfuerzo** = km (incluida cinta) + D+ / 100.\n"
                "- Calculado aquí con la carga de cada actividad; puede diferir un poco de los valores de intervals.icu."
            )
    else:
        st.info("Sin actividades todavía.")


with tab_sets:
    # ─────────────────────────── Hoja por Sets ───────────────────────────
    st.subheader(f"D+ {year} por Sets")
    st.markdown('<span class="note">Set = bloque de 7 días del mes (1–7, 8–14, 15–21, 22–28, 29–31). Ultra Ind = 1,7 × D+/Km. '
                'Incr vs M‑1 = (D+ mes − D+ mes anterior) / D+ mes.</span>', unsafe_allow_html=True)
    MET = {"D+": ("out_dp", 0, rgb(GOLD)), "Km": ("out_km", 1, rgb(INK)), "Km Cinta": ("cinta_km", 1, rgb(GLACIER)),
           "min Gim": ("gim_min", 0, rgb(GREEN))}
    months_n = today.month if year == now_y else 12
    mlabels = [f"{MES[m - 1]} {str(year)[2:]}" for m in range(1, months_n + 1)]
    vista = st.segmented_control("Vista", ["Resumen mensual", "Detalle por Sets"], default="Resumen mensual",
                                 label_visibility="collapsed", key="sets_view") or "Resumen mensual"
    fN = lambda d: (lambda v: "" if pd.isna(v) else ("0" if v == 0 else fnum(v, d)))  # noqa: E731
    if vista == "Resumen mensual":
        R = pd.DataFrame({
            "Mes": mlabels,
            "D+ m": My["out_dp"].values[:months_n], "Km": My["out_km"].values[:months_n],
            "Km Cinta": My["cinta_km"].values[:months_n], "min Gim": My["gim_min"].values[:months_n],
            "Ultra Ind": My["ultra"].values[:months_n], "Incr vs M‑1": (My["incr"] * 100).values[:months_n],
        })
        tot = {"Mes": "Total", "D+ m": R["D+ m"].sum(), "Km": R["Km"].sum(), "Km Cinta": R["Km Cinta"].sum(),
               "min Gim": R["min Gim"].sum(), "Ultra Ind": T["ultra"], "Incr vs M‑1": np.nan}
        R = pd.concat([R, pd.DataFrame([tot])], ignore_index=True)

        def incr_fmt(v):
            if pd.isna(v) or v == 0:
                return "" if pd.isna(v) else "0"
            return f'<span class="{"up" if v > 0 else "down"}">{"▲" if v > 0 else "▼"} {fnum(abs(v))} %</span>'

        html_table(R, fmt={"D+ m": fN(0), "Km": fN(1), "Km Cinta": fN(1), "min Gim": fN(0), "Ultra Ind": fN(1), "Incr vs M‑1": incr_fmt},
                   heat={"D+ m": (float(max(1, R["D+ m"].iloc[:-1].max())), rgb(GOLD))}, group_start={"Ultra Ind"}, total_last=True)
    else:
        met = st.pills("Métrica", list(MET), default="D+", key="sets_metric") or "D+"
        src, dec, heat_rgb = MET[met]
        D = pd.DataFrame({"Mes": mlabels})
        s_ = df_y.assign(m=df_y["ts"].dt.month, s=((df_y["ts"].dt.day - 1) // 7).clip(upper=4) + 1) if len(df_y) else None
        for si, rng in enumerate(["1–7", "8–14", "15–21", "22–28", "29–31"], start=1):
            if s_ is not None:
                col = s_[s_["s"] == si].groupby("m")[src].sum().reindex(range(1, months_n + 1), fill_value=0).values
            else:
                col = np.zeros(months_n)
            D[f"Set {si}|Set {si} · {rng}"] = col
        D["Total mes"] = D[[c for c in D.columns if c.startswith("Set ")]].sum(axis=1)
        tot = {"Mes": "Total", **{c: D[c].sum() for c in D.columns if c != "Mes"}}
        D = pd.concat([D, pd.DataFrame([tot])], ignore_index=True)
        setcols = [c for c in D.columns if c.startswith("Set ")]
        mx = float(max(1, D[setcols].iloc[:-1].to_numpy().max()))
        html_table(D, fmt={c: fN(dec) for c in D.columns if c != "Mes"},
                   heat={c: (mx, heat_rgb) for c in setcols}, group_start={"Total mes"}, total_last=True)
        st.caption(f"{met} de cada bloque de 7 días; cuanto más intenso el color, más volumen en ese Set.")


with tab_long:
    # ─────────────────────────── Entrenamientos largos ───────────────────────────
    st.subheader("Entrenamientos largos")
    all_runs = all_df[all_df["sport"].isin(OUT)] if len(all_df) else all_df
    PER = ["30 días", "90 días", "6 meses", f"Temporada {year}", "Todo", "Personalizado"]
    pc1 = pc2 = st.container()
    with pc1:
        per = st.segmented_control("Periodo", PER, default=f"Temporada {year}", key="lg_per") or f"Temporada {year}"
    d_min = all_runs["date"].min() if len(all_runs) else today
    if per == "30 días":
        p_from, p_to = today - dt.timedelta(days=29), today
    elif per == "90 días":
        p_from, p_to = today - dt.timedelta(days=89), today
    elif per == "6 meses":
        p_from, p_to = today - dt.timedelta(days=182), today
    elif per == "Todo":
        p_from, p_to = d_min, today
    elif per == "Personalizado":
        dc1, dc2, _ = st.columns([1, 1, 2])
        with dc1:
            p_from = st.date_input("Desde", value=max(d_min, today - dt.timedelta(days=60)), min_value=d_min, max_value=today,
                                   format="DD/MM/YYYY", key="lg_from")
        with dc2:
            p_to = st.date_input("Hasta", value=today, min_value=d_min, max_value=today, format="DD/MM/YYYY", key="lg_to")
        if p_from > p_to:
            p_from, p_to = p_to, p_from
        st.caption("Pulsa en una fecha para abrir el calendario.")
    else:
        p_from, p_to = dt.date(year, 1, 1), min(dt.date(year, 12, 31), today)
    per_txt = f"{p_from.strftime('%d/%m/%y')} – {p_to.strftime('%d/%m/%y')}"
    if per != "Personalizado":
        with pc2:
            st.markdown(f'<div class="note" style="margin-top:-6px">{per_txt}</div>', unsafe_allow_html=True)
    runs = all_runs[(all_runs["date"] >= p_from) & (all_runs["date"] <= p_to)] if len(all_runs) else all_runs
    if not len(runs):
        st.info(f"No hay carreras registradas entre {per_txt}.")
    else:
        hmax = float(max(1.0, math.ceil(runs["elapsed"].max() / 3600 * 4) / 4))
        kmax = float(max(1.0, math.ceil(runs["km"].max())))
        dmax = int(max(100, math.ceil(runs["dp"].max() / 50) * 50))
        f1, f2c, f3c = st.columns(3)
        with f1:
            dp_rng = st.slider("Desnivel positivo (m)", 0, dmax, (min(500, dmax), dmax), 50, key="lg_dp")
        with f2c:
            km_rng = st.slider("Distancia (km)", 0.0, kmax, (0.0, kmax), 0.5, key="lg_km", format="%.1f km")
        with f3c:
            h_rng = st.slider("Tiempo total de la actividad (h)", 0.0, hmax, (0.0, hmax), 0.25, key="lg_h", format="%.2f h")
        tipos = st.pills("Tipo", ["Trail", "Asfalto"], selection_mode="multi", default=["Trail", "Asfalto"], key="lg_tipo")
        sel_sports = {"Trail": "TrailRun", "Asfalto": "Run"}
        eh = runs["elapsed"] / 3600
        lg = runs[runs["dp"].between(*dp_rng) & runs["km"].between(*km_rng) & eh.between(*h_rng)
                  & runs["sport"].isin([sel_sports[t] for t in (tipos or [])])].sort_values("ts", ascending=False)
        if len(lg):
            tot_km, tot_dp, tot_h = lg["km"].sum(), lg["dp"].sum(), lg["elapsed"].sum() / 3600
            cards([
                ("Entrenamientos", GOLD, fnum(len(lg)), "", [f"de {len(runs)} carreras · {per_txt}"]),
                ("Distancia", INK, fnum(tot_km, 1), "km", [f"media {fnum(tot_km / len(lg), 1)} km"]),
                ("Desnivel", GOLD, fnum(tot_dp), "m", [f"media {fnum(tot_dp / len(lg))} m · {fnum(tot_dp / tot_km if tot_km else 0)} m/km"]),
                ("Tiempo total", TEAL, f"{int(tot_h)}:{int(round(tot_h % 1 * 60)) % 60:02d}", "h", [f"media {fnum(tot_h / len(lg), 1)} h"]),
            ])
            hm = lambda s: f"{int(s // 3600)}:{int(s % 3600 // 60):02d}"  # noqa: E731
            ALLC = ["Tipo", "Distancia", "D+", "D−", "Tiempo total", "Tiempo mov.", "Ritmo", "Carga", "Cardio med",
                    "Cardio máx", "Calorías", "Carbs", "Sensación"]
            DEF = ["Tipo", "Distancia", "D+", "Tiempo total", "Ritmo", "Carga"]
            o1, o2 = st.columns([3, 1])
            with o1:
                show = st.multiselect("Columnas", ALLC, default=DEF, key="lg_cols")
            with o2:
                orden = st.selectbox("Ordenar por", ["Fecha", "D+", "Distancia", "Tiempo total", "Carga"], key="lg_sort")
            okey = {"Fecha": "ts", "D+": "dp", "Distancia": "km", "Tiempo total": "elapsed", "Carga": "load"}[orden]
            lg2 = lg.sort_values(okey, ascending=False)
            pace_f = lambda p: f"{int(p // 60)}:{int(round(p % 60)) % 60:02d}" if pd.notna(p) and p > 0 else ""  # noqa: E731
            full = pd.DataFrame({
                "Fecha": lg2["ts"].dt.strftime("%d/%m/%y").values,
                "Entrenamiento": lg2["name"].values,
                "Tipo": lg2["sport"].values,
                "Distancia": lg2["km"].values, "D+": lg2["dp"].values, "D−": lg2["dm"].values,
                "Tiempo total": lg2["elapsed"].values, "Tiempo mov.": lg2["secs"].values, "Ritmo": lg2["pace"].values,
                "Carga": lg2["load"].values, "Cardio med": lg2["hr_avg"].values, "Cardio máx": lg2["hr_max"].values,
                "Calorías": lg2["kcal"].values, "Carbs": lg2["carbs"].values, "Sensación": lg2["feel"].values,
            })
            view = full[["Fecha", "Entrenamiento"] + [c for c in ALLC if c in show]]
            chip = lambda v: (f'<span class="chip" style="--c:{GOLD};--o:{on(GOLD)}">Trail</span>' if v == "TrailRun"  # noqa: E731
                              else f'<span class="chip" style="--c:{INK};--o:{on(INK)}">Asfalto</span>')
            num = lambda d, u="": (lambda v: "" if pd.isna(v) else f"{fnum(v, d)}{u}")  # noqa: E731
            name_f = lambda v: (str(v)[:38] + "…") if len(str(v)) > 39 else str(v)  # noqa: E731
            html_table(view, left={"Entrenamiento", "Tipo"}, max_height=620,
                       fmt={"Entrenamiento": name_f, "Tipo": chip, "Distancia": num(1, " km"), "D+": num(0, " m"), "D−": num(0, " m"),
                            "Tiempo total": hm, "Tiempo mov.": hm, "Ritmo": pace_f, "Carga": num(0), "Cardio med": num(0),
                            "Cardio máx": num(0), "Calorías": num(0), "Carbs": num(0, " g"),
                            "Sensación": lambda v: "" if pd.isna(v) else f"{int(v)}/5"},
                       heat={"D+": (float(max(1, lg2["dp"].max())), rgb(GOLD))} if "D+" in show else None)
            fig_l = go.Figure()
            fig_l.add_scatter(x=lg["km"], y=lg["dp"], mode="markers", text=lg["name"],
                              customdata=np.stack([lg["ts"].dt.strftime("%d/%m/%Y"), lg["elapsed"].map(hm)], axis=-1),
                              marker=dict(size=np.clip(lg["elapsed"] / 3600 * 6, 6, 30),
                                          color=np.where(lg["sport"] == "TrailRun", GOLD, INK), opacity=.85, line=dict(width=0)),
                              hovertemplate="%{customdata[0]} · %{text}<br>%{x:.1f} km · %{y:.0f} m D+ · %{customdata[1]} h<extra></extra>",
                              showlegend=False)
            fig_l.update_xaxes(title="km", ticksuffix="")
            fig_l.update_yaxes(title="D+ m")
            st.markdown('<span class="note">Distancia frente a desnivel; el tamaño del punto es el tiempo total. Dorado = trail, blanco = asfalto.</span>', unsafe_allow_html=True)
            st.plotly_chart(plot_layout(fig_l, 300, legend=False), width="stretch", theme=None)
        else:
            st.info("Ninguna carrera cumple los filtros. Amplía los rangos para ver más.")

with tab_cinta:
    st.subheader("Pendiente de las sesiones de cinta")
    if st.session_state.get("cinta_msg"):
        st.success(st.session_state.pop("cinta_msg"))
    st.markdown(
        f'<span class="note">El reloj no registra el desnivel en cinta. Indica la <b>pendiente media (%)</b> de cada sesión y se calculará '
        f'su D+ (km × pendiente). Se guarda en intervals.icu, en el campo personalizado de actividad <b>{INCLINE_FIELD}</b>, '
        f'así queda junto a la actividad y lo verás desde cualquier dispositivo.</span>', unsafe_allow_html=True)
    tm_ = all_df[all_df["sport"].isin(CINTA)].sort_values("ts", ascending=False) if len(all_df) else all_df
    periodo = st.segmented_control("Periodo cinta", ["30 días", "90 días", f"Año {year}", "Todo"], default="90 días",
                                   label_visibility="collapsed", key="cinta_rng") or "90 días"
    if periodo == "30 días":
        tm_ = tm_[tm_["date"] >= today - dt.timedelta(days=30)]
    elif periodo == "90 días":
        tm_ = tm_[tm_["date"] >= today - dt.timedelta(days=90)]
    elif periodo.startswith("Año"):
        tm_ = tm_[tm_["ts"].dt.year == year]
    if not len(tm_):
        st.info("No hay sesiones de cinta en este periodo.")
    else:
        pend_n = int(tm_["incline"].isna().sum())
        cards([
            ("Sesiones", GLACIER, fnum(len(tm_)), "", [f"{pend_n} sin pendiente" if pend_n else "todas con pendiente"]),
            ("Km cinta", GLACIER, fnum(tm_["km"].sum(), 1), "km", ["&nbsp;"]),
            ("D+ cinta", GOLD, fnum(tm_["dp"].sum()), "m", ["sumado al D+ total" if cinta_dp else "no se suma (desactivado)"]),
            ("Pendiente media", ORANGE, fnum((tm_["dp"].sum() / (tm_["km"].sum() * 10)) if tm_["km"].sum() else 0, 1), "%", ["ponderada por km"]),
        ])
        MAXR = 40
        rows_c = tm_.head(MAXR)
        if len(tm_) > MAXR:
            st.caption(f"Se muestran las {MAXR} sesiones más recientes de {len(tm_)}. Acota el periodo para ver otras.")
        CW_ = [1.1, 2.8, 0.9, 0.9, 1.3, 1.0]
        hc = st.columns(CW_, vertical_alignment="center")
        for col, (t, r) in zip(hc, [("Fecha", ""), ("Sesión", ""), ("Km", "r"), ("Tiempo", "r"), ("Pendiente %", ""), ("D+ m", "r")]):
            col.markdown(f'<div class="chd {r}">{t}</div>', unsafe_allow_html=True)
        with st.form("cinta_form", border=False):
            inputs = {}
            for i, (_, rw) in enumerate(rows_c.iterrows()):
                with st.container(key=f"crow{'E' if i % 2 else 'O'}_{i}"):
                    cc = st.columns(CW_, vertical_alignment="center")
                    cc[0].markdown(f'<div class="ctd" style="font-family:IBM Plex Mono,monospace">{rw["ts"].strftime("%d/%m/%y")}</div>', unsafe_allow_html=True)
                    cc[1].markdown(f'<div class="ctd" title="{rw["name"]}">{rw["name"]}</div>', unsafe_allow_html=True)
                    cc[2].markdown(f'<div class="ctd r">{fnum(rw["km"], 2)}</div>', unsafe_allow_html=True)
                    cc[3].markdown(f'<div class="ctd r">{int(rw["secs"] // 3600)}:{int(rw["secs"] % 3600 // 60):02d}</div>', unsafe_allow_html=True)
                    inputs[rw["id"]] = cc[4].number_input(
                        "Pendiente %", min_value=0.0, max_value=40.0, step=0.5, format="%.1f",
                        value=None if pd.isna(rw["incline"]) else float(rw["incline"]),
                        placeholder="—", label_visibility="collapsed", key=f"inc_{rw['id']}")
                    dpv = rw["dp"]
                    cc[5].markdown(f'<div class="ctd r" style="color:{GOLD if dpv > 0 else ZERO}">{fnum(dpv) if dpv > 0 else "0"}</div>',
                                   unsafe_allow_html=True)
            cA, cB = st.columns([1, 3], vertical_alignment="center")
            with cA:
                save = st.form_submit_button("Guardar en intervals.icu", type="primary", width="stretch")
            with cB:
                st.caption("Escribe la pendiente media y pulsa Guardar; el D+ se recalcula al guardar. Antes del primer guardado, crea en "
                           f"intervals.icu un campo personalizado de actividad, numérico, con el código `{INCLINE_FIELD}`.")
        orig = rows_c.set_index("id")["incline"]
        changed = []
        for act_id, val in inputs.items():
            o = orig[act_id]
            if (val is None and pd.isna(o)) or (val is not None and pd.notna(o) and abs(val - o) < 1e-9):
                continue
            changed.append((act_id, np.nan if val is None else val))
        if save and not changed:
            st.info("No hay cambios que guardar.")
        if save and changed:
            ov = dict(st.session_state.get("incline_overrides", {}))
            ok, fails = 0, []
            for act_id, val in changed:
                v = None if pd.isna(val) else float(val)
                if demo:
                    ok += 1
                    ov[act_id] = v
                    continue
                try:
                    r = requests.put(f"{API}/activity/{act_id}", json={INCLINE_FIELD: v}, auth=("API_KEY", key),
                                     headers={"Accept": "application/json", "User-Agent": "LlibretaD+ (Streamlit)"}, timeout=30)
                    if r.status_code >= 400:
                        fails.append(f"{act_id}: error {r.status_code} {r.text[:120]}")
                    else:
                        ok += 1
                        ov[act_id] = v
                except Exception as e:  # noqa: BLE001
                    fails.append(f"{act_id}: {e}")
            st.session_state["incline_overrides"] = ov
            if fails:
                st.error("No se pudieron guardar algunas pendientes:\n\n" + "\n\n".join(fails))
            if ok:
                st.cache_data.clear()
                st.session_state["cinta_msg"] = f"Guardadas {ok} pendientes en intervals.icu."
                st.rerun()

st.caption("Datos leídos en directo de la API de intervals.icu con tu clave personal. Duplicados (misma hora, deporte y duración) se cuentan una vez.")
