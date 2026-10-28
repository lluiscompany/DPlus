"""Llibreta D+ · dashboard de trail running sobre intervals.icu (Streamlit)."""
from __future__ import annotations

import datetime as dt
import html as _html
import json
import math
import os
import random

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote_plus

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
.shoes {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; margin: 6px 0 16px; }}
@media (max-width: 640px) {{ .shoes {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
  .shoe {{ padding: 8px; }} .shoe .km {{ font-size: 22px; }} .shoe .ph {{ font-size: 40px; }} }}
.shoe {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; padding: 10px; display: grid; gap: 4px; min-width: 0; }}
.shoe.ret {{ opacity: .62; }}
.shoe .ph {{ aspect-ratio: 1; border-radius: 6px; background: #ffffff; display: flex; align-items: center; justify-content: center;
             overflow: hidden; font-size: 54px; position: relative; }}
.shoe .ph.no {{ background: {SURFACE2}; }}
.shoe .ph .im {{ position: absolute; inset: 0; background-size: contain; background-position: center; background-repeat: no-repeat; }}
.shoe .nm {{ font: 600 17px/1.1 "Barlow Condensed", sans-serif; color: {INK}; margin-top: 4px; }}
.shoe .br {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: {MUTED}; }}
.shoe .km {{ font: 600 26px/1 "Barlow Condensed", sans-serif; color: {INK}; font-variant-numeric: tabular-nums; }}
.shoe .km small {{ font: 400 12px "IBM Plex Sans", sans-serif; color: {MUTED}; margin-left: 3px; }}
.shoe .ln {{ font-size: 12px; color: {MUTED}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.bar {{ height: 6px; border-radius: 3px; background: {GRID}; overflow: hidden; margin-top: 2px; }}
.bar > span {{ display: block; height: 100%; background: var(--c); }}
.shoe .st {{ position: absolute; top: 6px; left: 6px; font-size: 10.5px; padding: 1px 6px; border-radius: 2px; background: var(--c); color: var(--o); }}
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
.stNumberInput button {{ background: {SURFACE2} !important; color: {INK} !important; border-color: {LINE} !important; }}
.stNumberInput button:hover {{ background: {HOVER} !important; color: {GOLD} !important; }}
.stNumberInput button svg, .stNumberInput button span {{ color: {INK} !important; fill: {INK} !important; }}
.stButton button[kind="secondary"], [data-testid="stBaseButton-secondary"] {{ background: {SURFACE} !important; color: {INK} !important; border-color: {LINE} !important; }}
.stButton button[kind="secondary"] p {{ color: {INK} !important; }}
.stCheckbox label:has(input:not(:checked)) > div:nth-of-type(1) {{ background: {LINE} !important; }}
.stCheckbox label:has(input:not(:checked)) > div:nth-of-type(1) > div {{ background: {SURFACE} !important; box-shadow: 0 0 0 1px {MUTED}; }}
.stTabs button p {{ color: {INK}; }}
.stSlider [data-testid="stSliderTickBarMin"], .stSlider [data-testid="stSliderTickBarMax"] {{ color: {MUTED}; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{ color: {INK}; }}
[data-testid="stSidebar"] .stButton button p {{ color: {on(GOLD)}; }}
[data-testid="stHeader"] {{ color: {INK}; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {MUTED} !important; }}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], .stTextArea textarea, .stDateInput input,
[data-testid="stDateInputField"], .stTextInput input {{ background: {SURFACE} !important; color: {INK} !important; border-color: {LINE} !important; }}
[data-baseweb="input"], [data-baseweb="textarea"] {{ border: 1px solid {LINE} !important; }}
.stTextInput div:has(> input), .stNumberInput div:has(> input), .stTextArea div:has(> textarea), .stDateInput div:has(> input) {{
  background: {SURFACE} !important; border-color: {LINE} !important; }}
.stTextInput div:has(> input):focus-within, .stNumberInput div:has(> input):focus-within,
.stTextArea div:has(> textarea):focus-within {{ border-color: {GOLD} !important; }}
.stNumberInput div:has(> input) > button, .stNumberInput div:has(> input) > div > button {{ background: transparent !important; }}
.stNumberInput div:has(> input) svg {{ color: {MUTED} !important; fill: {MUTED} !important; }}
input::placeholder, textarea::placeholder {{ color: {MUTED} !important; opacity: 1; }}
[data-testid="stLinkButton"] a {{ background: {SURFACE} !important; color: {INK} !important; border: 1px solid {LINE} !important; }}
[data-testid="stLinkButton"] a p, [data-testid="stLinkButton"] a span {{ color: {INK} !important; }}
[data-testid="stLinkButton"] a:hover {{ border-color: {GOLD} !important; }}
[data-baseweb="calendar"], [data-baseweb="calendar"] * {{ background-color: {SURFACE}; color: {INK}; }}
[data-baseweb="calendar"] [aria-selected="true"] div {{ background-color: {GOLD} !important; color: {on(GOLD)} !important; }}
.stTooltipIcon svg, [data-testid="stTooltipHoverTarget"] svg {{ color: {MUTED}; fill: {MUTED}; }}
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
        gear_id=(a.get("gear") or {}).get("id"), gear_name=(a.get("gear") or {}).get("name"),
        device=a.get("device_name"),
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
                        incline=rnd.choice([None, None, 3, 5, 8]) if s == "VirtualRun" else None,
                        gear_id=demo_gear_for(s, d, rnd), gear_name=None, device="SUUNTO Suunto Race 2"))
        d += dt.timedelta(days=rnd.choice([1, 1, 2, 3]))
    # Tres salidas de ejemplo por la misma ruta (para la pestaña Comparar)
    for aid, day, km, dp, dev, secs, el in DEMO_ROUTE:
        if day.year == year and day <= today:
            out.append(dict(id=aid, start=f"{day}T08:15:00", sport="TrailRun", name="Ruta de ejemplo (3 cimas)", km=km, dp=dp, dm=dp * .99,
                            secs=secs, elapsed=el, load={"demoRA": 246, "demoRB": 280}.get(aid, 298),
                            hr_avg={"demoRA": 137, "demoRB": 144}.get(aid, 142), hr_max=170, kcal=2400, carbs=None, feel=3,
                            pace=secs / km, incline=None, gear_id="gd1", gear_name=None, device=dev))
    return out


def to_frame(rows: list[dict], hike: bool, cinta_dp: bool = True, overrides: dict | None = None) -> pd.DataFrame:
    cols = ["id", "start", "sport", "name", "km", "dp", "dm", "secs", "elapsed", "load", "hr_avg", "hr_max", "kcal", "carbs", "feel", "pace",
            "incline", "gear_id", "gear_name", "device"]
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
    is_run = df["sport"].isin(OUT)
    df["dp_run"] = np.where(is_run, df["dp"], 0.0)
    df["km_run"] = np.where(is_run, df["km"], 0.0)
    df["dp_hike"] = np.where(hike & (df["sport"] == "Hike"), df["dp"], 0.0)
    df["dp_cinta"] = np.where(cinta_up, df["dp"], 0.0)
    df["cinta_km"] = np.where(df["sport"].isin(CINTA), df["km"], 0.0)
    df["gim_min"] = np.where(df["sport"].isin(GIM), df["secs"] / 60, 0.0)
    df["hours"] = df["secs"] / 3600
    return df


def totals(d: pd.DataFrame) -> dict:
    dp, km, ukm = d["out_dp"].sum(), d["out_km"].sum(), d["ukm"].sum() if "ukm" in d else d["out_km"].sum()
    return dict(dp=dp, km=km, cinta=d["cinta_km"].sum(), gim=d["gim_min"].sum(), n=len(d),
                load=d["load"].sum(), h=d["hours"].sum(), ultra=1.7 * dp / ukm if ukm > 0 else 0.0,
                kmE=km + d["cinta_km"].sum() + dp / 100,
                **{c: (d[c].sum() if c in d else 0.0) for c in ("dp_run", "dp_hike", "dp_cinta")})


# Origen del desnivel: carrera (Run/TrailRun), caminata y cinta (según los interruptores)
DP_SRC = [("dp_run", "Carrera", "GOLD"), ("dp_hike", "Caminata", "ORANGE"), ("dp_cinta", "Cinta", "GLACIER")]


def src_color(name: str) -> str:
    return globals()[name]


def dp_split_line(t: dict) -> str:
    """Desglose del D+ por origen, solo si hay caminata o cinta."""
    if not (t.get("dp_hike", 0) > 0 or t.get("dp_cinta", 0) > 0):
        return ""
    parts = [f'<span style="color:{src_color(c)}">●</span> {lab.lower()} {fnum(t[k])}' for k, lab, c in DP_SRC if t.get(k, 0) > 0]
    return " · ".join(parts)


# ─────────────────────────── Material (zapatillas) ───────────────────────────
SHOE_SPORTS = {"Run": "Carrera", "TrailRun": "Trail", "VirtualRun": "Cinta", "Hike": "Caminata", "Walk": "Caminata"}
NOTE_KEYS = ("marca", "modelo", "foto", "km_previos")
_DEMO_GEAR = [
    dict(id="gd1", type="Shoes", name="La Sportiva Prodigio Pro", purchased="2026-04-22T00:00:00", retired=None,
         notes="marca: La Sportiva\nmodelo: Prodigio Pro\nfoto: https://encrypted-tbn3.gstatic.com/shopping?q=tbn:ANd9GcTm8FFUwmA43OFdiH4vY3tXT-SR1AECBDa2iyOKhp_7ytrjBkOsldWf75f07a2e-o1nVxHCxzoUX489TBsPT_lmTcqlUstbu7U1j-NMGwwrmeGAM3wpD9k1UKInCwXgntKLmnI71mAHraE&usqp=CAc",
         reminders=[dict(id=1, name="Límite de km", distance=800000.0)]),
    dict(id="gd2", type="Shoes", name="ASICS Gel Fuji Trabuco 13", purchased="2024-12-29T00:00:00", retired=None,
         notes="marca: ASICS\nmodelo: Gel Fuji Trabuco 13\nfoto: https://example.invalid/trabuco13.jpg\nTalla 43,5", reminders=[dict(id=2, name="Límite de km", distance=700000.0)]),
    dict(id="gd3", type="Shoes", name="ASICS nimbus 16", purchased="2016-05-11T00:00:00", retired=None,
         notes="marca: ASICS\nmodelo: nimbus 16\nkm_previos: 163.9", reminders=[]),
    dict(id="gd4", type="Shoes", name="PUMA Deviate Nitro 2", purchased="2023-06-08T00:00:00", retired=None,
         notes="marca: PUMA\nmodelo: Deviate Nitro 2", reminders=[dict(id=4, name="Límite de km", distance=400000.0)]),
    dict(id="gd5", type="Shoes", name="La Sportiva Akyra", purchased="2019-04-29T00:00:00", retired="2020-03-05T00:00:00",
         notes="marca: La Sportiva\nmodelo: Akyra\nkm_previos: 219.1", reminders=[]),
]


def demo_gear_for(sport: str, d: dt.date, rnd: random.Random):
    """Zapatilla de ejemplo según el tipo y la fecha (respeta compras y retiradas)."""
    if sport == "VirtualRun":
        return "gd3"
    if sport == "TrailRun":
        if d >= dt.date(2026, 4, 22):
            return "gd1"
        if d >= dt.date(2024, 12, 29):
            return "gd2"
        return "gd5" if dt.date(2019, 4, 29) <= d <= dt.date(2020, 3, 5) else None
    if sport == "Run":
        return "gd4" if d >= dt.date(2023, 6, 8) else None
    if sport == "Hike":
        return rnd.choice(["gd2", None]) if d >= dt.date(2024, 12, 29) else None
    return None


def parse_notes(notes: str | None) -> dict:
    """Notas del gear → {marca, modelo, foto, km_previos, libre}. Las claves van una por línea: 'clave: valor'."""
    out, libre = {k: "" for k in NOTE_KEYS}, []
    for ln in (notes or "").splitlines():
        k, sep, v = ln.partition(":")
        if sep and k.strip().lower() in NOTE_KEYS and (k.strip().lower() != "foto" or v.strip().startswith("http")):
            out[k.strip().lower()] = v.strip()
        else:
            libre.append(ln)
    try:
        out["km_previos"] = float(str(out["km_previos"]).replace(",", ".")) if out["km_previos"] else 0.0
    except ValueError:
        out["km_previos"] = 0.0
    out["libre"] = "\n".join(libre).strip()
    return out


def build_notes(marca: str, modelo: str, foto: str, km_previos: float, libre: str) -> str:
    lines = [f"marca: {marca.strip()}", f"modelo: {modelo.strip()}"]
    if foto.strip():
        lines.append(f"foto: {foto.strip()}")
    if km_previos:
        lines.append(f"km_previos: {km_previos:.1f}")
    return "\n".join(lines + ([libre.strip()] if libre.strip() else []))


def km_limit(g: dict):
    """Límite de km: aviso (GearReminder) con distancia. La API usa metros."""
    for r in g.get("reminders") or []:
        if (r.get("distance") or 0) > 0:
            return r, float(r["distance"]) / 1000
    return None, None


def iso_date(v) -> dt.date | None:
    try:
        return pd.to_datetime(v).date() if v else None
    except (ValueError, TypeError):
        return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_gear(athlete: str, key: str) -> list[dict]:
    r = requests.get(f"{API}/athlete/{athlete}/gear", auth=("API_KEY", key),
                     headers={"Accept": "application/json", "User-Agent": "LlibretaD+ (Streamlit)"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


@st.cache_data(ttl=3600, show_spinner=False)
def image_ok(url: str) -> bool:
    """Comprueba (cacheado) que la URL responde con una imagen."""
    if not url or not url.startswith("http"):
        return False
    try:
        h = {"User-Agent": "Mozilla/5.0 (LlibretaD+)"}
        r = requests.head(url, headers=h, timeout=5, allow_redirects=True)
        if r.status_code >= 400 or not r.headers.get("Content-Type", "").startswith("image"):
            r = requests.get(url, headers=h, timeout=6, stream=True)
            r.close()
        return r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image")
    except requests.RequestException:
        return False


def icu_write(method: str, path: str, body=None):
    """Escritura en intervals.icu (o en la memoria de la sesión en DEMO). Devuelve el JSON de respuesta."""
    r = requests.request(method, f"{API}{path}", json=body, auth=("API_KEY", key), timeout=30,
                         headers={"Accept": "application/json", "User-Agent": "LlibretaD+ (Streamlit)"})
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path.split('?')[0]} → HTTP {r.status_code}: {r.text[:160]}")
    return r.json() if r.content else None


# ─────────────────────────── Comparar: datos por segundo y análisis ───────────────────────────
STREAM_TYPES = "time,distance,altitude,heartrate,velocity_smooth,latlng,cadence"
BANDS = [(-1e9, -20, "≤ −20 %"), (-20, -10, "−20/−10 %"), (-10, -3, "−10/−3 %"), (-3, 3, "Llano ±3 %"),
         (3, 10, "3/10 %"), (10, 20, "10/20 %"), (20, 30, "20/30 %"), (30, 1e9, "> 30 %")]
# id, fecha, km, D+, reloj, tiempo en movimiento, tiempo total (DEMO)
DEMO_ROUTE = [("demoRA", dt.date(2026, 10, 24), 21.36, 1395, "SUUNTO Suunto Race 2", 13708, 14485),
              ("demoRB", dt.date(2025, 11, 1), 21.73, 1395, "SUUNTO Suunto 9", 13619, 14021),
              ("demoRC", dt.date(2025, 9, 24), 21.78, 1377, "SUUNTO Suunto 9", 14524, 15924)]


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_streams(key: str, act_id: str) -> list:
    r = requests.get(f"{API}/activity/{act_id}/streams.json", params={"types": STREAM_TYPES}, auth=("API_KEY", key),
                     headers={"Accept": "application/json", "User-Agent": "LlibretaD+ (Streamlit)"}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fit_streams(key: str, act_id: str) -> list:
    """Alternativa: fichero original (FIT) de la actividad, convertido al formato de streams."""
    try:
        import fitdecode
    except ImportError:
        return []
    import gzip
    import io
    r = requests.get(f"{API}/activity/{act_id}/file", auth=("API_KEY", key),
                     headers={"User-Agent": "LlibretaD+ (Streamlit)"}, timeout=90)
    if r.status_code >= 400 or not r.content:
        return []
    blob = r.content
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    recs = []
    try:
        with fitdecode.FitReader(io.BytesIO(blob)) as fr:
            for f in fr:
                if isinstance(f, fitdecode.FitDataMessage) and f.name == "record":
                    g = lambda k: f.get_value(k) if f.has_field(k) else None  # noqa: E731
                    recs.append((g("timestamp"), g("distance"), g("enhanced_altitude") if f.has_field("enhanced_altitude") else g("altitude"),
                                 g("heart_rate"), g("enhanced_speed") if f.has_field("enhanced_speed") else g("speed"),
                                 g("position_lat"), g("position_long"), g("cadence")))
    except Exception:  # noqa: BLE001
        return []
    recs = [x for x in recs if x[0] is not None]
    if not recs:
        return []
    t0, sc = recs[0][0], 180 / 2 ** 31
    col = lambda i: [x[i] for x in recs]  # noqa: E731
    return [dict(type="time", data=[int((x[0] - t0).total_seconds()) for x in recs]),
            dict(type="distance", data=col(1)), dict(type="altitude", data=col(2)), dict(type="heartrate", data=col(3)),
            dict(type="velocity_smooth", data=col(4)), dict(type="cadence", data=col(7)),
            dict(type="latlng", data=[v * sc if v is not None else None for v in col(5)],
                 data2=[v * sc if v is not None else None for v in col(6)])]


def streams_to_df(raw: list) -> pd.DataFrame:
    """Streams de intervals.icu → DataFrame limpio (t, dist, alt, alt_s, hr, v, lat, lng, cad, dt, mov)."""
    m = {s_.get("type"): s_ for s_ in (raw or []) if isinstance(s_, dict)}

    def arr(t, k="data"):
        v = (m.get(t) or {}).get(k)
        return None if v is None else pd.to_numeric(pd.Series(list(v), dtype="object"), errors="coerce").astype(float)

    t = arr("time")
    if t is None or len(t) < 30:
        return pd.DataFrame()
    n = len(t)
    df = pd.DataFrame({"t": t.values})
    for c, typ, k in [("dist", "distance", "data"), ("alt", "altitude", "data"), ("hr", "heartrate", "data"),
                      ("v", "velocity_smooth", "data"), ("cad", "cadence", "data"), ("lat", "latlng", "data"), ("lng", "latlng", "data2")]:
        a = arr(typ, k)
        df[c] = a.values if a is not None and len(a) == n else np.nan
    return clean_stream(df)


def clean_stream(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["t"]).sort_values("t").drop_duplicates("t").reset_index(drop=True)
    ok = (df["dist"].notna() & df["alt"].notna()).to_numpy()
    if ok.sum() < 30:
        return pd.DataFrame()
    i0, i1 = int(np.argmax(ok)), len(ok) - 1 - int(np.argmax(ok[::-1]))   # sin nulls al principio ni al final
    df = df.iloc[i0:i1 + 1].reset_index(drop=True)
    for c in ("dist", "alt", "hr", "v", "cad"):
        df[c] = df[c].interpolate(limit=10, limit_area="inside")          # huecos cortos (≤ 10 muestras)
    for c in ("lat", "lng"):                                              # GPS en modo ahorro: huecos más largos
        df[c] = df[c].interpolate(limit=120, limit_area="inside")
    df["dist"] = df["dist"].ffill().cummax()
    df["alt"] = df["alt"].ffill()
    df["dt"] = df["t"].diff().fillna(0).clip(0, 10)
    if df["v"].notna().sum() < len(df) * .5:
        dd = df["dist"].diff().fillna(0)
        df["v"] = (dd.rolling(5, min_periods=1).sum() / df["t"].diff().fillna(1).clip(lower=1).rolling(5, min_periods=1).sum())
    df["mov"] = (df["v"].fillna(0) >= 0.25) & (df["dt"] > 0)
    df["alt_s"] = df["alt"].rolling(15, center=True, min_periods=1).median().rolling(9, center=True, min_periods=1).mean()
    return df


def stream_stats(df: pd.DataFrame) -> dict:
    d_alt = df["alt_s"].diff().fillna(0)
    mt = float((df["dt"] * df["mov"]).sum())
    w = df["dt"] * df["mov"]
    hr = float((df["hr"] * w).sum() / w[df["hr"].notna()].sum()) if df["hr"].notna().any() and w[df["hr"].notna()].sum() > 0 else np.nan
    return dict(km=float(df["dist"].iloc[-1] - df["dist"].iloc[0]) / 1000, mov=mt, elapsed=float(df["t"].iloc[-1] - df["t"].iloc[0]),
                dp=float(d_alt.clip(lower=0).sum()), dm=float(-d_alt.clip(upper=0).sum()), hr=hr)


def grade_bands(df: pd.DataFrame, seg_m: float = 100) -> pd.DataFrame:
    """Estadísticas por banda de pendiente (segmentos de seg_m metros)."""
    x = df.assign(seg=((df["dist"] - df["dist"].iloc[0]) // seg_m).astype(int), w=df["dt"] * df["mov"])
    x["hrw"] = x["hr"].fillna(0) * x["w"]
    x["wh"] = np.where(x["hr"].notna(), x["w"], 0)
    g = x.groupby("seg").agg(d0=("dist", "first"), a0=("alt_s", "first"), mt=("w", "sum"), hrw=("hrw", "sum"), wh=("wh", "sum"))
    g["dist"] = g["d0"].shift(-1).fillna(df["dist"].iloc[-1]) - g["d0"]
    g["dalt"] = g["a0"].shift(-1).fillna(df["alt_s"].iloc[-1]) - g["a0"]
    g = g[g["dist"] > 20]
    g["grade"] = 100 * g["dalt"] / g["dist"]
    g["band"] = pd.cut(g["grade"], [b[0] for b in BANDS] + [BANDS[-1][1]], labels=[b[2] for b in BANDS])
    tot = g["mt"].sum() or 1
    rows = []
    for lab in [b[2] for b in BANDS]:
        b = g[g["band"] == lab]
        km, mt = b["dist"].sum() / 1000, b["mt"].sum()
        up, dn = b["dalt"].clip(lower=0).sum(), -b["dalt"].clip(upper=0).sum()
        rows.append(dict(band=lab, km=km, pct_t=100 * mt / tot, dp=up, dm=dn, mt=mt,
                         pace=(mt / km) if km > 0 and mt > 0 else np.nan,
                         vam=(up / mt * 3600) if mt > 0 and up > dn else np.nan,
                         vdesc=(dn / mt * 3600) if mt > 0 and dn > up else np.nan,
                         hr=(b["hrw"].sum() / b["wh"].sum()) if b["wh"].sum() > 0 else np.nan))
    return pd.DataFrame(rows)


def _xy_m(lat, lng, lat0):
    return (np.asarray(lng) * 111320 * math.cos(math.radians(lat0)), np.asarray(lat) * 110540)


def route_similarity(a: pd.DataFrame, b: pd.DataFrame) -> dict | None:
    """Parecido del recorrido con GPS: desviación media entre trazas, distancia entre inicios y entre puntos más altos."""
    pa, pb = a.dropna(subset=["lat", "lng"]), b.dropna(subset=["lat", "lng"])
    if len(pa) < 50 or len(pb) < 50:
        return None
    lat0 = float(pa["lat"].iloc[0])
    sa = pa.iloc[np.linspace(0, len(pa) - 1, 80).astype(int)]
    sb = pb.iloc[::max(1, len(pb) // 2000)]
    ax, ay = _xy_m(sa["lat"], sa["lng"], lat0)
    bx, by = _xy_m(sb["lat"], sb["lng"], lat0)
    dmin = np.sqrt((ax[:, None] - bx[None, :]) ** 2 + (ay[:, None] - by[None, :]) ** 2).min(axis=1)
    p2 = lambda r1, r2: float(np.hypot(*(np.subtract(_xy_m(r1["lat"], r1["lng"], lat0), _xy_m(r2["lat"], r2["lng"], lat0)))))  # noqa: E731
    start = p2(pa.iloc[0], pb.iloc[0])
    ta = pa.loc[pa["alt_s"].idxmax()]                 # punto más alto de A → punto de B más cercano
    tx, ty = _xy_m([ta["lat"]], [ta["lng"]], lat0)
    top = float(np.sqrt((bx - tx[0]) ** 2 + (by - ty[0]) ** 2).min())
    dev = float(np.median(dmin))
    p90 = float(np.percentile(dmin, 90))
    label = "misma ruta" if dev < 60 and p90 < 250 else "parecida" if dev < 250 else "distinta"
    return dict(dev=dev, p90=p90, start=start, top=top, label=label)


def find_segments(df: pd.DataFrame, amp: float = 60) -> list[tuple[float, float]]:
    """Subidas y bajadas principales (zigzag sobre la altitud suavizada): lista de (dist_ini, dist_fin)."""
    d = df["dist"].to_numpy()
    grid = np.arange(d[0], d[-1], 20.0)
    if len(grid) < 3:
        return []
    a = np.interp(grid, d, df["alt_s"].to_numpy())
    piv, trend, ext = [0], None, 0
    lo = hi = 0
    for i in range(1, len(a)):
        if trend is None:
            lo, hi = (i if a[i] < a[lo] else lo), (i if a[i] > a[hi] else hi)
            if a[i] - a[lo] >= amp:
                trend, ext = "up", i
                if lo > 0:
                    piv.append(lo)
            elif a[hi] - a[i] >= amp:
                trend, ext = "down", i
                if hi > 0:
                    piv.append(hi)
        elif trend == "up":
            if a[i] > a[ext]:
                ext = i
            elif a[ext] - a[i] >= amp:
                piv.append(ext)
                trend, ext = "down", i
        else:
            if a[i] < a[ext]:
                ext = i
            elif a[i] - a[ext] >= amp:
                piv.append(ext)
                trend, ext = "up", i
    if trend is not None and ext not in piv:
        piv.append(ext)
    if piv[-1] != len(a) - 1:
        piv.append(len(a) - 1)
    piv = sorted(set(piv))
    return [(float(grid[i]), float(grid[j])) for i, j in zip(piv[:-1], piv[1:]) if grid[j] - grid[i] >= 200]


def locate_in(b: pd.DataFrame, a: pd.DataFrame, bounds_a: list[float], use_gps: bool) -> list[float]:
    """Distancias en B equivalentes a cada distancia de A (monótonas)."""
    out, prev = [], float(b["dist"].iloc[0])
    tot_a, tot_b = a["dist"].iloc[-1] - a["dist"].iloc[0], b["dist"].iloc[-1] - b["dist"].iloc[0]
    pa = a.dropna(subset=["lat", "lng"])
    pb = b.dropna(subset=["lat", "lng"])
    lat0 = float(pa["lat"].iloc[0]) if len(pa) else 0.0
    for k, da in enumerate(bounds_a):
        guess = b["dist"].iloc[0] + (da - a["dist"].iloc[0]) * tot_b / tot_a if tot_a > 0 else prev
        if k == 0:
            out.append(float(b["dist"].iloc[0]) if da <= a["dist"].iloc[0] + 1 else guess)
            prev = out[-1]
            continue
        if k == len(bounds_a) - 1 and da >= a["dist"].iloc[-1] - 1:
            out.append(float(b["dist"].iloc[-1]))
            continue
        lo, hi = max(prev, guess - 1500), guess + 1500
        win = (pb if use_gps else b)
        win = win[(win["dist"] >= lo) & (win["dist"] <= hi)]
        if use_gps and len(win) and len(pa):
            ia = int(np.searchsorted(pa["dist"].to_numpy(), da).clip(0, len(pa) - 1))
            ax, ay = _xy_m([pa["lat"].iloc[ia]], [pa["lng"].iloc[ia]], lat0)
            bx, by = _xy_m(win["lat"], win["lng"], lat0)
            j = int(np.argmin((bx - ax[0]) ** 2 + (by - ay[0]) ** 2))
        elif len(win):
            alt_a = float(np.interp(da, a["dist"], a["alt_s"]))
            j = int(np.argmin(np.abs(win["alt_s"].to_numpy() - alt_a) + np.abs(win["dist"].to_numpy() - guess) / 50))
        else:
            out.append(max(prev, guess))
            prev = out[-1]
            continue
        out.append(max(prev, float(win["dist"].iloc[j])))
        prev = out[-1]
    return out


def span_stats(df: pd.DataFrame, d0: float, d1: float) -> dict:
    x = df[(df["dist"] >= d0) & (df["dist"] <= d1)]
    if len(x) < 2:
        return dict(mt=np.nan, el=np.nan, gain=np.nan, loss=np.nan, hr=np.nan, a0=np.nan, a1=np.nan, km=(d1 - d0) / 1000)
    w = x["dt"].iloc[1:] * x["mov"].iloc[1:]
    da = x["alt_s"].diff().fillna(0)
    hrw = (x["hr"].iloc[1:] * w)
    wh = w[x["hr"].iloc[1:].notna()].sum()
    return dict(mt=float(w.sum()), el=float(x["t"].iloc[-1] - x["t"].iloc[0]), gain=float(da.clip(lower=0).sum()),
                loss=float(-da.clip(upper=0).sum()), hr=float(hrw.sum() / wh) if wh > 0 else np.nan,
                a0=float(x["alt_s"].iloc[0]), a1=float(x["alt_s"].iloc[-1]), km=(d1 - d0) / 1000)


def race_align(a: pd.DataFrame, b: pd.DataFrame, use_gps: bool, moving: bool, step_m: float = 25.0, step_t: float = 10.0) -> dict:
    """Carrera virtual: alinea B sobre la ruta de A.

    Devuelve, sobre una rejilla de distancia de A (cada step_m): dA, dB (posición equivalente de B), tA, tB, dT = tB − tA
    (negativo = B por delante), alt de A; y sobre una rejilla de tiempo de carrera (cada step_t): T, posición en la ruta
    de A y B (km de A), distancia propia de cada una, lat/lng, altitud y FC de cada una.
    """
    def clock(d):
        c = (d["dt"] * d["mov"]).cumsum() if moving else d["t"] - d["t"].iloc[0]
        return c.to_numpy(dtype=float)

    ca, cb = clock(a), clock(b)
    da_all, db_all = a["dist"].to_numpy(float) - a["dist"].iloc[0], b["dist"].to_numpy(float) - b["dist"].iloc[0]
    dA = np.arange(0, da_all[-1], step_m)
    tot_a, tot_b = da_all[-1], db_all[-1]
    # posición equivalente de B para cada punto de A (búsqueda hacia delante, monótona)
    dB = dA * (tot_b / tot_a if tot_a > 0 else 1)
    off = np.zeros(len(dA), dtype=bool)
    pa, pb = a[["lat", "lng"]].to_numpy(float), b[["lat", "lng"]].to_numpy(float)
    if use_gps and np.isfinite(pa).all(axis=1).mean() > .5 and np.isfinite(pb).all(axis=1).mean() > .5:
        lat0 = float(np.nanmean(pa[:, 0]))
        kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
        ia = np.clip(np.searchsorted(da_all, dA), 0, len(da_all) - 1)
        ax, ay = pa[ia, 1] * kx, pa[ia, 0] * ky
        sub = max(1, len(db_all) // 6000)
        bd, bx, by = db_all[::sub], pb[::sub, 1] * kx, pb[::sub, 0] * ky
        prev = 0.0
        for k in range(len(dA)):                      # ~1 iteración cada 25 m (no por segundo)
            if not (np.isfinite(ax[k]) and np.isfinite(ay[k])):
                dB[k] = max(prev, dB[k])
                prev = dB[k]
                continue
            lo, hi = np.searchsorted(bd, prev - 30), np.searchsorted(bd, prev + 400)
            if hi <= lo:
                dB[k] = max(prev, dB[k])
                prev = dB[k]
                continue
            d2 = (bx[lo:hi] - ax[k]) ** 2 + (by[lo:hi] - ay[k]) ** 2
            j = int(np.nanargmin(d2)) if np.isfinite(d2).any() else 0
            if not np.isfinite(d2[j]) or d2[j] > 150 ** 2:   # fuera de ruta: seguir por proporción
                off[k] = True
                dB[k] = max(prev, min(prev + step_m * tot_b / max(tot_a, 1), tot_b))
            else:
                dB[k] = max(prev, bd[lo + j])
            prev = dB[k]
    tA = np.interp(dA, da_all, ca)
    tB = np.interp(dB, db_all, cb)
    dT = tB - tA
    altA = np.interp(dA, da_all, a["alt_s"].to_numpy(float))
    # rejilla de tiempo de carrera
    endA, endB = float(ca[-1]), float(cb[-1])
    T = np.arange(0, max(endA, endB) + step_t, step_t)
    own_a = np.interp(T, ca, da_all)
    own_b = np.interp(T, cb, db_all)
    posA = own_a                                   # posición en km de la ruta de A
    posB = np.interp(own_b, dB, dA)                # distancia de B convertida a la ruta de A

    def at(df_, c_, col):
        v = df_[col].to_numpy(float)
        ok = np.isfinite(v)
        return np.interp(T, c_[ok], v[ok]) if ok.sum() > 1 else np.full(len(T), np.nan)
    def cum_gain(df_, c_):
        g = np.clip(np.diff(df_["alt_s"].to_numpy(float), prepend=df_["alt_s"].iloc[0]), 0, None).cumsum()
        return np.interp(T, c_, g)
    return dict(dA=dA, dB=dB, tA=tA, tB=tB, dT=dT, altA=altA, off=off, T=T, endA=endA, endB=endB,
                dpA=cum_gain(a, ca), dpB=cum_gain(b, cb),
                posA=posA, posB=posB, ownA=own_a, ownB=own_b, totA=tot_a, totB=tot_b,
                latA=at(a, ca, "lat"), lngA=at(a, ca, "lng"), latB=at(b, cb, "lat"), lngB=at(b, cb, "lng"),
                altTA=at(a, ca, "alt_s"), altTB=at(b, cb, "alt_s"), hrA=at(a, ca, "hr"), hrB=at(b, cb, "hr"))


def race_gap(r: dict, k: int) -> tuple[float, float]:
    """En el instante r['T'][k]: (ventaja en distancia de B en m, ventaja en tiempo de B en s; >0 = B por delante)."""
    pa, pb = r["posA"][k], r["posB"][k]
    dd = pb - pa
    p = min(pa, pb)                                   # el que va detrás pasa por p: tiempo que le saca el de delante
    dt_ = float(np.interp(p, r["dA"], r["dT"]))
    return float(dd), -dt_


# Capas de mapa (sin clave). Condiciones: IGN/CNIG CC BY 4.0 (atribución visible); OpenTopoMap CC-BY-SA;
# Esri World Imagery con atribución; AWS Terrain Tiles (Tilezen/Mapzen, datos abiertos).
_IGN_WMTS = ("https://www.ign.es/wmts/{svc}?service=WMTS&request=GetTile&version=1.0.0&Format=image/{fmt}&layer={layer}"
             "&style=default&tilematrixset=GoogleMapsCompatible&TileMatrix={{z}}&TileRow={{y}}&TileCol={{x}}")
TILESETS = {
    "ign_mtn": dict(urls=[_IGN_WMTS.format(svc="mapa-raster", fmt="jpeg", layer="MTN")],
                    attr="Mapa Topográfico Nacional CC BY 4.0 ign.es", maxzoom=18),
    "otm": dict(urls=[f"https://{s_}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png" for s_ in "abc"],
                attr="© OpenStreetMap, SRTM · estilo © OpenTopoMap (CC-BY-SA)", maxzoom=17),
    "pnoa": dict(urls=[_IGN_WMTS.format(svc="pnoa-ma", fmt="png", layer="OI.OrthoimageCoverage")],
                 attr="PNOA CC BY 4.0 scne.es", maxzoom=19),
    "esri_img": dict(urls=["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                     attr="Tiles © Esri — Esri, Maxar, Earthstar Geographics", maxzoom=19),
    "carto_light": dict(urls=[f"https://{s_}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png" for s_ in "abcd"],
                        attr="© OpenStreetMap © CARTO", maxzoom=19),
    "carto_dark": dict(urls=[f"https://{s_}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png" for s_ in "abcd"],
                       attr="© OpenStreetMap © CARTO", maxzoom=19),
}
TERRAIN_TILES = dict(urls=["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
                     attr="Relieve: Terrain Tiles (Tilezen/Mapzen, AWS Open Data)", maxzoom=15)
MAP_BACKGROUNDS = ["Topográfico", "Satélite", "Callejero", "Sin fondo"]

# Vista 3D de la carrera virtual: MapLibre GL JS (relieve real con teselas de elevación), reproducción en el navegador.
MAP3D_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<style>
 html,body{margin:0;padding:0;background:transparent;font-family:"IBM Plex Sans",system-ui,sans-serif;color:var(--ink)}
 #wrap{display:flex;flex-direction:column;gap:6px}
 #mapbox{position:relative}
 #map{height:440px;border-radius:8px;border:1px solid var(--line);overflow:hidden;background:var(--surface2)}
 #lab{position:absolute;top:8px;left:8px;z-index:5;background:var(--surface);color:var(--ink);border:1px solid var(--line);
      padding:4px 8px;border-radius:4px;font-size:13px;font-weight:600;pointer-events:none}
 #err{display:none;position:absolute;inset:0;z-index:6;padding:24px;font-size:14px;color:var(--ink);background:var(--surface2)}
 .ctl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px;color:var(--muted)}
 button,select{background:var(--surface2);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
 button.on{border-color:var(--A);color:var(--A)}
 input[type=range]{flex:1;min-width:150px;accent-color:var(--A)}
 #tt{font:12px "IBM Plex Mono",monospace;min-width:62px;color:var(--ink)}
 canvas{width:100%;display:block;background:var(--surface);border:1px solid var(--line);border-radius:8px}
 .dot{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;
      font:700 12px "IBM Plex Sans",sans-serif;border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.55)}
 .maplibregl-ctrl-attrib{font-size:10px}
</style></head><body>
<div id="wrap">
 <div id="mapbox"><div id="map"></div><div id="lab"></div><div id="err"></div></div>
 <div class="ctl">
  <button data-sp="30">▶ ×30</button><button data-sp="60">▶ ×60</button><button data-sp="120">▶ ×120</button>
  <button id="pause">⏸</button><input type="range" id="rng" min="0" step="1"><span id="tt"></span>
 </div>
 <div class="ctl">
  <label>Cámara <select id="cam"><option value="fix">Vista fija</option><option value="A">Seguir a A</option><option value="B">Seguir a B</option></select></label>
  <label>Relieve <select id="exa"><option value="1">1×</option><option value="1.5" selected>1,5×</option><option value="2">2×</option></select></label>
 </div>
 <canvas id="prof" style="height:150px"></canvas>
 <canvas id="dp" style="height:110px"></canvas>
</div>
<script>
const D = __PAYLOAD__;
const C = D.col, root = document.documentElement.style;
for (const [k, v] of Object.entries({ink:C.ink, muted:C.muted, line:C.line, surface:C.surface, surface2:C.surface2, A:C.A})) root.setProperty('--'+k, v);
const fmt = (v, d=0) => { const [i, f] = Math.abs(Number(v)).toFixed(d).split('.'); return (v < 0 ? '−' : '') + i.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (f ? ',' + f : ''); };
const hms = s => { s = Math.max(0, Math.round(s)); return `${Math.floor(s/3600)}:${String(Math.floor(s%3600/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`; };
const mmss = s => { s = Math.abs(Math.round(s)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`; };
const T = D.T, n = T.length, tmax = T[n-1];
function fidx(t){ let lo=0, hi=n-1; if (t<=T[0]) return 0; if (t>=T[hi]) return hi; while (hi-lo>1){ const m=(lo+hi)>>1; if (T[m]<=t) lo=m; else hi=m; } return lo + (t-T[lo])/(T[hi]-T[lo]); }
function at(arr, f){ const i=Math.floor(f), j=Math.min(n-1, i+1), w=f-i; const a=arr[i], b=arr[j]; if (a==null) return b; if (b==null) return a; return a+(b-a)*w; }
function interp(x, xs, ys){ if (x<=xs[0]) return ys[0]; if (x>=xs[xs.length-1]) return ys[ys.length-1]; let lo=0, hi=xs.length-1; while (hi-lo>1){ const m=(lo+hi)>>1; if (xs[m]<=x) lo=m; else hi=m; } return ys[lo]+(ys[hi]-ys[lo])*(x-xs[lo])/(xs[hi]-xs[lo]); }
function label(t, f){
  if (t >= D.endA && t >= D.endB) return D.endB < D.endA ? `B ${mmss(D.endA-D.endB)} más rápida` : `A ${mmss(D.endB-D.endA)} más rápida`;
  const g = at(D.gap, f), dd = at(D.dd, f);
  if (Math.abs(g) < 3 && Math.abs(dd) < 10) return 'Empatadas';
  return g > 0 ? `B ${mmss(g)} por delante` : `A ${mmss(g)} por delante`;
}

// ── mapa ──
let map = null, mkA = null, mkB = null, ready = false;
const err = document.getElementById('err');
function fail(msg){ err.style.display='block'; err.innerHTML = msg; }
try {
  if (typeof maplibregl === 'undefined') throw new Error('no se pudo cargar MapLibre (¿red que bloquea unpkg.com?)');
  const sources = {}, layers = [{id:'bg', type:'background', paint:{'background-color': C.surface2}}];
  if (D.base) { sources.base = {type:'raster', tiles:D.base.urls, tileSize:256, maxzoom:D.base.maxzoom, attribution:D.base.attr}; layers.push({id:'base', type:'raster', source:'base'}); }
  map = new maplibregl.Map({container:'map', style:{version:8, sources, layers}, bounds:D.bounds,
                            fitBoundsOptions:{padding:40}, pitch:55, bearing:-15, maxPitch:80, attributionControl:{compact:true}});
  map.addControl(new maplibregl.NavigationControl({visualizePitch:true}), 'top-right');
  map.on('load', () => {
    const dem = {type:'raster-dem', tiles:D.terrain.urls, tileSize:256, encoding:'terrarium', maxzoom:D.terrain.maxzoom, attribution:D.terrain.attr};
    map.addSource('dem', dem); map.addSource('demh', {...dem, attribution:undefined});
    map.addLayer({id:'hill', type:'hillshade', source:'demh', paint:{'hillshade-exaggeration': D.base ? 0.25 : 0.6, 'hillshade-shadow-color':'#000'}});
    map.setTerrain({source:'dem', exaggeration:1.5});
    const line = (id, coords) => map.addSource(id, {type:'geojson', data:{type:'Feature', geometry:{type:'LineString', coordinates:coords}}});
    line('trkA', D.trackA); line('trkB', D.trackB); line('doneA', []); line('doneB', []);
    map.addLayer({id:'trkA', type:'line', source:'trkA', paint:{'line-color':C.A, 'line-width':3, 'line-opacity':.55}});
    map.addLayer({id:'trkB', type:'line', source:'trkB', paint:{'line-color':C.B, 'line-width':3, 'line-opacity':.55}});
    map.addLayer({id:'doneA', type:'line', source:'doneA', paint:{'line-color':C.A, 'line-width':6}});
    map.addLayer({id:'doneB', type:'line', source:'doneB', paint:{'line-color':C.B, 'line-width':6}});
    const dot = (txt, bg, fg) => { const e=document.createElement('div'); e.className='dot'; e.style.background=bg; e.style.color=fg; e.textContent=txt; return e; };
    mkA = new maplibregl.Marker({element:dot('A', C.A, C.onA)}).setLngLat(D.trackA[0]).addTo(map);
    mkB = new maplibregl.Marker({element:dot('B', C.B, C.onB)}).setLngLat(D.trackB[0]).addTo(map);
    ready = true; render(tSim, true);
  });
} catch (e) { fail('No se puede mostrar el mapa 3D: ' + e.message + '.<br>Vuelve a la vista 2D.'); }

// ── perfil y D+ ──
function canvas(id){ const c=document.getElementById(id), r=window.devicePixelRatio||1, w=c.clientWidth, h=c.clientHeight;
  if (c.width !== Math.round(w*r)) { c.width=Math.round(w*r); c.height=Math.round(h*r); } const x=c.getContext('2d'); x.setTransform(r,0,0,r,0,0); x.clearRect(0,0,w,h); return [x,w,h]; }
const pX = D.profX, pY = D.profY, ymin = Math.min(...pY)-40, ymax = Math.max(...pY)+70, dpmax = Math.max(D.dpA[n-1], D.dpB[n-1], 1);
function drawProfile(posA, posB, f){
  const [x,w,h] = canvas('prof'), L=56, R=8, Tp=24, B=18;
  const sx = v => L + (w-L-R)*v/pX[pX.length-1], sy = v => Tp + (h-Tp-B)*(1-(v-ymin)/(ymax-ymin));
  const area = (upto, col, alpha) => { x.beginPath(); x.moveTo(sx(0), sy(ymin)); for (let i=0;i<pX.length && pX[i]<=upto;i++) x.lineTo(sx(pX[i]), sy(pY[i]));
    x.lineTo(sx(upto), sy(interp(upto,pX,pY))); x.lineTo(sx(upto), sy(ymin)); x.closePath(); x.globalAlpha=alpha; x.fillStyle=col; x.fill(); x.globalAlpha=1; };
  area(posA, C.A, .30); area(posB, C.B, .25);
  x.beginPath(); pX.forEach((v,i)=> i? x.lineTo(sx(v),sy(pY[i])) : x.moveTo(sx(v),sy(pY[i]))); x.strokeStyle=C.muted; x.lineWidth=1.4; x.stroke();
  x.fillStyle=C.muted; x.font='10px "IBM Plex Mono",monospace'; x.textAlign='right';
  [ymin+40, (ymin+ymax)/2, ymax-70].forEach(v=>x.fillText(fmt(v)+' m', L-4, sy(v)+3)); x.textAlign='center';
  for (let k=0;k<=pX[pX.length-1];k+=5) x.fillText(k+' km', sx(k), h-4);
  const dotp = (p, col, txt) => { const yy=sy(interp(p,pX,pY)); x.beginPath(); x.arc(sx(p), yy, 6, 0, 7); x.fillStyle=col; x.fill(); x.lineWidth=1.5; x.strokeStyle=C.bg; x.stroke();
    x.fillStyle=col; x.font='bold 11px sans-serif'; x.fillText(txt, sx(p), yy-10); };
  dotp(posB, C.B, 'B'); dotp(posA, C.A, 'A');
  x.textAlign='left'; x.font='11px "IBM Plex Sans",sans-serif'; x.fillStyle=C.ink;
  x.fillText(`A ${fmt(interp(posA,pX,pY))} m · D+ ${fmt(at(D.dpA,f))} m    |    B ${fmt(interp(posB,pX,pY))} m · D+ ${fmt(at(D.dpB,f))} m`, L, 14);
}
function drawDp(t, f){
  const [x,w,h] = canvas('dp'), L=56, R=8, Tp=8, B=18;
  const sx = v => L + (w-L-R)*v/tmax, sy = v => Tp + (h-Tp-B)*(1-v/dpmax);
  [[D.dpA, C.A], [D.dpB, C.B]].forEach(([arr, col]) => { x.beginPath(); arr.forEach((v,i)=> i? x.lineTo(sx(T[i]),sy(v)) : x.moveTo(sx(T[i]),sy(v))); x.strokeStyle=col; x.lineWidth=1.8; x.stroke(); });
  x.strokeStyle=C.line; x.setLineDash([3,3]); x.beginPath(); x.moveTo(sx(t), Tp); x.lineTo(sx(t), h-B); x.stroke(); x.setLineDash([]);
  [[at(D.dpA,f), C.A], [at(D.dpB,f), C.B]].forEach(([v,col]) => { x.beginPath(); x.arc(sx(t), sy(v), 5, 0, 7); x.fillStyle=col; x.fill(); });
  x.fillStyle=C.muted; x.font='10px "IBM Plex Mono",monospace'; x.textAlign='right'; x.fillText(fmt(dpmax)+' m', L-4, sy(dpmax)+8); x.fillText('0', L-4, sy(0));
  x.textAlign='center'; for (let hh=0; hh*3600<=tmax; hh++) x.fillText(hh+' h', sx(hh*3600), h-4);
  x.textAlign='left'; x.fillStyle=C.ink; x.font='11px "IBM Plex Sans",sans-serif'; x.fillText('D+ acumulado', L+6, Tp+10);
}

// ── reproducción ──
const rng = document.getElementById('rng'), tt = document.getElementById('tt'), lab = document.getElementById('lab'), cam = document.getElementById('cam');
rng.max = tmax; rng.step = 10;
let tSim = T[Math.min(D.k0, n-1)], speed = 0, last = null, lastHeavy = 0, lastCam = 0;
function render(t, heavy){
  const f = fidx(t), pa = at(D.posA, f), pb = at(D.posB, f);
  rng.value = t; tt.textContent = hms(t); lab.textContent = `${hms(t)} · ${label(t, f)}`;
  drawProfile(pa, pb, f); drawDp(t, f);
  if (!ready) return;
  const la=[at(D.lngA,f), at(D.latA,f)], lb=[at(D.lngB,f), at(D.latB,f)];
  if (la[0]!=null) mkA.setLngLat(la); if (lb[0]!=null) mkB.setLngLat(lb);
  const now = performance.now();
  if (heavy || now - lastHeavy > 120) {
    lastHeavy = now; const k = Math.floor(f);
    const path = (lng, lat) => { const out=[]; const st=Math.max(1, Math.floor(k/400)); for (let i=0;i<=k;i+=st) if (lng[i]!=null) out.push([lng[i],lat[i]]); return out; };
    map.getSource('doneA').setData({type:'Feature', geometry:{type:'LineString', coordinates:path(D.lngA, D.latA).concat([la])}});
    map.getSource('doneB').setData({type:'Feature', geometry:{type:'LineString', coordinates:path(D.lngB, D.latB).concat([lb])}});
  }
  if (cam.value !== 'fix' && (heavy || now - lastCam > 300)) { lastCam = now; map.easeTo({center: cam.value==='A' ? la : lb, duration: heavy ? 600 : 300}); }
}
function loop(ts){
  if (speed && last != null) { tSim = Math.min(tmax, tSim + (ts-last)/1000*speed); render(tSim, false); if (tSim >= tmax) setSpeed(0); }
  last = ts; requestAnimationFrame(loop);
}
function setSpeed(sp){ speed = sp; document.querySelectorAll('button[data-sp]').forEach(b => b.classList.toggle('on', Number(b.dataset.sp)===sp)); if (sp && tSim>=tmax) tSim = 0; }
document.querySelectorAll('button[data-sp]').forEach(b => b.onclick = () => setSpeed(Number(b.dataset.sp)));
document.getElementById('pause').onclick = () => setSpeed(0);
rng.oninput = () => { setSpeed(0); tSim = Number(rng.value); render(tSim, true); };
cam.onchange = () => { if (!ready) return; if (cam.value==='fix') map.fitBounds(D.bounds, {padding:40, pitch:55, bearing:-15, duration:800});
  else { map.easeTo({pitch:62, zoom:Math.max(map.getZoom(), 14), duration:800}); render(tSim, true); } };
document.getElementById('exa').onchange = e => { if (ready) map.setTerrain({source:'dem', exaggeration:Number(e.target.value)}); };
window.addEventListener('resize', () => render(tSim, true));
render(tSim, true); requestAnimationFrame(loop);
</script></body></html>"""



def in_spain(lat: float, lng: float) -> bool:
    return (35.8 <= lat <= 43.95 and -9.6 <= lng <= 4.6) or (27.5 <= lat <= 29.5 and -18.3 <= lng <= -13.3)


def base_tiles(fondo: str, lat: float, lng: float, light: bool) -> dict | None:
    """Capa raster de fondo según el selector (IGN en España; OpenTopoMap/Esri fuera)."""
    es = in_spain(lat, lng)
    if fondo == "Topográfico":
        return TILESETS["ign_mtn" if es else "otm"]
    if fondo == "Satélite":
        return TILESETS["pnoa" if es else "esri_img"]
    if fondo == "Callejero":
        return TILESETS["carto_light" if light else "carto_dark"]
    return None


@st.cache_data(ttl=3600, show_spinner=False, max_entries=20)
def race_cached(aid_a: str, aid_b: str, moving: bool, use_gps: bool, _a: pd.DataFrame, _b: pd.DataFrame) -> dict:
    return race_align(_a, _b, use_gps, moving)


def demo_streams(aid: str, km: float, dp: float, secs: float) -> list:
    """Streams sintéticos: las salidas DEMO_ROUTE comparten recorrido (3 cimas); el resto, recorrido propio."""
    rnd = random.Random(aid)
    same = aid.startswith("demoR")
    hr_off = {"demoRA": -6, "demoRB": 0, "demoRC": -2}.get(aid, 0)
    total = max(1000.0, km * 1000)
    h = max(30.0, dp / 3)
    lat_c, lng_c = (42.60, 0.52) if same else (41.5 + rnd.random(), 1.0 + rnd.random())
    t_, d_, out = 0, 0.0, {k: [] for k in ("time", "distance", "altitude", "heartrate", "velocity_smooth", "lat", "lng")}
    hr = 110.0
    stop_at = total * (0.36 if aid == "demoRA" else 0.5)
    stopped = 0
    mod = (lambda x_: 1.06 if x_ < 0.36 else 0.965) if aid == "demoRA" else (lambda x_: 1.0)  # noqa: E731
    shape = lambda g, x_=0.0: math.exp(-3.5 * abs(g + 0.05)) * mod(x_)  # noqa: E731  (velocidad según la pendiente, Tobler)
    grid_ = np.arange(0, total, 10.0)
    t_shape = float(np.sum(10.0 / np.array([shape(h * 3 * math.pi * math.sin(6 * math.pi * x_ / total) / total, x_ / total) for x_ in grid_])))
    c_v = t_shape / max(600.0, float(secs) or 600.0)          # escala para que el tiempo en movimiento cuadre
    while d_ < total:
        x = d_ / total
        alt = 1800 + h * (1 - math.cos(6 * math.pi * x)) / 2
        g = h * 3 * math.pi * math.sin(6 * math.pi * x) / total
        v = c_v * shape(g, x) * (1 + rnd.uniform(-.06, .06))
        if stopped < (420 if aid == "demoRA" else 180) and d_ >= stop_at:
            v, stopped = 0.0, stopped + 1
        hr += ((128 + 70 * max(-0.25, min(0.6, g * 2.5)) + hr_off) - hr) * 0.05 + rnd.uniform(-1, 1)
        for k, val in (("time", t_), ("distance", round(d_, 1)), ("altitude", round(alt + rnd.uniform(-1.5, 1.5), 1)),
                       ("heartrate", round(hr)), ("velocity_smooth", round(v, 2)),
                       ("lat", lat_c + 0.02 * math.sin(2 * math.pi * x) + rnd.uniform(-2e-5, 2e-5)),
                       ("lng", lng_c + 0.03 * (1 - math.cos(2 * math.pi * x)) + rnd.uniform(-2e-5, 2e-5))):
            out[k].append(val)
        t_ += 1
        d_ += v
    gaps = set(range(0, 25))                      # GPS aún sin señal al principio
    nul = lambda arr: [None if i in gaps else v for i, v in enumerate(arr)]  # noqa: E731
    return [dict(type="time", data=out["time"]), dict(type="distance", data=nul(out["distance"])),
            dict(type="altitude", data=nul(out["altitude"])), dict(type="heartrate", data=out["heartrate"]),
            dict(type="velocity_smooth", data=out["velocity_smooth"]),
            dict(type="latlng", data=nul(out["lat"]), data2=nul(out["lng"]))]


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
    ("D+", GOLD, fnum(T["dp"]), "m", [prev_line(P["dp"], 0, "m")] + ([dp_split_line(T)] if dp_split_line(T) else [])),
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


tab_temp, tab_cw, tab_lw, tab_fat, tab_sets, tab_long, tab_cmp, tab_cinta, tab_mat = st.tabs(
    ["Temporada", "Semana en curso", "Última semana", "Esfuerzo y fatiga", "Hoja por Sets", "Entrenamientos largos", "Comparar",
     "Cinta", "Material"])

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
    if df_y["dp_hike"].sum() > 0 or df_y["dp_cinta"].sum() > 0:
        days_r = pd.date_range(f"{year}-01-01", today if year == now_y else dt.date(year, 12, 31), freq="D")
        gr = df_y.groupby(df_y["ts"].dt.normalize())[["km_run", "dp_run"]].sum().reindex(days_r, fill_value=0).cumsum()
        fig.add_scatter(x=gr["km_run"], y=gr["dp_run"], mode="lines", name=f"{year} solo carrera",
                        line=dict(color=GOLD, width=1.6, dash="dot"), opacity=.8,
                        hovertemplate="%{x:.0f} km · %{y:.0f} m<extra>solo carrera</extra>")
        fig.data[-2].name = f"{year} con caminata/cinta"
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
        m = d.groupby(d["ts"].dt.month)[["out_dp", "out_km", "ukm", "cinta_km", "gim_min", "dp_run", "dp_hike", "dp_cinta"]].sum().reindex(range(1, 13), fill_value=0)
        m["ultra"] = np.where(m["ukm"] > 0, 1.7 * m["out_dp"] / m["ukm"].replace(0, np.nan), 0)
        prev = m["out_dp"].shift(1)
        m["incr"] = np.where((m["out_dp"] > 0) & (m.index > 1), (m["out_dp"] - prev) / m["out_dp"].replace(0, np.nan), 0)
        return m.fillna(0)


    My, Mp = monthly(df_y), monthly(df_p)
    c1, c2 = st.columns([3, 2])
    for col, key_, title, color, dec in [(c1, "out_dp", "D+ por mes", GOLD, 0), (c2, "ultra", "Ultra Ind por mes", RED, 1)]:
        with col:
            st.subheader(title)
            if key_ == "out_dp":
                # Total del año (respeta los interruptores de caminata/cinta, igual que las tarjetas)
                tot_y = float(My["out_dp"].sum())
                if year == now_y and len(df_p):
                    try:
                        cut = pd.Timestamp(today.replace(year=year - 1)) + pd.Timedelta(days=1)
                    except ValueError:                     # 29 de febrero
                        cut = pd.Timestamp(dt.date(year - 1, 3, 1))
                    tot_p, lab_p = float(df_p.loc[df_p["ts"] < cut, "out_dp"].sum()), f"{year - 1} a misma fecha"
                else:
                    tot_p, lab_p = float(df_p["out_dp"].sum()) if len(df_p) else 0.0, str(year - 1)
                diff_txt = ""
                if tot_p > 0:
                    dlt = (tot_y - tot_p) / tot_p * 100
                    diff_txt = f' <span style="color:{GREEN if dlt >= 0 else RED}">{dlt:+.0f} %</span>'
                st.markdown(f'<div class="note" style="margin-top:-.4rem">Total {year}: <b style="color:{GOLD}">{fnum(tot_y)} m</b>'
                            + (f' · {lab_p}: {fnum(tot_p)} m{diff_txt}' if len(df_p) else "") + '</div>', unsafe_allow_html=True)
            f2 = go.Figure()
            xm = MES if key_ == "out_dp" else [m[0] for m in MES]
            split_m = key_ == "out_dp" and (My["dp_hike"].sum() > 0 or My["dp_cinta"].sum() > 0)
            if split_m:
                cd_m = np.stack([MES, [fnum(v) for v in My["out_dp"]]], axis=-1)
                for k_, lab_, c_ in DP_SRC:
                    if My[k_].sum() > 0:
                        f2.add_bar(x=list(range(12)), y=My[k_], name=f"{lab_} {year}", marker_color=src_color(c_), customdata=cd_m,
                                   hovertemplate=f"%{{customdata[0]}} · {lab_}: %{{y:,.0f}} m<br>Total mes: %{{customdata[1]}} m<extra></extra>")
                f2.update_layout(barmode="stack")
            else:
                f2.add_bar(x=list(range(12)), y=My[key_], name=str(year), marker_color=color, customdata=MES, hovertemplate=f"%{{customdata}}: %{{y:.{dec}f}}<extra>{year}</extra>")
            if key_ == "out_dp":
                lbl = My["out_dp"].where(My["out_dp"] > 0)
                f2.add_scatter(x=list(range(12)), y=lbl, mode="text", text=[fnum(v) if v > 0 else "" for v in My["out_dp"]],
                               textposition="top center", textfont=dict(color=INK, size=10, family="IBM Plex Sans, system-ui, sans-serif"),
                               showlegend=False, hoverinfo="skip", cliponaxis=False)
            if len(df_p):
                f2.add_scatter(x=list(range(12)), y=Mp[key_].where(Mp[key_] > 0), mode="markers", name=f"Total {year - 1}" if split_m else str(year - 1),
                               marker=dict(symbol="line-ew", size=26, line=dict(width=3, color=PREV)),
                               customdata=MES, hovertemplate=f"%{{customdata}}: %{{y:.{dec}f}}<extra>{year - 1}</extra>")
            f2.update_xaxes(tickvals=list(range(12)), ticktext=xm, tickangle=0)
            if key_ == "out_dp":
                ymax = float(max(My["out_dp"].max(), Mp["out_dp"].max() if len(df_p) else 0, 1))
                f2.update_yaxes(range=[0, ymax * 1.15])
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
        ] + ([dp_split_line(CW)] if k == "dp" and dp_split_line(CW) else []))


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
        if tm == "dp" and (CW["dp_hike"] > 0 or CW["dp_cinta"] > 0):
            for k_, lab_, c_ in DP_SRC:
                ys_ = list(np.cumsum([span_tot(cur_mon + dt.timedelta(days=i), cur_mon + dt.timedelta(days=i))[k_] for i in range(dow + 1)]))
                if ys_ and ys_[-1] > 0:
                    f6.add_scatter(x=DIAS[: dow + 1], y=ys_, name=f"{lab_} (esta semana)", mode="lines", stackgroup="cw",
                                   line=dict(color=src_color(c_), width=1), fillcolor=rgba(src_color(c_), .35),
                                   hovertemplate=f"%{{x}} · {lab_}: %{{y:.0f}} m<extra></extra>")
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
    cards([(lab, col, fnum(LW[k], d), u, [delta_html(LW[k], PW[k], "sem. anterior"), delta_html(LW[k], AVG[k], "media 8 sem")]
            + ([dp_split_line(LW)] if k == "dp" and dp_split_line(LW) else []))
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
        split_w = metric == "dp" and any(w["dp_hike"] > 0 or w["dp_cinta"] > 0 for w in W)
        if split_w:
            for k_, lab_, c_ in DP_SRC:
                ys_ = [w[k_] for w in W]
                if sum(ys_) > 0:
                    f3.add_bar(x=xs, y=ys_, name=lab_, marker=dict(color=src_color(c_), opacity=opac),
                               hovertemplate=f"Semana %{{x}} · {lab_}: %{{y:.0f}} m<extra></extra>")
            f3.update_layout(barmode="stack")
            f3.add_annotation(x=xs[11], y=vals[11], text=fnum(vals[11]), showarrow=False, yshift=10, font=dict(color=INK))
        else:
            f3.add_bar(x=xs, y=vals, marker=dict(color=colr, opacity=opac, line=dict(color=colr, width=[0] * 12 + [1.5])),
                       text=[fnum(v, dec) if i == 11 else "" for i, v in enumerate(vals)], textposition="outside",
                       textfont=dict(color=INK), hovertemplate=f"Semana %{{x}}: %{{y:.{dec}f}} {unit}<extra></extra>", showlegend=False)
        if AVG[metric] > 0:
            f3.add_scatter(x=xs[3:12], y=[AVG[metric]] * 9, mode="lines", line=dict(color=INK, dash="dash", width=1.4),
                           name=f"media 8 sem: {fnum(AVG[metric], dec)}", hoverinfo="skip")
        f3.update_xaxes(ticktext=xs[:12] + [f"{xs[12]}<br>en curso"], tickvals=xs, tickangle=0, tickfont=dict(size=10))
        plot_layout(f3, 290)
        if split_w:
            f3.update_layout(legend=dict(orientation="h", y=-0.22, x=0), margin=dict(t=20))
        st.plotly_chart(f3, width="stretch", theme=None)
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
        # Paginación
        PER_PAGE = 20
        n_pages = max(1, math.ceil(len(tm_) / PER_PAGE))
        sig = f"{periodo}|{len(tm_)}"
        if st.session_state.get("cinta_sig") != sig:          # cambio de periodo → volver a la primera página
            st.session_state["cinta_sig"] = sig
            st.session_state["cinta_page"] = 1
        page = min(max(1, int(st.session_state.get("cinta_page", 1))), n_pages)
        if n_pages > 1:
            pg1, pg2, pg3, _ = st.columns([1, 1.6, 1, 3], vertical_alignment="center")
            with pg1:
                if st.button("◀ Anterior", disabled=page <= 1, width="stretch", key="cinta_prev"):
                    st.session_state["cinta_page"] = page - 1
                    st.rerun()
            with pg2:
                st.markdown(f'<div class="note" style="text-align:center">Página <b style="color:{INK}">{page}</b> de {n_pages} · '
                            f'{len(tm_)} sesiones</div>', unsafe_allow_html=True)
            with pg3:
                if st.button("Siguiente ▶", disabled=page >= n_pages, width="stretch", key="cinta_next"):
                    st.session_state["cinta_page"] = page + 1
                    st.rerun()
        rows_c = tm_.iloc[(page - 1) * PER_PAGE: page * PER_PAGE]
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
                st.caption(("Guarda antes de cambiar de página: los cambios sin guardar se pierden. " if n_pages > 1 else "")
                           + "Escribe la pendiente media y pulsa Guardar; el D+ se recalcula al guardar. Antes del primer guardado, crea en "
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

with tab_mat:
    # ─────────────────────────── Material ───────────────────────────
    st.subheader("Material · zapatillas")
    if st.session_state.get("mat_msg"):
        st.success(st.session_state.pop("mat_msg"))

    # Maestro de zapatillas (intervals.icu, o memoria de la sesión en DEMO)
    gear_err = None
    if demo:
        if "demo_gear" not in st.session_state:
            st.session_state["demo_gear"] = [{**g, "reminders": [dict(r) for r in g["reminders"]]} for g in _DEMO_GEAR]
        gear_raw = st.session_state["demo_gear"]
    else:
        try:
            gear_raw = fetch_gear(athlete, key)
        except Exception as e:  # noqa: BLE001
            gear_raw, gear_err = [], e
    shoes = [g for g in gear_raw if (g.get("type") or "") == "Shoes"]
    if gear_err:
        st.error(f"No se pudo leer el material de intervals.icu: {gear_err}")

    # Histórico completo de actividades (desde la compra más antigua o 2020)
    buy_years = [d.year for d in (iso_date(g.get("purchased")) for g in shoes) if d]
    y0 = max(2010, min([2020] + buy_years))
    hist_rows = []
    with st.spinner("Leyendo el histórico de actividades…"):
        for y in range(y0, now_y + 1):
            if y in raw:
                hist_rows += raw[y]
                continue
            try:
                hist_rows += demo_year(y) if demo else fetch_year(athlete, key, y)
            except Exception as e:  # noqa: BLE001
                st.warning(f"No se pudieron leer las actividades de {y}: {e}")
    hist = to_frame(hist_rows, True, True, st.session_state.get("incline_overrides"))
    ov_g = st.session_state.get("gear_overrides", {})
    if len(hist) and ov_g:   # asignaciones guardadas en esta sesión
        m_ = hist["id"].isin(list(ov_g))
        hist.loc[m_, "gear_id"] = hist.loc[m_, "id"].map(ov_g)
    shoe_hist = hist[hist["sport"].isin(list(SHOE_SPORTS))] if len(hist) else hist

    # Tabla base por zapatilla (km de por vida = actividades asignadas + km previos)
    SHOE_COLORS = [GOLD, GLACIER, ORANGE, GREEN, VIOLET, TEAL, RED, INK, PREV, MUTED]
    base_rows = []
    for g in shoes:
        nt = parse_notes(g.get("notes"))
        a_ = hist[hist["gear_id"] == g["id"]] if len(hist) else hist
        rem, lim = km_limit(g)
        km_all = float(a_["km"].sum()) + nt["km_previos"]
        base_rows.append(dict(
            id=g["id"], name=g.get("name") or "", marca=nt["marca"], modelo=nt["modelo"] or (g.get("name") or ""),
            foto=nt["foto"], libre=nt["libre"], km_prev=nt["km_previos"], km=km_all, dp=float(a_["dp"].sum()),
            h=float(a_["secs"].sum()) / 3600, n=len(a_), last=a_["date"].max() if len(a_) else None,
            compra=iso_date(g.get("purchased")), retirada=iso_date(g.get("retired")), lim=lim, rem=rem,
            pct=(km_all / lim * 100) if lim else None))
    SB = pd.DataFrame(base_rows)
    if len(SB):
        SB["ret"] = SB["retirada"].notna()
        SB["_last"] = pd.to_datetime(SB["last"])
        SB = SB.sort_values(["ret", "_last"], ascending=[True, False], na_position="last").reset_index(drop=True)
        SB["color"] = [SHOE_COLORS[i % len(SHOE_COLORS)] for i in range(len(SB))]
    shoe_name = dict(zip(SB["id"], SB["name"])) if len(SB) else {}
    shoe_color = dict(zip(SB["id"], SB["color"])) if len(SB) else {}

    def nn(v):
        """None si el valor está vacío (None/NaN/NaT)."""
        return None if v is None or (not isinstance(v, (str, dt.date)) and pd.isna(v)) else v

    def pct_color(p):
        p = nn(p)
        return MUTED if p is None else (RED if p >= 100 else ORANGE if p >= 80 else GREEN)

    def photo_html(url: str, badge: str = "", badge_c: str = "") -> str:
        b_ = f'<span class="st" style="--c:{badge_c};--o:{on(badge_c)}">{badge}</span>' if badge else ""
        if url:  # imagen como fondo: si no carga, queda visible el icono de detrás
            u = _html.escape(url, quote=True).replace("'", "%27").replace("(", "%28").replace(")", "%29")
            return f'<div class="ph no"><span>👟</span><div class="im" style="background-image:url(\'{u}\')"></div>{b_}</div>'
        return f'<div class="ph no">👟{b_}</div>'

    vista = st.segmented_control("Vista material", ["Resumen", "Zapatillas", "Asignar a actividades"], default="Resumen",
                                 key="mat_view", label_visibility="collapsed") or "Resumen"

    # ═══════════════════════════ Resumen y análisis ═══════════════════════════
    if vista == "Resumen":
        if not len(SB):
            st.info("No hay zapatillas en intervals.icu. Crea la primera en «Zapatillas» o ejecuta migrar_material.py.")
        else:
            PERM = ["90 días", "12 meses", f"Temporada {year}", "Todo", "Personalizado"]
            per_m = st.segmented_control("Periodo material", PERM, default="Todo", key="mt_per",
                                         label_visibility="collapsed") or "Todo"
            d_min_m = shoe_hist["date"].min() if len(shoe_hist) else today
            if per_m == "90 días":
                m_from, m_to = today - dt.timedelta(days=89), today
            elif per_m == "12 meses":
                m_from, m_to = today - dt.timedelta(days=364), today
            elif per_m.startswith("Temporada"):
                m_from, m_to = dt.date(year, 1, 1), min(dt.date(year, 12, 31), today)
            elif per_m == "Personalizado":
                dc1, dc2, _ = st.columns([1, 1, 2])
                with dc1:
                    m_from = st.date_input("Desde", value=max(d_min_m, today - dt.timedelta(days=180)), min_value=d_min_m,
                                           max_value=today, format="DD/MM/YYYY", key="mt_from")
                with dc2:
                    m_to = st.date_input("Hasta", value=today, min_value=d_min_m, max_value=today, format="DD/MM/YYYY", key="mt_to")
                if m_from > m_to:
                    m_from, m_to = m_to, m_from
            else:
                m_from, m_to = d_min_m, today
            fc1, fc2 = st.columns([1, 2])
            with fc1:
                est = st.pills("Estado", ["Activas", "Retiradas"], selection_mode="multi", default=["Activas"], key="mt_est") or []
            with fc2:
                tipos_m = st.pills("Tipo de actividad", ["Carrera", "Trail", "Cinta", "Caminata"], selection_mode="multi",
                                   default=["Carrera", "Trail", "Cinta", "Caminata"], key="mt_tipo") or []
            sports_sel = [s_ for s_, t_ in SHOE_SPORTS.items() if t_ in tipos_m]
            SBf = SB[(SB["ret"] & ("Retiradas" in est)) | (~SB["ret"] & ("Activas" in est))]
            per_txt_m = f"{m_from.strftime('%d/%m/%y')} – {m_to.strftime('%d/%m/%y')}"
            act_p = shoe_hist[(shoe_hist["date"] >= m_from) & (shoe_hist["date"] <= m_to) & shoe_hist["sport"].isin(sports_sel)]
            act_ps = act_p[act_p["gear_id"].isin(list(SBf["id"]))]

            # Indicadores
            n_act, n_ret = int((~SB["ret"]).sum()), int(SB["ret"].sum())
            alerts = SB[~SB["ret"] & SB["pct"].notna() & (SB["pct"] >= 80)]
            con_zap = act_p["gear_id"].isin(list(shoe_name)).mean() * 100 if len(act_p) else 0
            cards([
                ("Zapatillas activas", GOLD, fnum(n_act), "", [f"{n_ret} retiradas"]),
                ("Km con zapatilla", INK, fnum(act_ps["km"].sum(), 1), "km", [per_txt_m]),
                ("Actividades", GLACIER, fnum(len(act_ps)), "", [f"{fnum(con_zap)} % de las del periodo tienen zapatilla"]),
                ("Avisos de cambio", RED if (alerts["pct"] >= 100).any() else ORANGE if len(alerts) else GREEN, fnum(len(alerts)), "",
                 ["≥ 80 % del límite de km" if len(alerts) else "ninguna cerca del límite"]),
            ])
            for _, r_ in alerts.sort_values("pct", ascending=False).iterrows():
                c_ = pct_color(r_["pct"])
                txt = "ha superado su límite" if r_["pct"] >= 100 else "está cerca de su límite"
                st.markdown(f'<div class="reading" style="--c:{c_}"><b>{_html.escape(r_["name"])}</b> {txt}: '
                            f'{fnum(r_["km"])} de {fnum(r_["lim"])} km ({fnum(r_["pct"])} %).</div>', unsafe_allow_html=True)

            # Galería
            cards_html = ['<div class="shoes">']
            for _, r_ in SBf.iterrows():
                badge, bc = ("Retirada", MUTED) if r_["ret"] else ("", "")
                bar = ""
                if nn(r_["lim"]):
                    pc = r_["pct"]
                    bar = (f'<div class="bar"><span style="width:{min(100, pc):.0f}%;--c:{pct_color(pc)}"></span></div>'
                           f'<div class="ln">{fnum(pc)} % de {fnum(r_["lim"])} km</div>')
                last_txt = r_["last"].strftime("%d/%m/%y") if nn(r_["last"]) else "—"
                cards_html.append(
                    f'<div class="shoe{" ret" if r_["ret"] else ""}">{photo_html(r_["foto"], badge, bc)}'
                    f'<div class="br"><span style="color:{r_["color"]}">●</span> {_html.escape(r_["marca"] or "")}</div>'
                    f'<div class="nm">{_html.escape(r_["modelo"])}</div>'
                    f'<div class="km">{fnum(r_["km"])}<small>km</small></div>'
                    f'<div class="ln">{r_["n"]} act. · {fnum(r_["h"])} h · {fnum(r_["dp"])} m D+</div>'
                    f'<div class="ln">Compra {r_["compra"].year if nn(r_["compra"]) else "—"} · último uso {last_txt}</div>{bar}</div>')
            cards_html.append("</div>")
            if len(SBf):
                st.markdown("".join(cards_html), unsafe_allow_html=True)
            else:
                st.info("No hay zapatillas con ese estado.")

            if not len(act_ps):
                st.info(f"No hay actividades con zapatilla entre {per_txt_m} para los filtros elegidos.")
            else:
                # Tabla resumen del periodo
                st.subheader("Uso en el periodo")
                TIP = ["Carrera", "Trail", "Cinta", "Caminata"]
                g_ = act_ps.assign(tipo=act_ps["sport"].map(SHOE_SPORTS))
                runs_ = g_[g_["sport"].isin(["Run", "TrailRun", "VirtualRun"])]
                tb = pd.DataFrame({
                    "Zapatilla": [shoe_name[i] for i in SBf["id"]],
                    "Km": [g_.loc[g_["gear_id"] == i, "km"].sum() for i in SBf["id"]],
                    "D+": [g_.loc[g_["gear_id"] == i, "dp"].sum() for i in SBf["id"]],
                    "Horas": [g_.loc[g_["gear_id"] == i, "secs"].sum() / 3600 for i in SBf["id"]],
                    "Act.": [int((g_["gear_id"] == i).sum()) for i in SBf["id"]],
                    **{t_: [g_.loc[(g_["gear_id"] == i) & (g_["tipo"] == t_), "km"].sum() for i in SBf["id"]] for t_ in TIP},
                    "Ritmo": [(runs_.loc[runs_["gear_id"] == i, "secs"].sum() / runs_.loc[runs_["gear_id"] == i, "km"].sum())
                              if runs_.loc[runs_["gear_id"] == i, "km"].sum() > 0 else np.nan for i in SBf["id"]],
                    "% límite": list(SBf["pct"]),
                })
                tb = tb[tb["Act."] > 0].sort_values("Km", ascending=False)
                tot = pd.DataFrame([{"Zapatilla": "Total", "Km": tb["Km"].sum(), "D+": tb["D+"].sum(), "Horas": tb["Horas"].sum(),
                                     "Act.": tb["Act."].sum(), **{t_: tb[t_].sum() for t_ in TIP},
                                     "Ritmo": np.nan, "% límite": np.nan}])
                tb_all = pd.concat([tb, tot], ignore_index=True)
                num_ = lambda d, u="": (lambda v: "" if pd.isna(v) else f"{fnum(v, d)}{u}")  # noqa: E731
                pct_f = lambda v: ("" if pd.isna(v) else f'<span style="color:{pct_color(v)}">{fnum(v)} %</span>')  # noqa: E731
                pace_f2 = lambda p: f"{int(p // 60)}:{int(round(p % 60)) % 60:02d}" if pd.notna(p) and p > 0 else ""  # noqa: E731
                html_table(tb_all, left={"Zapatilla"}, total_last=True, group_start={"Carrera"},
                           groups=[("", 5, ""), ("Km por tipo", 4, "g"), ("", 2, "")],
                           fmt={"Km": num_(1), "D+": num_(0), "Horas": num_(1), "Act.": num_(0), **{t_: num_(1) for t_ in TIP},
                                "Ritmo": pace_f2, "% límite": pct_f},
                           heat={"Km": (float(max(1, tb["Km"].max())), rgb(GOLD))})

                # km acumulados por zapatilla (vida completa, con km previos), recortado al periodo
                st.subheader("Km acumulados por zapatilla")
                f_cum = go.Figure()
                for _, r_ in SBf.iterrows():
                    a_ = shoe_hist[shoe_hist["gear_id"] == r_["id"]].sort_values("ts")
                    if not len(a_):
                        continue
                    cum = a_.groupby("date")["km"].sum().cumsum() + r_["km_prev"]
                    xs = [pd.Timestamp(d) for d in cum.index]
                    f_cum.add_scatter(x=xs, y=cum.values, mode="lines", name=r_["name"], line=dict(color=r_["color"], width=2, shape="hv"),
                                      hovertemplate="%{x|%d/%m/%y} · %{y:,.0f} km<extra>" + _html.escape(r_["name"]) + "</extra>")
                    if nn(r_["lim"]):
                        f_cum.add_scatter(x=[xs[0], pd.Timestamp(today)], y=[r_["lim"], r_["lim"]], mode="lines", showlegend=False,
                                          line=dict(color=r_["color"], width=1, dash="dash"), opacity=.6, hoverinfo="skip")
                f_cum.update_xaxes(range=[pd.Timestamp(m_from) - pd.Timedelta(days=3), pd.Timestamp(m_to) + pd.Timedelta(days=3)])
                f_cum.update_yaxes(ticksuffix=" km")
                st.markdown('<span class="note">Incluye los km previos de cada zapatilla. La línea discontinua es su límite de km.</span>',
                            unsafe_allow_html=True)
                st.plotly_chart(plot_layout(f_cum, 330), width="stretch", theme=None)

                # km por mes y zapatilla
                st.subheader("Km por mes y zapatilla")
                g_["mes"] = g_["ts"].dt.to_period("M").dt.to_timestamp()
                pm = g_.groupby(["mes", "gear_id"])["km"].sum().unstack(fill_value=0)
                f_m = go.Figure()
                for gid in [i for i in SBf["id"] if i in pm.columns]:
                    f_m.add_bar(x=pm.index, y=pm[gid], name=shoe_name[gid], marker_color=shoe_color[gid],
                                hovertemplate="%{x|%b %Y} · %{y:.0f} km<extra>" + _html.escape(shoe_name[gid]) + "</extra>")
                f_m.update_layout(barmode="stack")
                f_m.update_yaxes(ticksuffix=" km")
                st.plotly_chart(plot_layout(f_m, 300), width="stretch", theme=None)

                cA_, cB_ = st.columns(2)
                order_ = list(tb["Zapatilla"])[::-1]
                with cA_:
                    st.subheader("Reparto por tipo de actividad")
                    TCOL = {"Carrera": INK, "Trail": GOLD, "Cinta": GLACIER, "Caminata": ORANGE}
                    f_t = go.Figure()
                    for t_ in TIP:
                        f_t.add_bar(y=order_, x=[float(tb.loc[tb["Zapatilla"] == z, t_].iloc[0]) for z in order_], name=t_, orientation="h",
                                    marker_color=TCOL[t_], hovertemplate="%{y} · " + t_ + ": %{x:.0f} km<extra></extra>")
                    f_t.update_xaxes(ticksuffix=" km")
                    plot_layout(f_t, max(260, 34 * len(order_) + 110))
                    f_t.update_layout(barmode="stack", margin=dict(t=44), legend=dict(y=1.0, yanchor="bottom"))
                    st.plotly_chart(f_t, width="stretch", theme=None)
                with cB_:
                    st.subheader("D+ por zapatilla")
                    id_by_name = {v: k for k, v in shoe_name.items()}
                    f_d = go.Figure()
                    f_d.add_bar(y=order_, x=[float(tb.loc[tb["Zapatilla"] == z, "D+"].iloc[0]) for z in order_], orientation="h",
                                marker_color=[shoe_color[id_by_name[z]] for z in order_],
                                text=[fnum(float(tb.loc[tb["Zapatilla"] == z, "D+"].iloc[0])) for z in order_], textposition="outside",
                                textfont=dict(color=INK, size=11), cliponaxis=False, hovertemplate="%{y} · %{x:,.0f} m<extra></extra>")
                    dmax_ = float(tb["D+"].max()) if len(tb) else 1.0
                    f_d.update_xaxes(ticksuffix=" m", range=[0, max(1.0, dmax_) * 1.22])
                    plot_layout(f_d, max(260, 34 * len(order_) + 110), legend=False)
                    f_d.update_layout(margin=dict(t=44))
                    st.plotly_chart(f_d, width="stretch", theme=None)

    # ═══════════════════════════ Alta y edición ═══════════════════════════
    elif vista == "Zapatillas":
        NEW = "__new__"
        ids_ = [NEW] + list(SB["id"]) if len(SB) else [NEW]
        lab_ = {NEW: "➕ Nueva zapatilla", **{r_["id"]: r_["name"] + (" · retirada" if r_["ret"] else "") for _, r_ in SB.iterrows()}}
        if st.session_state.get("mt_sel_next") in ids_:      # tras guardar, mostrar la zapatilla guardada
            st.session_state["mt_sel"] = st.session_state.pop("mt_sel_next")
        gsel = st.selectbox("Zapatilla", ids_, format_func=lambda i: lab_.get(i, i), key="mt_sel",
                            index=1 if len(ids_) > 1 else 0)
        cur = {k: nn(v) for k, v in SB[SB["id"] == gsel].iloc[0].to_dict().items()} if gsel != NEW else {}
        k_ = f"mf_{gsel}_"
        e1, e2 = st.columns(2)
        with e1:
            f_marca = st.text_input("Marca", value=cur.get("marca", ""), key=k_ + "marca")
            f_modelo = st.text_input("Modelo", value=cur.get("modelo", ""), key=k_ + "modelo")
            f_compra = st.date_input("Fecha de compra", value=cur.get("compra"), min_value=dt.date(2010, 1, 1), max_value=today,
                                     format="DD/MM/YYYY", key=k_ + "compra")
            f_prev = st.number_input("Km previos", min_value=0.0, step=10.0, format="%.1f", value=float(cur.get("km_prev") or 0.0),
                                     help="Km hechos antes de tener las actividades en intervals.icu. Se suman a los km de la zapatilla.",
                                     key=k_ + "prev")
        with e2:
            f_lim = st.number_input("Límite de km (aviso de cambio)", min_value=0.0, step=50.0, format="%.0f",
                                    value=float(cur["lim"]) if cur.get("lim") else None, placeholder="sin aviso", key=k_ + "lim")
            f_ret = st.toggle("Retirada", value=bool(cur.get("ret")), key=k_ + "ret")
            f_retd = (st.date_input("Fecha de retirada", value=cur.get("retirada") or today, min_value=dt.date(2010, 1, 1),
                                    max_value=today, format="DD/MM/YYYY", key=k_ + "retd") if f_ret else None)
            f_libre = st.text_area("Notas", value=cur.get("libre", ""), height=90, key=k_ + "libre")
        ph1, ph2 = st.columns([3, 1], vertical_alignment="bottom")
        with ph1:
            f_foto = st.text_input("URL de la foto", value=cur.get("foto", ""), placeholder="https://…/zapatilla.jpg", key=k_ + "foto")
        with ph2:
            st.link_button("Buscar foto", f"https://www.google.com/search?tbm=isch&q={quote_plus((f_marca + ' ' + f_modelo + ' zapatilla').strip())}",
                           width="stretch")
        pv1, pv2 = st.columns([1, 3])
        with pv1:
            st.markdown(f'<div class="shoe" style="max-width:190px">{photo_html(f_foto.strip())}</div>', unsafe_allow_html=True)
        with pv2:
            if f_foto.strip():
                if not f_foto.strip().startswith("http"):
                    st.warning("La URL debe empezar por http:// o https://")
                elif not image_ok(f_foto.strip()):
                    st.warning("No he podido comprobar que la URL sea una imagen. Puedes guardarla igualmente; si no carga, se mostrará el icono.")
                else:
                    st.caption("✓ La URL devuelve una imagen.")
            if cur:
                st.caption(f"{cur['n']} actividades · {fnum(cur['km'])} km en total" + (f" (incluye {fnum(cur['km_prev'])} km previos)" if cur["km_prev"] else ""))

        if st.button("Revisar cambios", type="primary", key="mt_review"):
            if not f_marca.strip() or not f_modelo.strip():
                st.error("La marca y el modelo son obligatorios.")
            else:
                st.session_state["mat_pending"] = dict(
                    kind="gear", gid=None if gsel == NEW else gsel, name=f"{f_marca.strip()} {f_modelo.strip()}",
                    purchased=f_compra.isoformat() if f_compra else None, retired=f_retd.isoformat() if f_retd else None,
                    notes=build_notes(f_marca, f_modelo, f_foto, float(f_prev or 0), f_libre),
                    lim=float(f_lim) if f_lim else None)
        pend = st.session_state.get("mat_pending")
        if pend and pend.get("kind") == "gear" and (pend["gid"] or NEW) == gsel:
            with st.container(border=True):
                st.markdown(f"**{'Crear' if not pend['gid'] else 'Actualizar'} en intervals.icu:** {_html.escape(pend['name'])}")
                st.markdown(f"- Compra: {pend['purchased'] or '—'} · Retirada: {pend['retired'] or 'no'}\n"
                            f"- Límite de km: {fnum(pend['lim']) + ' km' if pend['lim'] else 'sin aviso'}\n"
                            f"- Notas:\n```\n{pend['notes']}\n```")
                b1, b2, _ = st.columns([1.2, 1, 3])
                if b1.button("Confirmar y guardar", type="primary", key="mt_conf"):
                    body = {"type": "Shoes", "name": pend["name"], "notes": pend["notes"],
                            "purchased": f"{pend['purchased']}T00:00:00" if pend["purchased"] else None,
                            "retired": f"{pend['retired']}T00:00:00" if pend["retired"] else None}
                    try:
                        if demo:
                            store = st.session_state["demo_gear"]
                            if pend["gid"]:
                                g0 = next(g for g in store if g["id"] == pend["gid"])
                            else:
                                g0 = {"id": f"gd{len(store) + 1}_{random.randint(100, 999)}", "reminders": []}
                                store.append(g0)
                            g0.update(body)
                            rem0 = next((r for r in g0["reminders"] if (r.get("distance") or 0) > 0), None)
                            if pend["lim"]:
                                if rem0:
                                    rem0["distance"] = pend["lim"] * 1000
                                else:
                                    g0["reminders"].append(dict(id=random.randint(1000, 9999), name="Límite de km", distance=pend["lim"] * 1000))
                            elif rem0:
                                g0["reminders"].remove(rem0)
                            gid_saved = g0["id"]
                        else:
                            if pend["gid"]:
                                g0 = next(g for g in shoes if g["id"] == pend["gid"])
                                g_new = icu_write("PUT", f"/athlete/{athlete}/gear/{pend['gid']}", {**g0, **body}) or g0
                            else:
                                g0 = {}
                                g_new = icu_write("POST", f"/athlete/{athlete}/gear", body)
                            gid_saved = (g_new or {}).get("id") or pend["gid"]
                            rem0, _l = km_limit(g0)
                            if pend["lim"]:
                                if rem0:
                                    icu_write("PUT", f"/athlete/{athlete}/gear/{gid_saved}/reminder/{rem0['id']}",
                                              {**rem0, "distance": pend["lim"] * 1000})
                                else:
                                    icu_write("POST", f"/athlete/{athlete}/gear/{gid_saved}/reminder",
                                              {"name": "Límite de km", "distance": pend["lim"] * 1000})
                            elif rem0:
                                icu_write("DELETE", f"/athlete/{athlete}/gear/{gid_saved}/reminder/{rem0['id']}")
                            icu_write("GET", f"/athlete/{athlete}/gear/{gid_saved}/calc")
                            st.cache_data.clear()
                        st.session_state.pop("mat_pending", None)
                        st.session_state["mt_sel_next"] = gid_saved
                        st.session_state["mat_msg"] = f"Guardada «{pend['name']}» en intervals.icu." if not demo else f"Guardada «{pend['name']}» (DEMO)."
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"No se pudo guardar: {e}")
                if b2.button("Cancelar", key="mt_cancel"):
                    st.session_state.pop("mat_pending", None)
                    st.rerun()

    # ═══════════════════════════ Asignar a actividades ═══════════════════════════
    else:
        if not len(SB):
            st.info("Primero crea alguna zapatilla en «Zapatillas».")
        else:
            a1, a2, a3 = st.columns([2.1, 2, 1], vertical_alignment="bottom")
            with a1:
                per_a = st.segmented_control("Periodo", ["30 días", "90 días", f"Año {year}", "Todo"], default="90 días",
                                             key="mt_as_per") or "90 días"
            with a2:
                tip_a = st.pills("Tipo", ["Carrera", "Trail", "Cinta", "Caminata"], selection_mode="multi",
                                 default=["Carrera", "Trail", "Cinta", "Caminata"], key="mt_as_tipo") or []
            with a3:
                solo_sin = st.toggle("Solo sin zapatilla", value=False, key="mt_as_none")
            la = shoe_hist[shoe_hist["sport"].isin([s_ for s_, t_ in SHOE_SPORTS.items() if t_ in tip_a])]
            if per_a == "30 días":
                la = la[la["date"] >= today - dt.timedelta(days=30)]
            elif per_a == "90 días":
                la = la[la["date"] >= today - dt.timedelta(days=90)]
            elif per_a.startswith("Año"):
                la = la[la["ts"].dt.year == year]
            if solo_sin:
                la = la[~la["gear_id"].isin(list(shoe_name))]
            la = la.sort_values("ts", ascending=False)
            n_sin = int((~la["gear_id"].isin(list(shoe_name))).sum())
            st.markdown(f'<div class="note">{len(la)} actividades · {n_sin} sin zapatilla</div>', unsafe_allow_html=True)
            if not len(la):
                st.info("No hay actividades con esos filtros.")
            else:
                PPA = 20
                npg = max(1, math.ceil(len(la) / PPA))
                sig_a = f"{per_a}|{','.join(tip_a)}|{solo_sin}|{len(la)}"
                if st.session_state.get("mt_as_sig") != sig_a:
                    st.session_state["mt_as_sig"] = sig_a
                    st.session_state["mt_as_page"] = 1
                pg = min(max(1, int(st.session_state.get("mt_as_page", 1))), npg)
                if npg > 1:
                    q1, q2, q3, _ = st.columns([1, 1.6, 1, 3], vertical_alignment="center")
                    with q1:
                        if st.button("◀ Anterior", disabled=pg <= 1, width="stretch", key="mt_as_prev"):
                            st.session_state["mt_as_page"] = pg - 1
                            st.rerun()
                    with q2:
                        st.markdown(f'<div class="note" style="text-align:center">Página <b style="color:{INK}">{pg}</b> de {npg}</div>',
                                    unsafe_allow_html=True)
                    with q3:
                        if st.button("Siguiente ▶", disabled=pg >= npg, width="stretch", key="mt_as_next"):
                            st.session_state["mt_as_page"] = pg + 1
                            st.rerun()
                rows_a = la.iloc[(pg - 1) * PPA: pg * PPA]
                act_ids = list(SB.loc[~SB["ret"], "id"])
                CWA = [1.0, 2.6, 0.9, 0.8, 0.8, 2.3]
                ha = st.columns(CWA, vertical_alignment="center")
                for col, (t, r) in zip(ha, [("Fecha", ""), ("Actividad", ""), ("Tipo", ""), ("Km", "r"), ("D+", "r"), ("Zapatilla", "")]):
                    col.markdown(f'<div class="chd {r}">{t}</div>', unsafe_allow_html=True)
                with st.form("mat_assign_form", border=False):
                    sel_a = {}
                    for i, (_, rw) in enumerate(rows_a.iterrows()):
                        cur_g = rw["gear_id"] if rw["gear_id"] in shoe_name else ""
                        opts = [""] + act_ids + ([cur_g] if cur_g and cur_g not in act_ids else [])
                        with st.container(key=f"crow{'E' if i % 2 else 'O'}_m{i}"):
                            cc = st.columns(CWA, vertical_alignment="center")
                            cc[0].markdown(f'<div class="ctd" style="font-family:IBM Plex Mono,monospace">{rw["ts"].strftime("%d/%m/%y")}</div>',
                                           unsafe_allow_html=True)
                            cc[1].markdown(f'<div class="ctd" title="{_html.escape(rw["name"])}">{_html.escape(rw["name"])}</div>',
                                           unsafe_allow_html=True)
                            cc[2].markdown(f'<div class="ctd">{SHOE_SPORTS.get(rw["sport"], rw["sport"])}</div>', unsafe_allow_html=True)
                            cc[3].markdown(f'<div class="ctd r">{fnum(rw["km"], 1)}</div>', unsafe_allow_html=True)
                            cc[4].markdown(f'<div class="ctd r">{fnum(rw["dp"])}</div>', unsafe_allow_html=True)
                            sel_a[rw["id"]] = (cur_g, cc[5].selectbox(
                                "Zapatilla", opts, index=opts.index(cur_g), label_visibility="collapsed", key=f"mas_{rw['id']}",
                                format_func=lambda i: "— sin zapatilla —" if not i else shoe_name.get(i, i)))
                    sub_a = st.form_submit_button("Revisar cambios", type="primary")
                if sub_a:
                    ch = [(aid, old, new) for aid, (old, new) in sel_a.items() if (old or "") != (new or "")]
                    if not ch:
                        st.info("No hay cambios que guardar.")
                        st.session_state.pop("mat_pending", None)
                    else:
                        st.session_state["mat_pending"] = dict(kind="assign", changes=ch)
                pend = st.session_state.get("mat_pending")
                if pend and pend.get("kind") == "assign":
                    info_ = la.set_index("id")
                    with st.container(border=True):
                        n_ch = len(pend["changes"])
                        st.markdown(f"**Vas a cambiar la zapatilla de {n_ch} actividad{'es' if n_ch != 1 else ''}:**")
                        st.markdown("\n".join(
                            f"- {info_.loc[aid, 'ts'].strftime('%d/%m/%y') if aid in info_.index else aid} · "
                            f"{_html.escape(str(info_.loc[aid, 'name'])) if aid in info_.index else ''}: "
                            f"{shoe_name.get(old, '—') if old else '—'} → **{shoe_name.get(new, '—') if new else 'sin zapatilla'}**"
                            for aid, old, new in pend["changes"]))
                        b1, b2, _ = st.columns([1.2, 1, 3])
                        if b1.button("Confirmar y guardar", type="primary", key="mt_as_conf"):
                            ov = dict(st.session_state.get("gear_overrides", {}))
                            ok, fails, touched = 0, [], set()
                            for aid, old, new in pend["changes"]:
                                try:
                                    if not demo:
                                        icu_write("PUT", f"/activity/{aid}", {"gear": {"id": new} if new else None})
                                    ov[aid] = new or None
                                    touched |= {x for x in (old, new) if x}
                                    ok += 1
                                except Exception as e:  # noqa: BLE001
                                    fails.append(f"{aid}: {e}")
                            if not demo:
                                for gid in touched:
                                    try:
                                        icu_write("GET", f"/athlete/{athlete}/gear/{gid}/calc")
                                    except Exception as e:  # noqa: BLE001
                                        fails.append(f"recalcular {shoe_name.get(gid, gid)}: {e}")
                                st.cache_data.clear()
                            st.session_state["gear_overrides"] = ov
                            st.session_state.pop("mat_pending", None)
                            if fails:
                                st.error("Algunos cambios no se guardaron:\n\n" + "\n\n".join(fails))
                            if ok:
                                st.session_state["mat_msg"] = (f"Zapatilla actualizada en {ok} actividad{'es' if ok != 1 else ''}"
                                                               + (" (DEMO)." if demo else "."))
                                st.rerun()
                        if b2.button("Cancelar", key="mt_as_cancel"):
                            st.session_state.pop("mat_pending", None)
                            st.rerun()

with tab_cmp:
    # ─────────────────────────── Comparar dos actividades ───────────────────────────
    # (usa `hist`, el histórico completo cargado en la pestaña Material)
    st.subheader("Comparar dos actividades")
    CMP_SPORTS = {"Trail": ["TrailRun"], "Carrera": ["Run"], "Caminata": ["Hike", "Walk"]}
    hms = lambda s_: "—" if s_ is None or pd.isna(s_) else f"{int(s_ // 3600)}:{int(s_ % 3600 // 60):02d}:{int(s_ % 60):02d}"  # noqa: E731
    mmss = lambda s_: "—" if s_ is None or pd.isna(s_) or s_ <= 0 else f"{int(s_ // 60)}:{int(round(s_ % 60)) % 60:02d}"  # noqa: E731

    def sgn_time(d_):
        if d_ is None or pd.isna(d_):
            return "—"
        return ("−" if d_ < 0 else "+") + mmss(abs(d_)) if abs(d_) >= 1 else "0:00"

    all_cmp = hist[hist["sport"].isin(sum(CMP_SPORTS.values(), []))].sort_values("ts", ascending=False) if len(hist) else hist
    if not len(all_cmp):
        st.info("No hay actividades de carrera, trail o caminata para comparar.")
    else:
        f1_, f2_ = st.columns([2, 1])
        with f1_:
            tip_c = st.pills("Tipo", list(CMP_SPORTS), selection_mode="multi", default=["Trail"], key="cmp_tipo") or list(CMP_SPORTS)
        years_c = sorted(all_cmp["ts"].dt.year.unique().tolist(), reverse=True)
        with f2_:
            yr_c = st.selectbox("Año de A", ["Todos"] + years_c, key="cmp_year")
        sp_sel = sum((CMP_SPORTS[t_] for t_ in tip_c), [])
        pool = all_cmp[all_cmp["sport"].isin(sp_sel)]
        pool_a = pool if yr_c == "Todos" else pool[pool["ts"].dt.year == yr_c]
        info_c = all_cmp.set_index("id")
        lab_c = lambda i: (f"{info_c.loc[i, 'ts']:%d/%m/%y} · {str(info_c.loc[i, 'name'])[:34]} · "  # noqa: E731
                           f"{fnum(info_c.loc[i, 'km'], 1)} km · {fnum(info_c.loc[i, 'dp'])} m")
        if not len(pool_a):
            st.info("No hay actividades con esos filtros.")
            st.stop()
        opts_a = list(pool_a["id"])
        if st.session_state.get("cmp_a") not in opts_a:
            st.session_state.pop("cmp_a", None)

        def _swap():
            a_, b_ = st.session_state.get("cmp_a"), st.session_state.get("cmp_b")
            if a_ and b_:
                st.session_state["cmp_a"], st.session_state["cmp_b"] = b_, a_
                st.session_state["cmp_b_for"] = b_           # mantener la B intercambiada
                st.session_state["cmp_year"] = "Todos"

        s1_, s2_ = st.columns([4, 1.3], vertical_alignment="bottom")
        with s1_:
            act_a = st.selectbox("Actividad A", opts_a, format_func=lab_c, key="cmp_a")
        with s2_:
            st.button("⇅ Intercambiar", on_click=_swap, width="stretch", key="cmp_swap")
        ra = info_c.loc[act_a]

        # Rutas parecidas a A (distancia ±5 %, D+ ±7 %), comprobadas con GPS
        sim_pool = all_cmp[(all_cmp["id"] != act_a) & (all_cmp["km"].between(ra["km"] * .95, ra["km"] * 1.05))
                           & (all_cmp["dp"].between(ra["dp"] * .93, ra["dp"] * 1.07))].copy()

        def load_df(aid):
            r_ = info_c.loc[aid]
            if demo:
                return streams_to_df(demo_streams(aid, float(r_["km"]), float(r_["dp"]), float(r_["secs"]))), "demo"
            try:
                d_ = streams_to_df(fetch_streams(key, aid))
            except Exception:  # noqa: BLE001
                d_ = pd.DataFrame()
            if len(d_):
                return d_, "streams"
            try:
                d_ = streams_to_df(fetch_fit_streams(key, aid))
            except Exception:  # noqa: BLE001
                d_ = pd.DataFrame()
            return d_, "fichero original" if len(d_) else "sin datos"

        with st.spinner("Leyendo los datos por segundo…"):
            df_a, src_a = load_df(act_a)
            if len(sim_pool):
                sim_pool["_k"] = (sim_pool["km"] / ra["km"] - 1).abs() + (sim_pool["dp"] / max(1, ra["dp"]) - 1).abs()
                top_ = sim_pool.nsmallest(6, "_k")
                rec = {}
                for aid in top_["id"]:
                    d_, _src = load_df(aid)
                    sim_ = route_similarity(df_a, d_) if len(df_a) and len(d_) else None
                    rec[aid] = sim_["label"] if sim_ else "sin GPS"
                sim_pool["recorrido"] = sim_pool["id"].map(rec).fillna("sin comprobar")
                sim_pool["_o"] = sim_pool["recorrido"].map({"misma ruta": 0, "parecida": 1, "sin GPS": 2, "sin comprobar": 3, "distinta": 4})
                sim_pool = sim_pool.sort_values(["_o", "ts"], ascending=[True, False])
        if len(sim_pool):
            st.markdown('<div class="note" style="margin:6px 0 2px">Rutas parecidas a A (distancia ±5 %, D+ ±7 %; recorrido comprobado con GPS)</div>',
                        unsafe_allow_html=True)
            badge = {"misma ruta": GREEN, "parecida": ORANGE, "distinta": RED, "sin GPS": MUTED, "sin comprobar": MUTED}
            html_table(pd.DataFrame({"Fecha": sim_pool["ts"].dt.strftime("%d/%m/%y").values, "Actividad": sim_pool["name"].values,
                                     "Km": sim_pool["km"].values, "D+": sim_pool["dp"].values, "Recorrido": sim_pool["recorrido"].values}),
                       left={"Actividad", "Recorrido"}, max_height=230,
                       fmt={"Km": lambda v: fnum(v, 1), "D+": lambda v: fnum(v),
                            "Actividad": lambda v: (str(v)[:40] + "…") if len(str(v)) > 41 else str(v),
                            "Recorrido": lambda v: f'<span class="chip" style="--c:{badge[v]};--o:{on(badge[v])}">{v}</span>'})
        else:
            st.markdown('<div class="note">No hay otras actividades con distancia ±5 % y D+ ±7 % que A.</div>', unsafe_allow_html=True)
        opts_b = list(sim_pool["id"]) + [i for i in pool["id"] if i != act_a and i not in set(sim_pool["id"])]
        if not opts_b:
            st.info("No hay otra actividad con la que comparar.")
            st.stop()
        if (st.session_state.get("cmp_b") not in opts_b or st.session_state.get("cmp_b") == act_a
                or st.session_state.get("cmp_b_for") != act_a):     # al cambiar A, proponer la ruta más parecida
            if not (st.session_state.get("cmp_b_for") == act_a and st.session_state.get("cmp_b") in opts_b):
                st.session_state["cmp_b"] = opts_b[0]
        st.session_state["cmp_b_for"] = act_a
        sim_ids = set(sim_pool["id"])
        act_b = st.selectbox("Actividad B", opts_b, key="cmp_b",
                             format_func=lambda i: ("≈ " if i in sim_ids else "") + lab_c(i))
        rb = info_c.loc[act_b]
        with st.spinner("Leyendo los datos por segundo…"):
            df_b, src_b = load_df(act_b)

        # ── Resumen ──
        st.markdown(f'<div class="note" style="margin-top:8px"><span style="color:{GOLD}">●</span> A · {lab_c(act_a)}<br>'
                    f'<span style="color:{GLACIER}">●</span> B · {lab_c(act_b)}</div>', unsafe_allow_html=True)
        stop_a, stop_b = ra["elapsed"] - ra["secs"], rb["elapsed"] - rb["secs"]

        def dnum(va, vb, d=0, u="", inv=False):
            if pd.isna(va) or pd.isna(vb):
                return "—"
            x = vb - va
            good = x < 0 if inv else x > 0
            c_ = GREEN if good else RED if abs(x) > 1e-9 else MUTED
            return f'<span style="color:{c_}">{"+" if x > 0 else "−" if x < 0 else ""}{fnum(abs(x), d)}{u}</span>'

        def dtime(va, vb):
            if pd.isna(va) or pd.isna(vb):
                return "—"
            x = vb - va
            return f'<span style="color:{GREEN if x < 0 else RED if x > 0 else MUTED}">{sgn_time(x)}</span>'

        pace_a = ra["secs"] / ra["km"] if ra["km"] else np.nan
        pace_b = rb["secs"] / rb["km"] if rb["km"] else np.nan
        summ = pd.DataFrame([
            ("Fecha", f"{ra['ts']:%d/%m/%y}", f"{rb['ts']:%d/%m/%y}", ""),
            ("Reloj", str(ra.get("device") or "—").replace("SUUNTO ", ""), str(rb.get("device") or "—").replace("SUUNTO ", ""), ""),
            ("Distancia", f"{fnum(ra['km'], 2)} km", f"{fnum(rb['km'], 2)} km", dnum(ra["km"], rb["km"], 2, " km")),
            ("D+", f"{fnum(ra['dp'])} m", f"{fnum(rb['dp'])} m", dnum(ra["dp"], rb["dp"], 0, " m")),
            ("D−", f"{fnum(ra['dm'])} m", f"{fnum(rb['dm'])} m", dnum(ra["dm"], rb["dm"], 0, " m")),
            ("Tiempo en movimiento", hms(ra["secs"]), hms(rb["secs"]), dtime(ra["secs"], rb["secs"])),
            ("Tiempo total", hms(ra["elapsed"]), hms(rb["elapsed"]), dtime(ra["elapsed"], rb["elapsed"])),
            ("Tiempo parado", hms(stop_a), hms(stop_b), dtime(stop_a, stop_b)),
            ("Ritmo (min/km)", mmss(pace_a), mmss(pace_b), dtime(pace_a, pace_b)),
            ("FC media", f"{fnum(ra['hr_avg'])} ppm" if pd.notna(ra["hr_avg"]) else "—",
             f"{fnum(rb['hr_avg'])} ppm" if pd.notna(rb["hr_avg"]) else "—", dnum(ra["hr_avg"], rb["hr_avg"], 0, " ppm", inv=True)),
            ("Carga", fnum(ra["load"]), fnum(rb["load"]), dnum(ra["load"], rb["load"], 0, "", inv=True)),
        ], columns=["Métrica", "A", "B", "Diferencia B − A"])
        html_table(summ, left={"Métrica"})

        notes_ = []        # «A tener en cuenta»
        if not len(df_a) or not len(df_b):
            falta = " y ".join(x for x, d_ in (("A", df_a), ("B", df_b)) if not len(d_))
            st.warning(f"No hay datos por segundo de {falta} (ni en intervals.icu ni en el fichero original): solo se muestra el resumen.")
        else:
            for lab_, d_, r_, src_ in (("A", df_a, ra, src_a), ("B", df_b, rb, src_b)):
                mv = stream_stats(d_)["mov"]
                if r_["secs"] and abs(mv - r_["secs"]) / r_["secs"] > 0.02:
                    notes_.append(f"En {lab_}, el tiempo en movimiento calculado por segundo ({hms(mv)}) difiere más de un 2 % "
                                  f"del de intervals.icu ({hms(r_['secs'])}); los tiempos por tramo pueden desviarse algo.")
                if src_ == "fichero original":
                    notes_.append(f"Los datos por segundo de {lab_} salen del fichero original del reloj (intervals.icu no los devolvió).")

            # ── Bandas de pendiente ──
            st.subheader("Por pendiente")
            ba, bb = grade_bands(df_a), grade_bands(df_b)
            vv = lambda r_: r_["vam"] if pd.notna(r_["vam"]) else r_["vdesc"]  # noqa: E731
            bt = pd.DataFrame({
                "Pendiente": ba["band"], "Km|A": ba["km"], "Km|B": bb["km"], "Tiempo|A": ba["mt"], "Tiempo|B": bb["mt"],
                "Ritmo|A": ba["pace"], "Ritmo|B": bb["pace"],
                "VAM / bajada|A": [vv(r_) for _, r_ in ba.iterrows()], "VAM / bajada|B": [vv(r_) for _, r_ in bb.iterrows()],
                "FC|A": ba["hr"], "FC|B": bb["hr"]})
            bt["Δ m/h"] = bt["VAM / bajada|B"] - bt["VAM / bajada|A"]
            bt = bt[["Pendiente", "Km|A", "Km|B", "Tiempo|A", "Tiempo|B", "Ritmo|A", "Ritmo|B", "VAM / bajada|A", "VAM / bajada|B", "Δ m/h", "FC|A", "FC|B"]]
            nf = lambda d, u="": (lambda v: "—" if pd.isna(v) else f"{fnum(v, d)}{u}")  # noqa: E731
            dcol = lambda v: "—" if pd.isna(v) else f'<span style="color:{GREEN if v > 0 else RED if v < 0 else MUTED}">{"+" if v > 0 else "−" if v < 0 else ""}{fnum(abs(v))}</span>'  # noqa: E731
            html_table(bt, left={"Pendiente"}, group_start={"Km|A", "Tiempo|A", "Ritmo|A", "VAM / bajada|A", "FC|A"},
                       groups=[("", 1, ""), ("Km", 2, "g"), ("Tiempo mov.", 2, "g"), ("Ritmo min/km", 2, "g"),
                               ("VAM / bajada m/h", 3, "g"), ("FC media", 2, "g")],
                       fmt={"Km|A": nf(1), "Km|B": nf(1), "Tiempo|A": hms, "Tiempo|B": hms, "Ritmo|A": mmss, "Ritmo|B": mmss,
                            "VAM / bajada|A": nf(0), "VAM / bajada|B": nf(0), "Δ m/h": dcol, "FC|A": nf(0), "FC|B": nf(0)})
            st.markdown('<span class="note">En subidas, VAM (metros subidos por hora); en bajadas, metros bajados por hora. '
                        'Δ en verde: B sube o baja más rápido que A.</span>', unsafe_allow_html=True)
            g1_, g2_ = st.columns(2)
            with g1_:
                f_v = go.Figure()
                for lab_, b_, c_ in (("A", ba, GOLD), ("B", bb, GLACIER)):
                    f_v.add_bar(x=b_["band"], y=[vv(r_) for _, r_ in b_.iterrows()], name=lab_, marker_color=c_,
                                hovertemplate="%{x} · %{y:.0f} m/h<extra>" + lab_ + "</extra>")
                f_v.update_layout(barmode="group")
                f_v.update_yaxes(ticksuffix=" m/h")
                st.markdown('<span class="note">VAM / velocidad de bajada por pendiente</span>', unsafe_allow_html=True)
                st.plotly_chart(plot_layout(f_v, 280), width="stretch", theme=None)
            with g2_:
                f_h = go.Figure()
                for lab_, b_, c_ in (("A", ba, GOLD), ("B", bb, GLACIER)):
                    f_h.add_bar(x=b_["band"], y=b_["hr"], name=lab_, marker_color=c_, hovertemplate="%{x} · %{y:.0f} ppm<extra>" + lab_ + "</extra>")
                f_h.update_layout(barmode="group")
                lo_ = np.nanmin([ba["hr"].min(), bb["hr"].min()]) if ba["hr"].notna().any() or bb["hr"].notna().any() else 100
                hi_ = np.nanmax([ba["hr"].max(), bb["hr"].max()]) if ba["hr"].notna().any() or bb["hr"].notna().any() else 180
                f_h.update_yaxes(range=[max(0, (lo_ if pd.notna(lo_) else 100) - 15), (hi_ if pd.notna(hi_) else 180) + 8], ticksuffix=" ppm")
                st.markdown('<span class="note">FC media por pendiente</span>', unsafe_allow_html=True)
                st.plotly_chart(plot_layout(f_h, 280), width="stretch", theme=None)

            # ── Tramo a tramo ──
            sim_ab = route_similarity(df_a, df_b)
            same_guess = (sim_ab["label"] == "misma ruta") if sim_ab else bool(
                abs(rb["km"] / ra["km"] - 1) <= .05 and abs(rb["dp"] / max(1, ra["dp"]) - 1) <= .07)
            st.subheader("Tramo a tramo")
            t1_, t2_ = st.columns([2, 1], vertical_alignment="bottom")
            with t1_:
                if sim_ab:
                    st.markdown(f'<div class="note">Recorrido según GPS: <b style="color:{INK}">{sim_ab["label"]}</b> · desviación mediana '
                                f'{fnum(sim_ab["dev"])} m · inicios a {fnum(sim_ab["start"])} m · cimas a {fnum(sim_ab["top"])} m</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown('<div class="note">Sin GPS en alguna de las dos: la ruta se supone igual por distancia y desnivel, '
                                'y los tramos se sitúan por distancia y altitud.</div>', unsafe_allow_html=True)
                do_seg = st.toggle("Comparar tramo a tramo (misma ruta)", value=same_guess, key=f"cmp_seg_{act_a}_{act_b}")
            with t2_:
                amp = st.slider("Desnivel mínimo de un tramo (m)", 30, 200, 60, 10, key="cmp_amp")
            seg_rows = []
            if do_seg:
                segs = find_segments(df_a, amp)
                if len(segs) < 2:
                    st.info("No hay subidas ni bajadas con ese desnivel mínimo. Bájalo para ver más tramos.")
                else:
                    bnd_a = [segs[0][0]] + [s_[1] for s_ in segs]
                    bnd_b = locate_in(df_b, df_a, bnd_a, use_gps=bool(sim_ab))
                    for i_, (d0, d1) in enumerate(segs):
                        sa_, sb_ = span_stats(df_a, d0, d1), span_stats(df_b, bnd_b[i_], bnd_b[i_ + 1])
                        up_ = sa_["a1"] > sa_["a0"]
                        rate = lambda s_: (s_["gain"] if up_ else s_["loss"]) / s_["mt"] * 3600 if s_["mt"] and s_["mt"] > 0 else np.nan  # noqa: E731
                        seg_rows.append(dict(n=i_ + 1, up=up_, d0=d0, d1=d1, a0=sa_["a0"], a1=sa_["a1"], km=sa_["km"],
                                             grade=100 * (sa_["a1"] - sa_["a0"]) / max(1, d1 - d0), ta=sa_["mt"], tb=sb_["mt"],
                                             ra=rate(sa_), rb=rate(sb_), hra=sa_["hr"], hrb=sb_["hr"], kmb=sb_["km"]))
                    SG = pd.DataFrame(seg_rows)
                    SG["diff"] = SG["tb"] - SG["ta"]
                    tbl = pd.DataFrame({
                        "Nº": SG["n"], "Tramo": np.where(SG["up"], "▲ Subida", "▼ Bajada"),
                        "Altitud": [f"{fnum(r_.a0)} → {fnum(r_.a1)} m" for r_ in SG.itertuples()],
                        "Km": SG["km"], "Pend.": SG["grade"], "Tiempo|A": SG["ta"], "Tiempo|B": SG["tb"], "Dif. B−A": SG["diff"],
                        "VAM / bajada|A": SG["ra"], "VAM / bajada|B": SG["rb"], "FC|A": SG["hra"], "FC|B": SG["hrb"]})
                    tot_row = pd.DataFrame([{"Nº": "", "Tramo": "Total", "Altitud": "", "Km": SG["km"].sum(), "Pend.": np.nan,
                                             "Tiempo|A": SG["ta"].sum(), "Tiempo|B": SG["tb"].sum(), "Dif. B−A": SG["diff"].sum(),
                                             "VAM / bajada|A": np.nan, "VAM / bajada|B": np.nan, "FC|A": np.nan, "FC|B": np.nan}])
                    tbl = pd.concat([tbl, tot_row], ignore_index=True)
                    up_c = lambda v: (f'<span style="color:{GOLD}">{v}</span>' if str(v).startswith("▲") else  # noqa: E731
                                      f'<span style="color:{GLACIER}">{v}</span>' if str(v).startswith("▼") else v)
                    dtf = lambda v: "—" if pd.isna(v) else f'<span style="color:{GREEN if v < 0 else RED if v > 0 else MUTED}">{sgn_time(v)}</span>'  # noqa: E731
                    html_table(tbl, left={"Tramo", "Altitud"}, total_last=True, group_start={"Tiempo|A", "VAM / bajada|A", "FC|A"},
                               groups=[("", 5, ""), ("Tiempo en movimiento", 3, "g"), ("VAM / bajada m/h", 2, "g"), ("FC media", 2, "g")],
                               fmt={"Km": nf(1), "Pend.": lambda v: "" if pd.isna(v) else f"{fnum(v)} %", "Tramo": up_c,
                                    "Tiempo|A": hms, "Tiempo|B": hms, "Dif. B−A": dtf,
                                    "VAM / bajada|A": nf(0), "VAM / bajada|B": nf(0), "FC|A": nf(0), "FC|B": nf(0)})
                    st.markdown('<span class="note">Diferencia en verde: B fue más rápida en ese tramo. Los tramos se detectan en A '
                                'y se buscan en B por GPS (o por distancia y altitud si no hay GPS).</span>', unsafe_allow_html=True)

                    # Perfil de A con tramos
                    f_p = go.Figure()
                    xa = df_a["dist"] / 1000
                    base_ = float(df_a["alt_s"].min()) - 30
                    for r_ in SG.itertuples():
                        f_p.add_vrect(x0=r_.d0 / 1000, x1=r_.d1 / 1000, fillcolor=GOLD if r_.up else GLACIER, opacity=.10, line_width=0,
                                      annotation_text=str(r_.n), annotation_position="top", annotation_font=dict(color=INK, size=12))
                    f_p.add_scatter(x=xa, y=df_a["alt_s"], mode="lines", line=dict(color=GOLD, width=2), name="A",
                                    fill="tozeroy", fillcolor=rgba(GOLD, .12), hovertemplate="%{x:.1f} km · %{y:.0f} m<extra>A</extra>")
                    f_p.update_yaxes(range=[base_, float(df_a["alt_s"].max()) + 60], ticksuffix=" m")
                    f_p.update_xaxes(ticksuffix=" km")
                    st.markdown('<span class="note">Perfil de A con los tramos numerados</span>', unsafe_allow_html=True)
                    st.plotly_chart(plot_layout(f_p, 260, legend=False), width="stretch", theme=None)

                    # Diferencia acumulada
                    f_c = go.Figure()
                    mid = ((SG["d0"] + SG["d1"]) / 2000).tolist()
                    f_c.add_bar(x=mid, y=SG["diff"] / 60, width=((SG["d1"] - SG["d0"]) / 1000 * .9).tolist(),
                                marker_color=[GREEN if v < 0 else RED for v in SG["diff"]], opacity=.55, name="por tramo",
                                customdata=SG["n"], hovertemplate="Tramo %{customdata} · %{y:+.1f} min<extra></extra>")
                    xs_ = [SG["d0"].iloc[0] / 1000] + (SG["d1"] / 1000).tolist()
                    ys_ = [0.0] + (SG["diff"].cumsum() / 60).tolist()
                    f_c.add_scatter(x=xs_, y=ys_, mode="lines+markers", line=dict(color=INK, width=2), name="acumulada",
                                    hovertemplate="km %{x:.1f} · %{y:+.1f} min<extra>acumulada</extra>")
                    f_c.add_hline(y=0, line=dict(color=MUTED, width=1))
                    f_c.update_yaxes(ticksuffix=" min")
                    f_c.update_xaxes(ticksuffix=" km")
                    st.markdown('<span class="note">Diferencia de tiempo B − A: por debajo de 0, B va por delante</span>', unsafe_allow_html=True)
                    st.plotly_chart(plot_layout(f_c, 260), width="stretch", theme=None)

            # FC frente a distancia
            f_hr = go.Figure()
            for lab_, d_, c_ in (("A", df_a, GOLD), ("B", df_b, GLACIER)):
                if d_["hr"].notna().any():
                    f_hr.add_scatter(x=d_["dist"] / 1000, y=d_["hr"].rolling(30, min_periods=5, center=True).mean(), mode="lines",
                                     line=dict(color=c_, width=1.6), name=lab_, hovertemplate="%{x:.1f} km · %{y:.0f} ppm<extra>" + lab_ + "</extra>")
            f_hr.update_yaxes(ticksuffix=" ppm")
            f_hr.update_xaxes(ticksuffix=" km")
            st.markdown('<span class="note">Frecuencia cardiaca a lo largo de la distancia (media de 30 s)</span>', unsafe_allow_html=True)
            st.plotly_chart(plot_layout(f_hr, 260), width="stretch", theme=None)

            # ── Carrera virtual ──
            st.subheader("Carrera virtual A vs B")
            race_ok = (sim_ab["label"] != "distinta") if sim_ab else same_guess
            if not race_ok:
                st.info("Las dos actividades no siguen el mismo recorrido: la carrera virtual solo tiene sentido en la misma ruta.")
            else:
                rv1, rv2 = st.columns([1, 2], vertical_alignment="center")
                with rv1:
                    mov_clock = st.toggle("Descontar paradas", value=False, key="race_mov",
                                          help="Activado: cada una avanza solo con su tiempo en movimiento. Desactivado: tiempo real, con paradas.")
                with rv2:
                    y_mode = st.segmented_control("Gráfico de diferencia", ["Tiempo por distancia", "Distancia por tiempo"],
                                                  default="Tiempo por distancia", key="race_y", label_visibility="collapsed") or "Tiempo por distancia"
                R = race_cached(act_a, act_b, mov_clock, bool(sim_ab), df_a, df_b)
                if not sim_ab:
                    st.caption("Sin GPS en alguna de las dos: B se sitúa sobre la ruta de A por distancia (aproximado).")
                elif R["off"].mean() > .05:
                    st.caption(f"B se sale del recorrido de A en un {fnum(R['off'].mean() * 100)} % de la ruta: ahí la diferencia es aproximada.")
                Tn = len(R["T"])
                tmax = int(R["T"][-1])
                skey = f"race_t_{act_a}_{act_b}_{int(mov_clock)}"
                if skey not in st.session_state:
                    st.session_state[skey] = tmax

                def _nudge(delta, k_=skey, mx=tmax):
                    st.session_state[k_] = int(min(mx, max(0, st.session_state.get(k_, 0) + delta)))

                n1, n2, n3 = st.columns([1, 10, 1], vertical_alignment="bottom")
                n1.button("◀", on_click=_nudge, args=(-60,), key=skey + "_m", help="−1 min", width="stretch")
                with n2:
                    t_sel = st.select_slider("Tiempo de carrera", options=list(range(0, tmax + 1, 10)), key=skey,
                                             format_func=lambda v: f"{int(v // 3600)}:{int(v % 3600 // 60):02d}:{int(v % 60):02d}")
                n3.button("▶", on_click=_nudge, args=(60,), key=skey + "_p", help="+1 min", width="stretch")
                k_t = int(min(Tn - 1, max(0, round(t_sel / 10))))
                dd_, gt_ = race_gap(R, k_t)
                fin_a, fin_b = R["T"][k_t] >= R["endA"], R["T"][k_t] >= R["endB"]

                def who(gt, dd):
                    if abs(gt) < 3 and abs(dd) < 10:
                        return "Empatadas", MUTED
                    return ((f"B {mmss(abs(gt))} por delante", GLACIER) if gt > 0 else (f"A {mmss(abs(gt))} por delante", GOLD))

                txt_, col_ = who(gt_, dd_)
                lineA = (f"🏁 meta en {hms(R['endA'])}" if fin_a else f"{fnum(R['altTA'][k_t])} m · {fnum(R['hrA'][k_t])} ppm")
                lineB = (f"🏁 meta en {hms(R['endB'])}" if fin_b else f"{fnum(R['altTB'][k_t])} m · {fnum(R['hrB'][k_t])} ppm")
                if fin_a and fin_b:
                    txt_, col_ = ((f"B {mmss(R['endA'] - R['endB'])} más rápida", GLACIER) if R["endB"] < R["endA"]
                                  else (f"A {mmss(R['endB'] - R['endA'])} más rápida", GOLD))
                cards([
                    ("Tiempo de carrera", INK, hms(R["T"][k_t]), "", ["con paradas descontadas" if mov_clock else "tiempo real, con paradas"]),
                    ("Distancia A", GOLD, fnum(R["ownA"][k_t] / 1000, 2), "km", [lineA]),
                    ("Distancia B", GLACIER, fnum(R["ownB"][k_t] / 1000, 2), "km", [lineB]),
                    ("Diferencia", col_, txt_, "", ["resultado final" if fin_a and fin_b else f"{fnum(abs(dd_))} m de distancia en la ruta"]),
                ])

                # Gráfico de diferencia (+ perfil de A)
                if y_mode == "Tiempo por distancia":
                    xk, y_ = R["dA"] / 1000, R["dT"] / 60
                    f_r = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.72, .28], vertical_spacing=.04)
                    f_r.add_scatter(x=xk, y=np.minimum(y_, 0), fill="tozeroy", mode="lines", line=dict(color=GREEN, width=0),
                                    fillcolor=rgba(GREEN, .45), name="B por delante", hoverinfo="skip", row=1, col=1)
                    f_r.add_scatter(x=xk, y=np.maximum(y_, 0), fill="tozeroy", mode="lines", line=dict(color=RED, width=0),
                                    fillcolor=rgba(RED, .45), name="B por detrás", hoverinfo="skip", row=1, col=1)
                    f_r.add_scatter(x=xk, y=y_, mode="lines", line=dict(color=INK, width=1.4), showlegend=False,
                                    customdata=np.stack([R["altA"], R["tA"], R["tB"]], axis=-1),
                                    hovertemplate="km %{x:.2f} · %{customdata[0]:.0f} m<br>B − A: %{y:+.1f} min<extra></extra>", row=1, col=1)
                    f_r.add_scatter(x=xk, y=R["altA"], mode="lines", fill="tozeroy", line=dict(color=GOLD, width=1.2),
                                    fillcolor=rgba(GOLD, .14), showlegend=False, hovertemplate="km %{x:.2f} · %{y:.0f} m<extra>perfil A</extra>",
                                    row=2, col=1)
                    plot_layout(f_r, 380)
                    f_r.update_yaxes(ticksuffix=" min", zeroline=True, zerolinecolor=MUTED, row=1, col=1)
                    f_r.update_yaxes(range=[float(np.nanmin(R["altA"])) - 30, float(np.nanmax(R["altA"])) + 40], ticksuffix=" m", row=2, col=1)
                    f_r.update_xaxes(ticksuffix=" km", row=2, col=1)
                    f_r.add_vline(x=min(R["posA"][k_t], R["posB"][k_t]) / 1000, line=dict(color=INK, width=1, dash="dot"))
                    st.markdown('<span class="note">Diferencia de tiempo B − A al pasar por cada punto de la ruta (por debajo de 0, B va por '
                                'delante) y, debajo, el perfil de A. La línea de puntos es el instante elegido.</span>', unsafe_allow_html=True)
                else:
                    both = R["T"] <= min(R["endA"], R["endB"]) + 1
                    xk, y_ = R["T"][both] / 3600, (R["posB"] - R["posA"])[both]
                    f_r = go.Figure()
                    f_r.add_scatter(x=xk, y=np.maximum(y_, 0), fill="tozeroy", mode="lines", line=dict(color=GREEN, width=0),
                                    fillcolor=rgba(GREEN, .45), name="B por delante", hoverinfo="skip")
                    f_r.add_scatter(x=xk, y=np.minimum(y_, 0), fill="tozeroy", mode="lines", line=dict(color=RED, width=0),
                                    fillcolor=rgba(RED, .45), name="B por detrás", hoverinfo="skip")
                    f_r.add_scatter(x=xk, y=y_, mode="lines", line=dict(color=INK, width=1.4), showlegend=False,
                                    hovertemplate="%{x:.2f} h · B − A: %{y:+.0f} m<extra></extra>")
                    plot_layout(f_r, 320)
                    f_r.update_yaxes(ticksuffix=" m", zeroline=True, zerolinecolor=MUTED)
                    f_r.update_xaxes(ticksuffix=" h")
                    f_r.add_vline(x=R["T"][k_t] / 3600, line=dict(color=INK, width=1, dash="dot"))
                    st.markdown('<span class="note">Distancia que B saca a A en cada momento de la carrera (por encima de 0, B va por delante).</span>',
                                unsafe_allow_html=True)
                st.plotly_chart(f_r, width="stretch", theme=None)

                # Mapa animado (2D Plotly / 3D MapLibre) + diferencia + desnivel, sincronizados
                okA, okB = df_a.dropna(subset=["lat", "lng"]), df_b.dropna(subset=["lat", "lng"])
                mc1, mc2 = st.columns([1, 3], vertical_alignment="bottom")
                with mc1:
                    vista_m = st.segmented_control("Vista del mapa", ["2D", "3D"], default="2D", key="race_view") or "2D"
                with mc2:
                    fondo = st.segmented_control(
                        "Fondo del mapa", MAP_BACKGROUNDS, default="Topográfico", key="race_bg2",
                        help="Topográfico: Mapa Topográfico Nacional del IGN (fuera de España, OpenTopoMap). Satélite: PNOA del IGN "
                             "(fuera de España, Esri). «Sin fondo» no descarga mapas: úsalo si tu red los bloquea y la animación no avanza.",
                    ) or "Topográfico"
                if len(okA) < 50 or len(okB) < 50:
                    st.info("Sin GPS en alguna de las dos actividades: no se puede dibujar el mapa.")
                else:
                    simp = lambda d_, n=1500: d_.iloc[np.unique(np.linspace(0, len(d_) - 1, min(len(d_), n)).astype(int))]  # noqa: E731
                    sa_, sb_ = simp(okA), simp(okB)
                    rd = lambda v, n=5: np.round(np.asarray(v, dtype=float), n)  # noqa: E731
                    lat_all = np.concatenate([sa_["lat"].to_numpy(), sb_["lat"].to_numpy()])
                    lng_all = np.concatenate([sa_["lng"].to_numpy(), sb_["lng"].to_numpy()])
                    c_lat, c_lng = float(np.mean(lat_all)), float(np.mean(lng_all))
                    tiles = base_tiles(fondo, c_lat, c_lng, LIGHT)
                    # perfil de la ruta (km de A) y posición de cada una sobre él
                    prof_i = np.unique(np.linspace(0, len(R["dA"]) - 1, min(len(R["dA"]), 220)).astype(int))
                    prof_x, prof_y = R["dA"][prof_i] / 1000, R["altA"][prof_i]
                    alt_on = lambda pos_m: float(np.interp(pos_m, R["dA"], R["altA"]))  # noqa: E731

                    def label_at(k):
                        g_dd, g_gt = race_gap(R, k)
                        t_, _c = who(g_gt, g_dd)
                        if R["T"][k] >= R["endA"] and R["T"][k] >= R["endB"]:
                            t_ = (f"B {mmss(R['endA'] - R['endB'])} más rápida" if R["endB"] < R["endA"]
                                  else f"A {mmss(R['endB'] - R['endA'])} más rápida")
                        return f"{hms(R['T'][k])} · {t_}"

                    def elev_label(k):
                        return (f"A {fnum(alt_on(R['posA'][k]))} m · D+ {fnum(R['dpA'][k])} m   |   "
                                f"B {fnum(alt_on(R['posB'][k]))} m · D+ {fnum(R['dpB'][k])} m")

                    if vista_m == "2D":
                        stepf = max(1, math.ceil(Tn / 240))
                        fidx = list(range(0, Tn, stepf))
                        if fidx[-1] != Tn - 1:
                            fidx.append(Tn - 1)
                        k0 = min(fidx, key=lambda i: abs(i - k_t))
                        if k0 == fidx[-1]:          # con el deslizador en meta, el mapa empieza en la salida para poder reproducir
                            k0 = fidx[0]
                        xk_m, yk_m = R["dA"] / 1000, R["dT"] / 60
                        dp_i = np.unique(np.linspace(0, Tn - 1, min(Tn, 400)).astype(int))

                        def done(lat, lng, k):
                            idx = np.unique(np.linspace(0, k, min(k + 1, 40)).astype(int))
                            return rd(lat[idx]), rd(lng[idx])

                        def prof_done(pos_m):
                            m_ = prof_x[::2] <= pos_m / 1000                  # perfil a media resolución en cada frame
                            xs, ys = list(prof_x[::2][m_]), list(prof_y[::2][m_])
                            return xs + [pos_m / 1000], ys + [alt_on(pos_m)]

                        def dyn(k):
                            la, lo = done(R["latA"], R["lngA"], k)
                            lb, lob = done(R["latB"], R["lngB"], k)
                            pos_ = min(R["posA"][k], R["posB"][k])
                            pxa, pya = prof_done(R["posA"][k])
                            pxb, pyb = prof_done(R["posB"][k])
                            th = R["T"][k] / 3600
                            return [go.Scattermap(lat=la, lon=lo), go.Scattermap(lat=lb, lon=lob),
                                    go.Scattermap(lat=[round(R["latA"][k], 5)], lon=[round(R["lngA"][k], 5)]),
                                    go.Scattermap(lat=[round(R["latB"][k], 5)], lon=[round(R["lngB"][k], 5)]),
                                    go.Scatter(x=[pos_ / 1000], y=[float(np.interp(pos_, R["dA"], R["dT"])) / 60]),
                                    go.Scatter(x=rd(pxa, 3), y=rd(pya, 0)), go.Scatter(x=rd(pxb, 3), y=rd(pyb, 0)),
                                    go.Scatter(x=[pxa[-1]], y=[pya[-1]]), go.Scatter(x=[pxb[-1]], y=[pyb[-1]]),
                                    go.Scatter(x=[th], y=[R["dpA"][k]]), go.Scatter(x=[th], y=[R["dpB"][k]])]

                        f_m = make_subplots(rows=4, cols=1, specs=[[{"type": "map"}], [{"type": "xy"}], [{"type": "xy"}], [{"type": "xy"}]],
                                            row_heights=[.46, .18, .18, .18], vertical_spacing=.045)
                        f_m.add_trace(go.Scattermap(lat=rd(sa_["lat"]), lon=rd(sa_["lng"]), mode="lines", line=dict(color=GOLD, width=2),
                                                    opacity=.45, name="A", hoverinfo="skip", showlegend=False), row=1, col=1)       # 0
                        f_m.add_trace(go.Scattermap(lat=rd(sb_["lat"]), lon=rd(sb_["lng"]), mode="lines", line=dict(color=GLACIER, width=2),
                                                    opacity=.45, name="B", hoverinfo="skip", showlegend=False), row=1, col=1)    # 1
                        d0 = dyn(k0)
                        f_m.add_trace(go.Scattermap(lat=d0[0].lat, lon=d0[0].lon, mode="lines", line=dict(color=GOLD, width=5),
                                                    hoverinfo="skip", showlegend=False), row=1, col=1)                              # 2
                        f_m.add_trace(go.Scattermap(lat=d0[1].lat, lon=d0[1].lon, mode="lines", line=dict(color=GLACIER, width=5),
                                                    hoverinfo="skip", showlegend=False), row=1, col=1)                              # 3
                        f_m.add_trace(go.Scattermap(lat=d0[2].lat, lon=d0[2].lon, mode="markers+text", text=["A"], name="A",
                                                    marker=dict(size=20, color=GOLD), textfont=dict(color=on(GOLD), size=12),
                                                    hoverinfo="skip"), row=1, col=1)                                                # 4
                        f_m.add_trace(go.Scattermap(lat=d0[3].lat, lon=d0[3].lon, mode="markers+text", text=["B"], name="B",
                                                    marker=dict(size=20, color=GLACIER), textfont=dict(color=on(GLACIER), size=12),
                                                    hoverinfo="skip"), row=1, col=1)                                                # 5
                        f_m.add_trace(go.Scatter(x=xk_m, y=yk_m, mode="lines", line=dict(color=INK, width=1.3), showlegend=False,
                                                 hovertemplate="km %{x:.2f} · %{y:+.1f} min<extra>B − A</extra>"), row=2, col=1)     # 6
                        f_m.add_trace(go.Scatter(x=d0[4].x, y=d0[4].y, mode="markers", marker=dict(size=11, color=INK, line=dict(color=BG, width=2)),
                                                 showlegend=False, hoverinfo="skip"), row=2, col=1)                                 # 7
                        f_m.add_trace(go.Scatter(x=rd(prof_x, 3), y=rd(prof_y, 0), mode="lines", line=dict(color=MUTED, width=1.4),
                                                 showlegend=False, hovertemplate="km %{x:.2f} · %{y:.0f} m<extra>perfil</extra>"), row=3, col=1)  # 8
                        f_m.add_trace(go.Scatter(x=d0[5].x, y=d0[5].y, mode="lines", fill="tozeroy", line=dict(color=GOLD, width=2),
                                                 fillcolor=rgba(GOLD, .28), showlegend=False, hoverinfo="skip"), row=3, col=1)       # 9
                        f_m.add_trace(go.Scatter(x=d0[6].x, y=d0[6].y, mode="lines", fill="tozeroy", line=dict(color=GLACIER, width=2),
                                                 fillcolor=rgba(GLACIER, .22), showlegend=False, hoverinfo="skip"), row=3, col=1)    # 10
                        f_m.add_trace(go.Scatter(x=d0[7].x, y=d0[7].y, mode="markers+text", text=["A"], textposition="top center",
                                                 marker=dict(size=13, color=GOLD, line=dict(color=BG, width=1.5)), textfont=dict(color=GOLD),
                                                 showlegend=False, hoverinfo="skip"), row=3, col=1)                                 # 11
                        f_m.add_trace(go.Scatter(x=d0[8].x, y=d0[8].y, mode="markers+text", text=["B"], textposition="top center",
                                                 marker=dict(size=13, color=GLACIER, line=dict(color=BG, width=1.5)), textfont=dict(color=GLACIER),
                                                 showlegend=False, hoverinfo="skip"), row=3, col=1)                                 # 12
                        f_m.add_trace(go.Scatter(x=rd(R["T"][dp_i] / 3600, 4), y=rd(R["dpA"][dp_i], 0), mode="lines", line=dict(color=GOLD, width=1.8),
                                                 name="D+ A", hovertemplate="%{x:.2f} h · %{y:.0f} m<extra>D+ A</extra>"), row=4, col=1)  # 13
                        f_m.add_trace(go.Scatter(x=rd(R["T"][dp_i] / 3600, 4), y=rd(R["dpB"][dp_i], 0), mode="lines", line=dict(color=GLACIER, width=1.8),
                                                 name="D+ B", hovertemplate="%{x:.2f} h · %{y:.0f} m<extra>D+ B</extra>"), row=4, col=1)  # 14
                        f_m.add_trace(go.Scatter(x=d0[9].x, y=d0[9].y, mode="markers", marker=dict(size=10, color=GOLD, line=dict(color=BG, width=1.5)),
                                                 showlegend=False, hoverinfo="skip"), row=4, col=1)                                 # 15
                        f_m.add_trace(go.Scatter(x=d0[10].x, y=d0[10].y, mode="markers", marker=dict(size=10, color=GLACIER, line=dict(color=BG, width=1.5)),
                                                 showlegend=False, hoverinfo="skip"), row=4, col=1)                                 # 16

                        def anns(k):
                            base_ = dict(xref="paper", yref="paper", xanchor="left", yanchor="top", showarrow=False, bgcolor=SURFACE,
                                         bordercolor=LINE, borderwidth=1, borderpad=4)
                            y3 = f_m.layout.yaxis2.domain[1] if f_m.layout.yaxis2.domain else .5
                            return [dict(text=f"<b>{label_at(k)}</b>", x=0.01, y=0.995, font=dict(color=INK, size=13), **base_),
                                    dict(text=elev_label(k), x=0.01, y=y3 + .005, font=dict(color=INK, size=11), **base_)]

                        f_m.frames = [go.Frame(name=str(k), data=dyn(k), traces=[2, 3, 4, 5, 7, 9, 10, 11, 12, 15, 16],
                                               layout=dict(annotations=anns(k))) for k in fidx]
                        span_ = max(float(np.ptp(lat_all)) * 1.6, float(np.ptp(lng_all)) * math.cos(math.radians(c_lat)) * 1.1, 0.002)
                        zoom_ = float(np.clip(math.log2(360 / span_) - 1.2, 8, 16))
                        if tiles:
                            map_cfg = dict(style="white-bg", layers=[dict(sourcetype="raster", source=tiles["urls"], below="traces",
                                                                          sourceattribution=tiles["attr"], maxzoom=tiles["maxzoom"])])
                        else:
                            map_cfg = dict(style="white-bg")
                        dur = lambda sp: max(30, int(stepf * 10 / sp * 1000))  # noqa: E731
                        play = lambda sp: dict(label=f"▶ ×{sp}", method="animate",  # noqa: E731
                                               args=[None, dict(frame=dict(duration=dur(sp), redraw=True), transition=dict(duration=0),
                                                                fromcurrent=True, mode="immediate")])
                        plot_layout(f_m, 980, legend=False)
                        alt_lo, alt_hi = float(np.nanmin(prof_y)), float(np.nanmax(prof_y))
                        f_m.update_layout(
                            map=dict(**map_cfg, center=dict(lat=c_lat, lon=c_lng), zoom=zoom_),
                            margin=dict(l=8, r=8, t=8, b=120), annotations=anns(k0),
                            updatemenus=[dict(type="buttons", direction="left", x=0, y=-0.035, xanchor="left", yanchor="top", showactive=False,
                                              bgcolor=SURFACE2, bordercolor=LINE, font=dict(color=INK, size=12), pad=dict(r=4, t=0),
                                              buttons=[play(30), play(60), play(120),
                                                       dict(label="⏸", method="animate",
                                                            args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
                            sliders=[dict(active=fidx.index(k0), x=0, len=1, y=-0.075, yanchor="top", pad=dict(t=0, b=0),
                                          bgcolor=SURFACE2, bordercolor=LINE, activebgcolor=GOLD, font=dict(color=MUTED, size=10),
                                          currentvalue=dict(visible=False), tickcolor=MUTED, ticklen=0, minorticklen=0,
                                          steps=[dict(method="animate", label=hms(R["T"][k]) if i % max(1, len(fidx) // 6) == 0 else "",
                                                      args=[[str(k)], dict(frame=dict(duration=0, redraw=True), mode="immediate",
                                                                           transition=dict(duration=0))]) for i, k in enumerate(fidx)])])
                        f_m.update_yaxes(ticksuffix=" min", zeroline=True, zerolinecolor=MUTED, row=2, col=1)
                        f_m.update_xaxes(ticksuffix=" km", row=2, col=1)
                        f_m.update_yaxes(range=[alt_lo - 40, alt_hi + 90], ticksuffix=" m", row=3, col=1)
                        f_m.update_xaxes(ticksuffix=" km", range=[0, float(prof_x[-1]) * 1.01], row=3, col=1)
                        f_m.update_yaxes(ticksuffix=" m", row=4, col=1)
                        f_m.update_xaxes(ticksuffix=" h", row=4, col=1)
                        st.markdown('<span class="note">Pulsa ▶ (×30, ×60 o ×120 la velocidad real) o arrastra la barra. Debajo del mapa: diferencia '
                                    'B − A a lo largo de la ruta, perfil con la posición de cada una y D+ acumulado frente al tiempo.</span>',
                                    unsafe_allow_html=True)
                        st.plotly_chart(f_m, width="stretch", theme=None, config={"scrollZoom": True})
                    else:
                        # ── Vista 3D (MapLibre GL JS, relieve real) ──
                        sub_k = np.unique(np.linspace(0, Tn - 1, min(Tn, 1800)).astype(int))
                        tri = lambda v: [None if not np.isfinite(x) else round(float(x), 5) for x in v]  # noqa: E731
                        payload = dict(
                            trackA=[[round(float(a), 5), round(float(b), 5)] for a, b in zip(sa_["lng"], sa_["lat"])],
                            trackB=[[round(float(a), 5), round(float(b), 5)] for a, b in zip(sb_["lng"], sb_["lat"])],
                            T=[int(x) for x in R["T"][sub_k]],
                            latA=tri(R["latA"][sub_k]), lngA=tri(R["lngA"][sub_k]), latB=tri(R["latB"][sub_k]), lngB=tri(R["lngB"][sub_k]),
                            posA=[round(float(x) / 1000, 3) for x in R["posA"][sub_k]], posB=[round(float(x) / 1000, 3) for x in R["posB"][sub_k]],
                            dpA=[int(x) for x in R["dpA"][sub_k]], dpB=[int(x) for x in R["dpB"][sub_k]],
                            gap=[round(race_gap(R, int(k))[1], 1) for k in sub_k], dd=[round(race_gap(R, int(k))[0]) for k in sub_k],
                            endA=float(R["endA"]), endB=float(R["endB"]),
                            profX=[round(float(x), 3) for x in prof_x], profY=[round(float(y)) for y in prof_y],
                            k0=int(np.searchsorted(R["T"][sub_k], R["T"][k_t])) if k_t < Tn - 1 else 0,
                            center=[c_lng, c_lat],
                            bounds=[[float(np.min(lng_all)), float(np.min(lat_all))], [float(np.max(lng_all)), float(np.max(lat_all))]],
                            base=tiles, terrain=TERRAIN_TILES,
                            col=dict(A=GOLD, B=GLACIER, ink=INK, muted=MUTED, line=LINE, surface=SURFACE, surface2=SURFACE2, bg=BG,
                                     green=GREEN, red=RED, onA=on(GOLD), onB=on(GLACIER)),
                        )
                        st.markdown('<span class="note">Vista 3D con relieve real: arrastra con el botón derecho (o dos dedos) para inclinar y girar. '
                                    'Si no ves el mapa (navegador sin WebGL o red que bloquea los mapas), vuelve a 2D.</span>',
                                    unsafe_allow_html=True)
                        html3d = MAP3D_HTML.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
                        if hasattr(st, "iframe"):
                            st.iframe(html3d, height=800)
                        else:                                  # Streamlit antiguo
                            components.html(html3d, height=800)

                # Lectura de la carrera
                lec = []
                both_k = R["T"] <= min(R["endA"], R["endB"])
                dd_all = (R["posB"] - R["posA"])[both_k]
                if len(dd_all):
                    pb_, pa_ = float((dd_all > 5).mean() * 100), float((dd_all < -5).mean() * 100)
                    lec.append(f"B fue por delante el {fnum(pb_)} % del tiempo y A el {fnum(pa_)} %"
                               + (f" (el resto, prácticamente juntas)." if pb_ + pa_ < 97 else "."))
                iB, iA = int(np.argmin(R["dT"])), int(np.argmax(R["dT"]))
                if R["dT"][iB] < -5:
                    lec.append(f"Máxima ventaja de B: {mmss(-R['dT'][iB])} min en el km {fnum(R['dA'][iB] / 1000, 1)} ({fnum(R['altA'][iB])} m).")
                if R["dT"][iA] > 5:
                    lec.append(f"Máxima ventaja de A: {mmss(R['dT'][iA])} min en el km {fnum(R['dA'][iA] / 1000, 1)} ({fnum(R['altA'][iA])} m).")
                sg_ = np.sign(R["dT"])
                sg_[np.abs(R["dT"]) < 10] = 0                       # ±10 s: empate (evita falsos adelantamientos)
                nz = np.flatnonzero(sg_)
                if len(nz):
                    chg = nz[1:][np.diff(sg_[nz]) != 0]
                    if len(chg):
                        lec.append(f"{len(chg)} adelantamiento{'s' if len(chg) != 1 else ''}: en el km "
                                   + ", ".join(fnum(R["dA"][i] / 1000, 1) for i in chg[:6]) + ".")
                    else:
                        lec.append("No hubo adelantamientos: " + ("B" if sg_[nz[-1]] < 0 else "A") + " fue por delante desde el principio.")
                segs_r = find_segments(df_a, amp)
                if segs_r:
                    ch_ = [(float(np.interp(d1, R["dA"], R["dT"]) - np.interp(d0, R["dA"], R["dT"])), d0, d1) for d0, d1 in segs_r]
                    big_r = max(ch_, key=lambda x: abs(x[0]))
                    a0_, a1_ = np.interp([big_r[1], big_r[2]], R["dA"], R["altA"])
                    lec.append(f"Donde más se abrió la diferencia: {'subida' if a1_ > a0_ else 'bajada'} del km {fnum(big_r[1] / 1000, 1)} al "
                               f"{fnum(big_r[2] / 1000, 1)} ({fnum(a0_)} → {fnum(a1_)} m), {'B gana' if big_r[0] < 0 else 'A gana'} "
                               f"{mmss(abs(big_r[0]))} min.")
                st.markdown("\n".join(f"- {x}" for x in lec))

            # ── Lectura automática ──
            ver = []
            if ra["secs"] and rb["secs"]:
                dmv = rb["secs"] - ra["secs"]
                pct = dmv / ra["secs"] * 100
                txt = (f"En movimiento, B fue {mmss(abs(dmv))} min {'más rápida' if dmv < 0 else 'más lenta'} que A ({fnum(abs(pct), 1)} %)"
                       if abs(dmv) >= 30 else "En movimiento, las dos tardaron prácticamente lo mismo")
                if pd.notna(ra["hr_avg"]) and pd.notna(rb["hr_avg"]):
                    dh = rb["hr_avg"] - ra["hr_avg"]
                    txt += f", con {fnum(abs(dh))} ppm {'menos' if dh < 0 else 'más'} de FC media" if abs(dh) >= 1 else ", con la misma FC media"
                    va_, vb_ = ra["km"] / ra["secs"], rb["km"] / rb["secs"]
                    eff = ((vb_ / rb["hr_avg"]) / (va_ / ra["hr_avg"]) - 1) * 100
                    if abs(eff) >= 1:
                        txt += f". Velocidad por pulsación {fnum(abs(eff), 1)} % {'mejor' if eff > 0 else 'peor'} en B"
                ver.append(txt + ".")
            if seg_rows:
                big = SG.loc[SG["diff"].abs().idxmax()]
                ver.append(f"La mayor diferencia está en el tramo {int(big['n'])} ({'subida' if big['up'] else 'bajada'} "
                           f"{fnum(big['a0'])} → {fnum(big['a1'])} m): B {mmss(abs(big['diff']))} min "
                           f"{'más rápida' if big['diff'] < 0 else 'más lenta'}.")
                su, ba_ = SG.loc[SG["up"], "diff"].sum(), SG.loc[~SG["up"], "diff"].sum()
                ver.append(f"En las subidas B {'gana' if su < 0 else 'pierde'} {mmss(abs(su))} min y en las bajadas "
                           f"{'gana' if ba_ < 0 else 'pierde'} {mmss(abs(ba_))} min.")
            else:
                up_b = bt[bt["Pendiente"].isin(["10/20 %", "20/30 %"]) & (bt["Km|A"] >= .3) & (bt["Km|B"] >= .3)]
                if len(up_b) and up_b["Δ m/h"].notna().any():
                    r_ = up_b.loc[up_b["Δ m/h"].abs().idxmax()]
                    ver.append(f"En las rampas del {r_['Pendiente']}, B sube a {fnum(r_['VAM / bajada|B'])} m/h frente a "
                               f"{fnum(r_['VAM / bajada|A'])} m/h de A.")
            if abs(stop_b - stop_a) >= 60:
                ver.append(f"Tiempo parado: {mmss(stop_a)} min en A y {mmss(stop_b)} min en B.")
            st.subheader("Qué se ve")
            st.markdown("\n".join(f"- {x}" for x in ver[:5]) or "- Sin diferencias destacables.")

            if (ra.get("device") or "") != (rb.get("device") or "") and ra.get("device") and rb.get("device"):
                notes_.insert(0, f"Cambia el reloj ({str(ra['device']).replace('SUUNTO ', '')} en A, {str(rb['device']).replace('SUUNTO ', '')} en B): "
                                 "la FC de muñeca y el GPS pueden variar algo entre relojes, y la cadencia no es comparable.")
            for lab_, r_ in (("A", ra), ("B", rb)):
                if r_["dp"] > 0 and r_["dm"] > 0 and abs(r_["dp"] - r_["dm"]) / max(r_["dp"], r_["dm"]) > .07:
                    notes_.append(f"En {lab_} el D+ ({fnum(r_['dp'])} m) y el D− ({fnum(r_['dm'])} m) difieren más de un 7 %: "
                                  "puede ser una variante de la ruta o un error de altitud.")
            for lab_, d_ in (("A", df_a), ("B", df_b)):
                hr_ = d_["hr"]
                if hr_.notna().sum() > 300:
                    jumps = int((hr_.diff(5).abs() > 30).sum())
                    desc = d_["alt_s"].diff(30) < -4
                    hi_ = (hr_ >= hr_.quantile(.98)) & desc
                    run_ = hi_.groupby((~hi_).cumsum()).sum().max() if hi_.any() else 0
                    if jumps > 5 or run_ >= 60:
                        notes_.append(f"La FC de {lab_} tiene saltos bruscos o tramos a FC máxima bajando: puede ser un error del sensor.")
            if do_seg and not sim_ab:
                notes_.append("Sin GPS, los tramos de B se sitúan por distancia y altitud: tómalo como aproximado.")
            st.subheader("A tener en cuenta")
            st.markdown("\n".join(f"- {x}" for x in notes_) if notes_ else "- Nada especial: datos completos y mismo reloj.")
