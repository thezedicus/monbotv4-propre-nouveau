#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  bce_dashboard.py — Dashboard BCE · Décisions basées sur les news           ║
║  Remplace tous les anciens dashboards du projet                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  COMMANDE MAC :                                                              ║
║    python3 -m streamlit run bce_dashboard.py                                ║
║                                                                              ║
║  INSTALLATION :                                                              ║
║    pip3 install streamlit plotly yfinance requests pandas numpy feedparser  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys, os, time, json, math, warnings, re
from datetime import datetime, date, timedelta
from pathlib  import Path
from typing   import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

# ── Dépendances obligatoires ──────────────────────────────────────────────────
try:
    import streamlit as st
except ImportError:
    print("pip3 install streamlit"); sys.exit(1)

try:
    import plotly.graph_objects as go
    from   plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

try:
    import pandas as pd
    import numpy  as np
except ImportError:
    st.error("pip3 install pandas numpy"); st.stop()

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

try:
    import requests
    REQ_OK = True
except ImportError:
    REQ_OK = False

try:
    import feedparser
    FP_OK = True
except ImportError:
    FP_OK = False

# ── Modules locaux ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
try:
    from bce_engine import (
        BCEDatabase, BCEAPI, AnalyseurTendancesBCE, RapportBCE
    )
    ENGINE_OK = True
except ImportError:
    ENGINE_OK = False

try:
    from orchestrator import (
        technical_score, macro_score, news_score,
        compute_decision, get_indices_data, BCE_INDICES_MAP,
        BULL_WORDS, BEAR_WORDS
    )
    ORCH_OK = True
except ImportError:
    ORCH_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG STREAMLIT
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title = "BCE · Décisions Marché",
    page_icon  = "🏦",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
.stApp { background:#000 !important; font-family:Inter,-apple-system,sans-serif }
.stApp > header { background:rgba(0,0,0,.94) !important }
[data-testid="stSidebar"] { background:#111 !important; border-right:.5px solid #222 }
[data-testid="stMetric"] {
    background:#111 !important; border-radius:14px !important;
    padding:14px !important; border:.5px solid #222 !important;
}
[data-testid="stMetricLabel"] { color:rgba(255,255,255,.45) !important; font-size:11px !important }
[data-testid="stMetricValue"] { color:#fff !important; font-weight:700 !important }
[data-testid="stMetricDelta"] { font-size:12px !important }
.stTabs [data-baseweb="tab-list"] {
    background:#111 !important; border-radius:14px; padding:5px; gap:3px;
}
.stTabs [data-baseweb="tab"] {
    color:rgba(255,255,255,.45) !important; border-radius:10px !important;
    font-weight:500 !important; font-size:13px !important;
}
.stTabs [aria-selected="true"] {
    background:#1a1a1a !important; color:#fff !important;
}
.stButton > button {
    background:#0a84ff !important; color:#fff !important;
    border-radius:12px !important; border:none !important;
    font-weight:600 !important; padding:9px 22px !important;
    font-size:13px !important;
}
.stButton > button:hover { opacity:.85 !important }
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div {
    background:#111 !important; border-color:#333 !important; color:#fff !important;
}
.stSlider > div { color:#fff !important }
div[data-testid="stExpander"] {
    background:#111 !important; border:.5px solid #222 !important; border-radius:12px !important;
}
p, h1, h2, h3, h4, li, label, span, div { color:#fff !important }
.stDataFrame { font-size:.84em !important }
::-webkit-scrollbar { width:5px }
::-webkit-scrollbar-thumb { background:#333; border-radius:3px }
</style>
""", unsafe_allow_html=True)

# ── Constantes visuelles ──────────────────────────────────────────────────────
C = {
    "buy":     "#30d158",
    "sell":    "#ff453a",
    "wait":    "#ff9f0a",
    "blue":    "#0a84ff",
    "purple":  "#bf5af2",
    "teal":    "#64d2ff",
    "sep":     "#222222",
    "card":    "#111111",
    "card2":   "#1a1a1a",
}
DEC_COLOR = {"ACHETER": C["buy"], "VENDRE": C["sell"], "ATTENDRE": C["wait"]}
DEC_ICON  = {"ACHETER": "🚀", "VENDRE": "⬇", "ATTENDRE": "⏸"}
CHART     = dict(
    template="plotly_dark", paper_bgcolor="#000", plot_bgcolor="#111",
    margin=dict(l=0,r=0,t=36,b=0),
    font=dict(family="Inter,system-ui", color="#ffffff", size=11),
    hovermode="x unified", xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.02, font_size=11),
    xaxis=dict(gridcolor="#1a1a1a"), yaxis=dict(gridcolor="#1a1a1a"),
)

# ── Indices BCE ───────────────────────────────────────────────────────────────
INDICES = {
    "^STOXX50E": "Euro Stoxx 50",
    "^FCHI":     "CAC 40",
    "^GDAXI":    "DAX 40",
    "^IBEX":     "IBEX 35",
    "^AEX":      "AEX",
    "EURUSD=X":  "EUR/USD",
    "EURGBP=X":  "EUR/GBP",
    "BZ=F":      "Brent",
    "NG=F":      "Gaz naturel",
}

# ── Sources RSS BCE ───────────────────────────────────────────────────────────
RSS_SOURCES = {
    "BCE Press":    "https://www.ecb.europa.eu/rss/press.html",
    "Reuters EU":   "https://feeds.reuters.com/reuters/businessNews",
    "Les Echos":    "https://www.lesechos.fr/feeds/rss/finance-marches.xml",
    "Le Monde Éco": "https://www.lemonde.fr/economie/rss_full.xml",
    "Yahoo Finance":"https://feeds.finance.yahoo.com/rss/2.0/headline?s=^STOXX50E&region=FR",
    "FT Markets":   "https://www.ft.com/rss/home/europe",
}

# ══════════════════════════════════════════════════════════════════════════════
# §1  HELPERS UI
# ══════════════════════════════════════════════════════════════════════════════

def kpi(label: str, val: str, sub: str = "", color: str = "#fff") -> str:
    return f"""
    <div style="background:{C['card']};border-radius:14px;padding:14px 16px;
    border:.5px solid {C['sep']};margin-bottom:8px">
      <div style="font-size:11px;color:rgba(255,255,255,.4);text-transform:uppercase;
      letter-spacing:.6px;margin-bottom:5px">{label}</div>
      <div style="font-size:22px;font-weight:700;color:{color};
      letter-spacing:-.5px;font-variant-numeric:tabular-nums">{val}</div>
      {"" if not sub else f'<div style="font-size:11px;color:rgba(255,255,255,.35);margin-top:4px">{sub}</div>'}
    </div>"""

def badge(txt: str, color: str, size: int = 13) -> str:
    return (f'<span style="background:{color}20;color:{color};font-size:{size}px;'
            f'font-weight:700;padding:4px 12px;border-radius:20px;'
            f'border:.5px solid {color}40">{txt}</span>')

def decision_banner(dec: str, conf: float, score: float, news_sent: str) -> None:
    dc   = DEC_COLOR.get(dec, C["wait"])
    icon = DEC_ICON.get(dec, "—")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{C['card']},{C['card2']});
    border-radius:20px;padding:24px 28px;margin-bottom:20px;
    border:.5px solid {C['sep']};border-left:5px solid {dc}">
      <div style="font-size:11px;color:rgba(255,255,255,.4);text-transform:uppercase;
      letter-spacing:.9px;margin-bottom:10px">Décision algorithmique — BCE Zone Euro</div>
      <div style="display:flex;align-items:flex-start;
      justify-content:space-between;flex-wrap:wrap;gap:16px">
        <div>
          <div style="font-size:48px;font-weight:800;color:{dc};
          letter-spacing:-2px;line-height:1">{icon} {dec}</div>
          <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap">
            {badge(f"Score {score:+.2f}", dc)}
            {badge(f"Confiance {conf:.0f}%", C['blue'])}
            {badge(f"News : {news_sent}", C['teal'])}
            {badge(datetime.utcnow().strftime("%H:%M UTC"), "rgba(255,255,255,.3)")}
          </div>
        </div>
        <div style="text-align:right;min-width:180px">
          <div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:8px">
            Niveau de confiance</div>
          <div style="background:{C['sep']};border-radius:6px;
          height:10px;overflow:hidden;width:180px;margin-bottom:4px">
            <div style="width:{min(conf,100):.0f}%;height:100%;
            background:{dc};border-radius:6px;
            transition:width 1s ease"></div>
          </div>
          <div style="font-size:12px;color:{dc};font-weight:700">{conf:.0f}%</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

def score_row(label: str, val: float, weight: str, details: str = "") -> None:
    pct = (val + 1) / 2 * 100
    c   = C["buy"] if val > 0.15 else C["sell"] if val < -0.15 else C["wait"]
    ic  = "↑" if val > 0.15 else "↓" if val < -0.15 else "—"
    st.markdown(f"""
    <div style="margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;
      align-items:center;margin-bottom:6px">
        <div>
          <span style="font-size:14px;font-weight:600">{label}</span>
          <span style="font-size:11px;color:rgba(255,255,255,.35);
          margin-left:8px">{weight}</span>
        </div>
        <span style="font-size:18px;font-weight:800;
        color:{c};font-variant-numeric:tabular-nums">{ic} {val:+.3f}</span>
      </div>
      <div style="background:{C['sep']};border-radius:5px;height:7px;overflow:hidden">
        <div style="width:{pct:.0f}%;height:100%;background:{c};
        border-radius:5px"></div>
      </div>
      {"" if not details else f'<div style="font-size:11px;color:rgba(255,255,255,.35);margin-top:4px">{details}</div>'}
    </div>""", unsafe_allow_html=True)

def news_card(art: Dict) -> None:
    sent = art.get("sentiment", "⚪ Neutre")
    cc   = C["buy"] if "Haussier" in sent else C["sell"] if "Baissier" in sent else "rgba(255,255,255,.3)"
    bce  = art.get("pertinent", False)
    st.markdown(f"""
    <a href="{art.get('lien','#')}" target="_blank" style="text-decoration:none">
    <div style="background:{C['card']};border-radius:13px;padding:13px 16px;
    margin-bottom:8px;border:.5px solid {C['sep']};border-left:3px solid {cc};
    transition:border-color .2s">
      <div style="font-size:13px;font-weight:500;line-height:1.45;
      color:#fff;margin-bottom:6px">{art.get('titre','')[:100]}</div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <span style="font-size:11px;color:rgba(255,255,255,.35)">
          {art.get('source','')} · {art.get('date','')[:16]}</span>
        <span style="font-size:11px;font-weight:600;color:{cc}">{sent}</span>
        {"<span style='font-size:10px;background:#0a84ff18;color:#0a84ff;padding:2px 7px;border-radius:8px'>📍 BCE</span>" if bce else ""}
      </div>
    </div></a>""", unsafe_allow_html=True)

def prob_bar(b: float, s: float, h: float) -> None:
    st.markdown(f"""
    <div style="margin:12px 0">
      <div style="display:flex;height:12px;border-radius:6px;overflow:hidden;margin-bottom:8px">
        <div style="width:{b:.0f}%;background:{C['buy']}"></div>
        <div style="width:{s:.0f}%;background:{C['wait']}"></div>
        <div style="width:{h:.0f}%;background:{C['sell']}"></div>
      </div>
      <div style="display:flex;justify-content:space-between;
      font-size:12px;font-weight:600">
        <span style="color:{C['buy']}">↓ Baisse {b:.0f}%</span>
        <span style="color:{C['wait']}">— Stable {s:.0f}%</span>
        <span style="color:{C['sell']}">↑ Hausse {h:.0f}%</span>
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# §2  CHARGEMENT DONNÉES — CACHE STREAMLIT
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def load_rapport_bce() -> Dict:
    if not ENGINE_OK:
        return {}
    try:
        return RapportBCE().generer()
    except Exception as e:
        return {"erreur": str(e)}


@st.cache_data(ttl=60, show_spinner=False)
def load_decision() -> Tuple:
    if not ORCH_OK:
        return "ATTENDRE", 50.0, {"technique": 0, "macro": 0, "news": 0, "total": 0}
    try:
        return compute_decision()
    except Exception:
        return "ATTENDRE", 50.0, {"technique": 0, "macro": 0, "news": 0, "total": 0}


@st.cache_data(ttl=30, show_spinner=False)
def load_prix_live(symbols: List[str]) -> Dict:
    if not YF_OK:
        return {}
    try:
        raw = yf.download(
            symbols if len(symbols) > 1 else symbols[0],
            period="5d", interval="1d", progress=False,
            auto_adjust=True,
            group_by="ticker" if len(symbols) > 1 else None,
            timeout=15,
        )
        if raw is None or raw.empty:
            return {}
        result = {}
        for sym in symbols:
            try:
                s = (raw[sym] if len(symbols) > 1
                       and isinstance(raw.columns, pd.MultiIndex)
                       and sym in raw.columns.get_level_values(0)
                       else raw)
                close = float(s["Close"].dropna().iloc[-1])
                prev  = float(s["Close"].dropna().iloc[-2]) if len(s) > 1 else close
                chg   = (close - prev) / prev * 100 if prev else 0.0
                result[sym] = {
                    "prix":    round(close, 4),
                    "var_pct": round(chg, 3),
                    "haut":    round(float(s["High"].dropna().iloc[-1]), 4),
                    "bas":     round(float(s["Low"].dropna().iloc[-1]), 4),
                }
            except Exception:
                pass
        return result
    except Exception:
        return {}


@st.cache_data(ttl=252, show_spinner=False)
def load_historique(symbol: str, jours: int = 252) -> "pd.DataFrame":
    if not YF_OK:
        return pd.DataFrame()
    try:
        raw = yf.download(
            symbol, period=f"{max(1, jours // 252)}y",
            interval="1d", progress=False, auto_adjust=True, timeout=15,
        )
        if raw is None or raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.droplevel(1)
        raw.columns = [c.title() for c in raw.columns]
        return raw[[c for c in ["Open","High","Low","Close","Volume"]
                     if c in raw.columns]].dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def load_news_bce() -> List[Dict]:
    """Charge les actualités BCE depuis tous les flux RSS."""
    if not FP_OK:
        return []

    BCE_MOTS = ["bce","ecb","banque centrale","taux directeur","euribor",
                 "zone euro","lagarde","politique monétaire","inflation",
                 "resserrement","assouplissement","taux de dépôt",
                 "rate decision","rate cut","rate hike"]

    articles = []
    for source, url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                titre = (entry.get("title","") or "").strip()
                if not titre:
                    continue
                tl     = titre.lower()
                resume = (entry.get("summary","") or entry.get("description","") or "")[:200]
                bull   = sum(1 for w in BULL_WORDS if w in tl)
                bear   = sum(1 for w in BEAR_WORDS if w in tl)
                score  = bull - bear
                bce    = any(m in tl for m in BCE_MOTS)
                sent   = ("🟢 Haussier" if score > 0 else
                           "🔴 Baissier" if score < 0 else "⚪ Neutre")
                articles.append({
                    "titre":    titre,
                    "source":   source,
                    "lien":     entry.get("link","#"),
                    "date":     entry.get("published","")[:25],
                    "sentiment":sent,
                    "score":    score,
                    "pertinent":bce,
                    "resume":   resume,
                })
            time.sleep(0.2)
        except Exception:
            pass

    # Trier : articles BCE en premier, puis par score absolu
    articles.sort(key=lambda x: (x["pertinent"], abs(x["score"])), reverse=True)
    return articles


@st.cache_data(ttl=600, show_spinner=False)
def load_fear_greed() -> Dict:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=7)
        if r.status_code == 200:
            data = r.json()["data"]
            return {
                "value":   int(data[0]["value"]),
                "label":   data[0]["value_classification"],
                "history": [int(d["value"]) for d in data],
            }
    except Exception:
        pass
    return {"value": 50, "label": "Neutral", "history": [50]*7}


# ══════════════════════════════════════════════════════════════════════════════
# §3  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def sidebar() -> Dict:
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:16px 0 22px">
          <div style="font-size:32px">🏦</div>
          <div style="font-size:17px;font-weight:800;margin-top:6px;
          letter-spacing:-.3px">BCE Dashboard</div>
          <div style="font-size:11px;color:rgba(255,255,255,.3);margin-top:4px">
            Market Oracle · Zone Euro</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("##### 📊 Indice principal")
        choix  = st.selectbox("", list(INDICES.keys()),
                               format_func=lambda x: INDICES.get(x,x))
        symbol = choix

        st.markdown("##### 🌐 Watchlist")
        watchlist = st.multiselect(
            "",
            options=list(INDICES.keys()),
            default=["^STOXX50E","^FCHI","^GDAXI","EURUSD=X","BZ=F"],
            format_func=lambda x: INDICES.get(x,x),
        )

        st.markdown("##### ⏱️ Historique")
        jours = st.select_slider("", [30,60,90,126,252,504], value=252)

        st.markdown("##### 💶 Capital")
        capital = st.number_input("", value=10_000, step=1_000, min_value=100)

        st.markdown("---")
        if st.button("🔄 Actualiser", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # Statut des modules
        modules = [
            ("bce_engine", ENGINE_OK),
            ("orchestrator", ORCH_OK),
            ("yfinance", YF_OK),
            ("feedparser", FP_OK),
        ]
        st.markdown("")
        for name, ok in modules:
            col_s = "#30d158" if ok else "#ff453a"
            st.markdown(
                f'<div style="font-size:10px;color:{col_s};margin-bottom:2px">'
                f'{"✅" if ok else "❌"} {name}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div style="font-size:10px;color:rgba(255,255,255,.2);margin-top:8px">'
            f'{datetime.utcnow():%Y-%m-%d %H:%M} UTC</div>',
            unsafe_allow_html=True,
        )

    return dict(symbol=symbol, watchlist=watchlist or ["^STOXX50E"],
                jours=jours, capital=capital)


# ══════════════════════════════════════════════════════════════════════════════
# §4  ONGLET 1 — DÉCISION EN DIRECT
# ══════════════════════════════════════════════════════════════════════════════

def tab_decision(cfg: Dict) -> None:

    # ── Décision + scores ─────────────────────────────────────────────────────
    with st.spinner("Calcul de la décision..."):
        dec, conf, scores = load_decision()
        news_data         = load_news_bce()
        fg                = load_fear_greed()

    # Score sentiment news pour le badge
    news_scores = [a["score"] for a in news_data]
    avg_ns      = sum(news_scores) / len(news_scores) if news_scores else 0
    ns_label    = "🟢 Positif" if avg_ns > 0.2 else "🔴 Négatif" if avg_ns < -0.2 else "⚪ Neutre"

    # Bannière décision principale
    decision_banner(dec, conf, scores.get("total", 0), ns_label)

    # ── 3 KPIs Fear & Greed + VIX ────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    fg_v  = fg.get("value", 50)
    fg_c  = C["buy"] if fg_v > 60 else C["sell"] if fg_v < 40 else C["wait"]
    k1.markdown(kpi("Fear & Greed",   f"{fg_v}/100", fg.get("label",""), fg_c), unsafe_allow_html=True)
    k2.markdown(kpi("Score technique", f"{scores.get('technique',0):+.3f}",
                     "RSI · MACD · EMA · ADX",
                     C["buy"] if scores.get("technique",0) > 0 else C["sell"]),
                 unsafe_allow_html=True)
    k3.markdown(kpi("Score macro",     f"{scores.get('macro',0):+.3f}",
                     "BCE · VIX · Euribor · Spread",
                     C["buy"] if scores.get("macro",0) > 0 else C["sell"]),
                 unsafe_allow_html=True)
    k4.markdown(kpi("Score news BCE",  f"{scores.get('news',0):+.3f}",
                     f"{len(news_data)} articles analysés",
                     C["buy"] if scores.get("news",0) > 0 else C["sell"]),
                 unsafe_allow_html=True)

    st.markdown("")

    # ── Scores détaillés ──────────────────────────────────────────────────────
    col_scores, col_news = st.columns([1, 1])

    with col_scores:
        st.markdown("##### Décomposition des scores")
        score_row("Score Technique",  scores.get("technique",0), "40%",
                   "RSI · MACD · EMA 20/50/200 · ADX · SuperTrend")
        score_row("Score Macro BCE",  scores.get("macro",0),     "40%",
                   "Euribor · BCE SDMX · VIX · Fear&Greed · Spreads")
        score_row("Score Actualités", scores.get("news",0),      "20%",
                   "RSS Reuters · Les Echos · BCE · Yahoo Finance")

        # Niveaux de trading si décision forte
        if dec in ("ACHETER","VENDRE") and ORCH_OK:
            st.markdown("##### Niveaux recommandés")
            sym    = cfg.get("symbol","^STOXX50E")
            prix_d = load_prix_live([sym])
            if prix_d.get(sym):
                px = prix_d[sym]["prix"]
                # ATR approximatif (2% du prix)
                atr = px * 0.018
                if dec == "ACHETER":
                    stop = round(px - atr * 2, 4)
                    tp   = round(px + atr * 4, 4)
                    rr   = abs(tp - px) / max(abs(px - stop), 1e-9)
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(kpi("Stop Long",   f"{stop:,.4f}", "",   C["sell"]), unsafe_allow_html=True)
                    c2.markdown(kpi("TP Long",     f"{tp:,.4f}",   "",   C["buy"]),  unsafe_allow_html=True)
                    c3.markdown(kpi("R:R Ratio",   f"{rr:.2f}x",   "",   C["blue"]), unsafe_allow_html=True)
                else:
                    stop = round(px + atr * 2, 4)
                    tp   = round(px - atr * 4, 4)
                    rr   = abs(px - tp) / max(abs(stop - px), 1e-9)
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(kpi("Stop Short",  f"{stop:,.4f}", "",   C["sell"]), unsafe_allow_html=True)
                    c2.markdown(kpi("TP Short",    f"{tp:,.4f}",   "",   C["buy"]),  unsafe_allow_html=True)
                    c3.markdown(kpi("R:R Ratio",   f"{rr:.2f}x",   "",   C["blue"]), unsafe_allow_html=True)

    # ── News qui fondent la décision ──────────────────────────────────────────
    with col_news:
        st.markdown("##### 📰 News BCE qui fondent la décision")
        if not news_data:
            st.info("Installer feedparser : pip3 install feedparser")
        else:
            for art in news_data[:6]:
                news_card(art)

    # ── Graphique historique de l'indice ──────────────────────────────────────
    sym = cfg.get("symbol","^STOXX50E")
    df  = load_historique(sym, cfg.get("jours",252))

    if not df.empty and PLOTLY_OK:
        st.markdown(f"##### 📈 {INDICES.get(sym,sym)}")
        C_   = df["Close"]
        fig  = make_subplots(rows=2, cols=1, row_heights=[0.72,0.28],
                              shared_xaxes=True, vertical_spacing=0.03)

        # Candlesticks
        if "Open" in df.columns:
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=C_, name=sym,
                increasing_line_color=C["buy"],
                decreasing_line_color=C["sell"],
                increasing_fillcolor='rgba(48,209,88,0.18)',
                decreasing_fillcolor='rgba(255,69,58,0.18)',
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(x=df.index, y=C_, mode="lines",
                                      name=sym, line=dict(color=C["blue"],width=2)),
                           row=1, col=1)

        # EMAs
        for period, color, dash in [
            (20, C["wait"],   "dot"),
            (50, C["teal"],   "dash"),
            (200,C["purple"], "dashdot"),
        ]:
            if len(C_) > period:
                e = C_.ewm(span=period, adjust=False).mean()
                fig.add_trace(go.Scatter(x=df.index, y=e, mode="lines",
                                          name=f"EMA{period}", opacity=.75,
                                          line=dict(color=color, width=1.2, dash=dash)),
                               row=1, col=1)

        # Bollinger Bands
        bm = C_.rolling(20).mean()
        bs = C_.rolling(20).std(ddof=0)
        bu, bd = bm + 2*bs, bm - 2*bs
        fig.add_trace(go.Scatter(
            x=list(df.index)+list(df.index[::-1]),
            y=list(bu)+list(bd[::-1]),
            fill="toself", fillcolor='rgba(10,132,255,0.05)',
            line=dict(color="rgba(0,0,0,0)"), name="BB ±2σ",
        ), row=1, col=1)

        # Volume
        if "Volume" in df.columns:
            cv = [C["buy"] if float(C_.iloc[i]) >= float(C_.iloc[max(0,i-1)])
                   else C["sell"] for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                                  marker_color=cv, opacity=.45), row=2, col=1)

        fig.update_layout(**CHART, height=540)
        fig.update_yaxes(showgrid=True, gridcolor="#1a1a1a", gridwidth=.5)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# §5  ONGLET 2 — TENDANCES BCE
# ══════════════════════════════════════════════════════════════════════════════

def tab_tendances_bce() -> None:
    st.markdown("### 📈 Tendances BCE — Analyse complète")

    with st.spinner("Chargement..."):
        rapport = load_rapport_bce()

    if not rapport or "erreur" in rapport:
        st.error(f"bce_engine.py requis : {rapport.get('erreur','introuvable')}")
        return

    t   = rapport.get("tendances_bce", {})
    pr  = t.get("probabilites", {})
    cal = rapport.get("prochaine_reunion", {})
    sc  = DEC_COLOR.get(
        {"ACCOMMODANT":"ACHETER","RESTRICTIF":"VENDRE"}.get(t.get("stance",""),"ATTENDRE"),
        C["wait"]
    )

    # ── Bannière phase ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{C['card']},{C['card2']});
    border-radius:18px;padding:22px 26px;margin-bottom:20px;
    border:.5px solid {C['sep']};border-left:5px solid {sc}">
      <div style="font-size:11px;color:rgba(255,255,255,.4);text-transform:uppercase;
      letter-spacing:.9px;margin-bottom:10px">Phase du cycle monétaire BCE</div>
      <div style="font-size:28px;font-weight:800;color:{sc};margin-bottom:10px">
        {t.get('phase_cycle','N/A')}</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        {badge("Stance : "+t.get("stance","N/A"), sc)}
        {badge("Biais marchés : "+t.get("biais_marche","N/A"),
               C["buy"] if t.get("biais_marche","")=="HAUSSIER" else C["sell"] if t.get("biais_marche","")=="BAISSIER" else C["wait"])}
        {badge("Confiance : "+str(t.get("confiance_pct",0))+"%", C["blue"])}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── KPIs clés ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Taux dépôt BCE",  f"{t.get('taux_actuel',0):.2f}%",
                     f"Neutre estimé : {t.get('taux_neutre_estime',2.0):.2f}%", sc),
                 unsafe_allow_html=True)
    c2.markdown(kpi("Inflation HICP",  f"{t.get('inflation_hicp',0):.1f}%",
                     t.get("inflation_situation",""),
                     C["sell"] if (t.get("inflation_hicp",2) or 2) > 2.5 else C["buy"]),
                 unsafe_allow_html=True)
    c3.markdown(kpi("Taux réel",        f"{t.get('taux_reel',0):.2f}%",
                     t.get("taux_reel_situation",""),
                     C["buy"] if (t.get("taux_reel",0) or 0) > 0 else C["sell"]),
                 unsafe_allow_html=True)
    c4.markdown(kpi("Euribor 3M",       f"{t.get('euribor_3m',0):.3f}%",
                     "Taux interbancaire zone euro", C["teal"]),
                 unsafe_allow_html=True)

    # ── Probabilités + Prochain mouvement ─────────────────────────────────────
    st.markdown("##### 🎲 Prochaine décision BCE")
    col_p, col_d, col_cal = st.columns([2, 2, 1])

    with col_p:
        prob_bar(pr.get("baisse_pct",33), pr.get("stable_pct",34), pr.get("hausse_pct",33))

    pc = (C["buy"]  if t.get("prochain_mvt_prevu","") == "BAISSE" else
          C["sell"] if t.get("prochain_mvt_prevu","") == "HAUSSE" else C["wait"])
    with col_d:
        st.markdown(f"""
        <div style="background:{C['card']};border-radius:14px;padding:14px;
        border:.5px solid {pc}60;height:100%">
          <div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:6px">
            Mouvement attendu</div>
          <div style="font-size:24px;font-weight:800;color:{pc}">
            {t.get("prochain_mvt_prevu","?")} ({t.get("bps_prevu",0):+d}bps)</div>
          <div style="font-size:12px;color:rgba(255,255,255,.45);margin-top:6px">
            {t.get("tendance_recente","")}</div>
        </div>""", unsafe_allow_html=True)

    with col_cal:
        if cal:
            try:
                days = (datetime.strptime(cal.get("date_reunion","2099-01-01"),
                                           "%Y-%m-%d").date() - date.today()).days
                jj = f"J-{days}" if days > 0 else "Aujourd'hui"
            except Exception:
                jj = ""
            st.markdown(f"""
            <div style="background:{C['card']};border-radius:14px;padding:14px;
            border:.5px solid {C['blue']}40;text-align:center;height:100%">
              <div style="font-size:10px;color:rgba(255,255,255,.4);margin-bottom:6px">
                Prochaine réunion</div>
              <div style="font-size:16px;font-weight:700;color:{C['blue']}">
                {cal.get('date_reunion','N/A')}</div>
              <div style="font-size:28px;font-weight:800;margin-top:4px">{jj}</div>
            </div>""", unsafe_allow_html=True)

    # ── Graphique historique taux BCE ─────────────────────────────────────────
    if ENGINE_OK and PLOTLY_OK:
        st.markdown("##### 📊 Historique des décisions BCE (2022–2025)")
        hist  = AnalyseurTendancesBCE.HISTORIQUE_DECISIONS
        dates = [d["date"] for d in hist]
        taux  = [d["taux_depot"] for d in hist]
        bps_  = [d["bps"] for d in hist]
        decs  = [d["decision"] for d in hist]
        dc_   = [C["buy"] if b < 0 else C["sell"] if b > 0 else C["wait"] for b in bps_]

        fig = make_subplots(rows=2, cols=1, row_heights=[0.62,0.38],
                             shared_xaxes=True, vertical_spacing=0.05)
        fig.add_trace(go.Scatter(
            x=dates, y=taux, mode="lines+markers", name="Taux dépôt (%)",
            line=dict(color=C["blue"], width=2.5),
            marker=dict(color=dc_, size=11, line=dict(color="#000", width=1.5)),
        ), row=1, col=1)
        fig.add_hline(y=2.0, row=1, col=1, line_color=C["wait"],
                       line_dash="dash", line_width=1.2,
                       annotation_text="Taux neutre ~2%",
                       annotation_font_size=10)
        fig.add_hrect(y0=0, y1=2.0, row=1, col=1,
                       fillcolor='rgba(48,209,88,0.04)', line_width=0)
        fig.add_hrect(y0=2.0, y1=5, row=1, col=1,
                       fillcolor='rgba(255,69,58,0.04)', line_width=0)
        fig.add_trace(go.Bar(x=dates, y=bps_, name="Variation (bps)",
                              marker_color=dc_, opacity=.8), row=2, col=1)
        fig.update_layout(**CHART, height=440,
                           title="Cycle monétaire BCE — Taux directeurs & décisions")
        fig.update_yaxes(title_text="Taux (%)", row=1, col=1)
        fig.update_yaxes(title_text="bps",      row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)

    # Tableau récapitulatif
    st.markdown("##### 10 dernières décisions")
    rows = []
    for d in AnalyseurTendancesBCE.HISTORIQUE_DECISIONS[-10:][::-1]:
        rows.append({
            "Date":        d["date"],
            "Taux (%)":    f"{d['taux_depot']:.2f}",
            "Décision":    d["decision"],
            "Variation":   f"{d['bps']:+d} bps",
            "Contexte":    d.get("contexte",""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# §6  ONGLET 3 — NEWS & IMPACT
# ══════════════════════════════════════════════════════════════════════════════

def tab_news_impact() -> None:
    st.markdown("### 📰 News BCE & Impact sur les marchés")

    with st.spinner("Chargement des actualités..."):
        news    = load_news_bce()
        rapport = load_rapport_bce()

    col_n, col_i = st.columns([3, 2])

    # ── Actualités ────────────────────────────────────────────────────────────
    with col_n:
        if not news:
            st.info("pip3 install feedparser — nécessaire pour les actualités RSS")
        else:
            # Score global
            all_scores = [a["score"] for a in news]
            avg        = sum(all_scores) / len(all_scores) if all_scores else 0
            norm       = min(max((avg + 3) / 6 * 100, 0), 100)
            sent_c     = C["buy"] if norm > 60 else C["sell"] if norm < 40 else C["wait"]
            sent_l     = "HAUSSIER" if norm > 60 else "BAISSIER" if norm < 40 else "NEUTRE"

            k1, k2, k3 = st.columns(3)
            k1.markdown(kpi("Sentiment global", f"{norm:.0f}/100", sent_l, sent_c),
                         unsafe_allow_html=True)
            k2.markdown(kpi("Articles analysés", str(len(news)),
                              "Toutes sources"), unsafe_allow_html=True)
            bce_n = sum(1 for a in news if a.get("pertinent"))
            k3.markdown(kpi("Articles BCE", str(bce_n),
                              "Directement liés à la BCE", C["blue"]),
                         unsafe_allow_html=True)

            # Filtre
            filtre = st.selectbox("Filtrer",
                                    ["Tous","🟢 Haussier","🔴 Baissier","⚪ Neutre",
                                     "📍 BCE uniquement"])
            filtered = news
            if "Haussier" in filtre:  filtered = [a for a in news if "Haussier" in a["sentiment"]]
            elif "Baissier" in filtre:filtered = [a for a in news if "Baissier" in a["sentiment"]]
            elif "Neutre" in filtre:  filtered = [a for a in news if "Neutre"   in a["sentiment"]]
            elif "BCE" in filtre:     filtered = [a for a in news if a.get("pertinent")]

            st.markdown("##### Actualités")
            for art in filtered[:12]:
                news_card(art)

    # ── Impact marchés ────────────────────────────────────────────────────────
    with col_i:
        if rapport and "impact_marches" in rapport:
            i = rapport["impact_marches"]
            st.markdown("##### Impact prévu si décision BCE")
            prochain = i.get("prochain_mouvement","STABLE")
            bps      = i.get("bps_attendus",0)
            pc       = C["buy"] if prochain=="BAISSE" else C["sell"] if prochain=="HAUSSE" else C["wait"]

            st.markdown(f"""
            <div style="background:{C['card']};border-radius:13px;
            padding:13px 16px;border:.5px solid {pc}50;margin-bottom:14px">
              <div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:5px">
                Scénario analysé</div>
              <div style="font-size:20px;font-weight:800;color:{pc}">
                {prochain} ({bps:+d}bps)</div>
              <div style="font-size:12px;color:rgba(255,255,255,.4);margin-top:4px">
                Confiance : {i.get('confiance_pct',50)}%</div>
            </div>""", unsafe_allow_html=True)

            imp_j1 = i.get("impact_j1_attendu",{})

            # Indices
            st.markdown("**Indices (J+1)**")
            for idx, d in imp_j1.get("actions_zone_euro",{}).items():
                v  = d.get("impact_pct",0)
                cc = C["buy"] if v > 0 else C["sell"]
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                align-items:center;padding:9px 14px;margin-bottom:5px;
                background:{C['card']};border-radius:10px;
                border:.5px solid {cc}40">
                  <span style="font-size:13px">{idx}</span>
                  <span style="font-size:16px;font-weight:700;color:{cc}">
                    {"▲" if v>0 else "▼"} {abs(v):.1f}%</span>
                </div>""", unsafe_allow_html=True)

            # Secteurs
            st.markdown("**Secteurs**")
            for sec, d in list(imp_j1.get("secteurs",{}).items())[:4]:
                v  = d.get("impact_pct",0)
                cc = C["buy"] if v > 0 else C["sell"]
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                align-items:center;padding:7px 12px;margin-bottom:4px;
                background:{C['card']};border-radius:9px;
                border:.5px solid {cc}30">
                  <span style="font-size:12px">{sec}</span>
                  <span style="font-size:13px;font-weight:700;color:{cc}">
                    {"▲" if v>0 else "▼"} {abs(v):.1f}%</span>
                </div>""", unsafe_allow_html=True)

            # Risques
            for r in i.get("facteurs_risque",[])[:3]:
                st.markdown(f"""
                <div style="font-size:12px;padding:8px 12px;margin-bottom:4px;
                background:{C['card']};border-radius:9px;
                border:.5px solid {C['sep']}">{r}</div>""", unsafe_allow_html=True)

            # Horizon MT
            mt = i.get("horizon_3_6_mois",{})
            if mt:
                st.markdown("**Horizon 3-6 mois**")
                k1, k2 = st.columns(2)
                k1.markdown(kpi("Stoxx 50", mt.get("stoxx50_3m","N/A")),
                             unsafe_allow_html=True)
                k2.markdown(kpi("EUR/USD",  mt.get("eur_usd_3m","N/A")),
                             unsafe_allow_html=True)
                if mt.get("secteurs_privilegies"):
                    st.success("✅ " + " · ".join(mt["secteurs_privilegies"]))
                if mt.get("secteurs_eviter"):
                    st.error("⛔ " + " · ".join(mt["secteurs_eviter"]))
        else:
            st.info("bce_engine.py requis pour l'analyse d'impact")


# ══════════════════════════════════════════════════════════════════════════════
# §7  ONGLET 4 — SCREENER INDICES BCE
# ══════════════════════════════════════════════════════════════════════════════

def tab_screener(cfg: Dict) -> None:
    st.markdown("### 🔍 Screener — Indices Zone Euro")

    wl   = cfg.get("watchlist", list(INDICES.keys())[:5])
    prix = load_prix_live(wl)

    # Tableau prix
    if prix:
        rows = []
        for sym in wl:
            d   = prix.get(sym, {})
            if not d: continue
            v   = d.get("var_pct",0)
            nom = INDICES.get(sym, sym)
            rows.append({
                "Indice":  nom,
                "Symbole": sym,
                "Prix":    f"{d.get('prix',0):,.4f}",
                "Var%":    f"{v:+.3f}%",
                "Haut":    f"{d.get('haut',0):,.4f}",
                "Bas":     f"{d.get('bas',0):,.4f}",
            })
        if rows:
            st.dataframe(pd.DataFrame(rows).set_index("Symbole"),
                          use_container_width=True)

    # Graphique comparatif
    if PLOTLY_OK and len(wl) > 1:
        st.markdown("##### Performance comparative (base 100)")
        fig = go.Figure()
        palette = [C["blue"],C["buy"],C["wait"],C["purple"],C["teal"],
                    C["sell"],"#ffd60a","#ff375f"]
        for i, sym in enumerate(wl[:6]):
            df = load_historique(sym, cfg.get("jours",252))
            if df.empty: continue
            C_  = df["Close"]
            norm = C_ / C_.iloc[0] * 100 - 100
            fig.add_trace(go.Scatter(
                x=df.index, y=norm, mode="lines",
                name=INDICES.get(sym,sym)[:18],
                line=dict(color=palette[i % len(palette)], width=1.8),
            ))
        fig.add_hline(y=0, line_color="#333", line_dash="dash", opacity=.5)
        fig.update_layout(**CHART, height=360, yaxis_title="Return (%)")
        st.plotly_chart(fig, use_container_width=True)

    # Prix détaillés
    st.markdown("##### Graphique individuel")
    sym_choice = st.selectbox("", wl, format_func=lambda x: INDICES.get(x,x))
    df         = load_historique(sym_choice, cfg.get("jours",252))

    if not df.empty and PLOTLY_OK:
        C_ = df["Close"]
        fig= go.Figure()
        if "Open" in df.columns:
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=C_, name=sym_choice,
                increasing_line_color=C["buy"], decreasing_line_color=C["sell"],
                increasing_fillcolor='rgba(48,209,88,0.15)',
                decreasing_fillcolor='rgba(255,69,58,0.15)',
            ))
        else:
            fig.add_trace(go.Scatter(x=df.index, y=C_, mode="lines",
                                      name=sym_choice,
                                      line=dict(color=C["blue"],width=2)))
        for p, col, dash in [(20,C["wait"],"dot"),(50,C["teal"],"dash"),
                               (200,C["purple"],"dashdot")]:
            if len(C_) > p:
                fig.add_trace(go.Scatter(x=df.index,
                                          y=C_.ewm(span=p,adjust=False).mean(),
                                          mode="lines", name=f"EMA{p}", opacity=.7,
                                          line=dict(color=col,width=1,dash=dash)))
        fig.update_layout(**CHART, height=420,
                           title=f"{INDICES.get(sym_choice,sym_choice)} — {cfg.get('jours',252)}j")
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# §8  ONGLET 5 — BACKTEST STRATÉGIE BCE
# ══════════════════════════════════════════════════════════════════════════════

def tab_backtest(cfg: Dict) -> None:
    st.markdown("### 🔁 Backtest — Stratégie basée sur les décisions BCE")
    st.info(
        f"Règle : LONG après chaque **baisse** BCE · SHORT/Cash après chaque **hausse** BCE · "
        f"Capital : **€{cfg.get('capital',10_000):,}**"
    )

    if not ENGINE_OK:
        st.warning("bce_engine.py requis dans le même dossier")
        return

    sym = cfg.get("symbol","^STOXX50E")
    df  = load_historique(sym, 756)  # 3 ans

    if df is None or df.empty or len(df) < 60:
        st.warning("Données insuffisantes (min 60 barres requises)")
        return

    cap       = cfg.get("capital", 10_000)
    C_        = df["Close"].astype(float)
    df_bt     = pd.DataFrame(index=df.index)
    df_bt["close"]  = C_
    df_bt["signal"] = 0

    for i, dec in enumerate(AnalyseurTendancesBCE.HISTORIQUE_DECISIONS):
        try:
            decs = AnalyseurTendancesBCE.HISTORIQUE_DECISIONS
            dt   = pd.Timestamp(dec["date"])
            nxt  = pd.Timestamp(decs[i+1]["date"]) if i+1 < len(decs) else df.index[-1]
            sig  = 1 if dec["decision"]=="BAISSE" else -1 if dec["decision"]=="HAUSSE" else 0
            mask = (df_bt.index >= dt) & (df_bt.index < nxt)
            df_bt.loc[mask, "signal"] = sig
        except Exception:
            pass

    df_bt["ret"]    = C_.pct_change()
    df_bt["strat"]  = df_bt["signal"].shift(1) * df_bt["ret"]
    df_bt["cum_s"]  = (1 + df_bt["strat"].fillna(0)).cumprod() * cap
    df_bt["cum_bh"] = (1 + df_bt["ret"].fillna(0)).cumprod() * cap

    ret_s   = (df_bt["cum_s"].iloc[-1]  / cap - 1) * 100
    ret_bh  = (df_bt["cum_bh"].iloc[-1] / cap - 1) * 100
    alpha   = ret_s - ret_bh
    strat_r = df_bt["strat"].dropna()
    sharpe  = float(strat_r.mean() / strat_r.std() * (252**.5)) if strat_r.std() > 0 else 0
    cm      = df_bt["cum_s"]
    pk      = cm.cummax()
    mdd     = float(((cm - pk) / pk).min() * 100)
    wins    = strat_r[strat_r > 0]
    losses  = strat_r[strat_r < 0]
    wr      = len(wins) / (len(wins)+len(losses)) if (len(wins)+len(losses)) > 0 else 0

    # Métriques
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Stratégie BCE",   f"{ret_s:+.2f}%",
               delta=f"{alpha:+.2f}% vs B&H")
    m2.metric("Buy & Hold",      f"{ret_bh:+.2f}%")
    m3.metric("Alpha",           f"{alpha:+.2f}%",
               delta="Surperformance" if alpha > 0 else "Sous-performance")
    m4.metric("Sharpe 1 an",     f"{sharpe:.2f}")
    m5.metric("Win Rate",        f"{wr:.1%}")
    m6.metric("Max Drawdown",    f"{mdd:.2f}%")

    # Graphique
    if PLOTLY_OK:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_bt.index, y=df_bt["cum_s"],
            mode="lines", name="Stratégie BCE",
            line=dict(color=C["blue"], width=2.5),
            fill="tozeroy", fillcolor='rgba(10,132,255,0.05)',
        ))
        fig.add_trace(go.Scatter(
            x=df_bt.index, y=df_bt["cum_bh"],
            mode="lines", name="Buy & Hold",
            line=dict(color="#444", width=1.5, dash="dot"),
        ))
        DC_C = {"BAISSE":C["buy"],"STABLE":C["wait"],"HAUSSE":C["sell"]}
        for dec in AnalyseurTendancesBCE.HISTORIQUE_DECISIONS:
            try:
                dt = pd.Timestamp(dec["date"])
                if dt >= df_bt.index[0]:
                    fig.add_vline(x=dt,
                                   line_color=DC_C.get(dec["decision"],"#444"),
                                   line_width=1, line_dash="dash", opacity=.4,
                                   annotation_text=dec["decision"][:1],
                                   annotation_font_size=9)
            except Exception:
                pass
        fig.update_layout(**CHART, height=400,
                           title=f"Stratégie BCE vs Buy&Hold — {INDICES.get(sym,sym)} · Capital €{cap:,}",
                           yaxis_title="Capital (€)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟢 Vert=baisse BCE (position longue) · 🟡 Orange=stable · 🔴 Rouge=hausse BCE (position courte)")


# ══════════════════════════════════════════════════════════════════════════════
# §9  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    cfg = sidebar()

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
    margin-bottom:20px;padding-bottom:16px;border-bottom:.5px solid {C['sep']}">
      <div>
        <h1 style="font-size:28px;font-weight:800;margin:0;letter-spacing:-.7px">
          🏦 BCE · Décisions Marché</h1>
        <div style="font-size:13px;color:rgba(255,255,255,.35);margin-top:5px">
          <span style="background:rgba(48,209,88,.15);color:{C['buy']};
          padding:2px 9px;border-radius:10px;font-weight:700;font-size:11px;
          margin-right:8px">● LIVE</span>
          Signaux basés sur news BCE · Données Yahoo Finance · RSS ·
          {datetime.utcnow():%Y-%m-%d %H:%M} UTC
        </div>
      </div>
      <div style="text-align:right;font-size:11px;color:rgba(255,255,255,.2)">
        {"✅ Engine" if ENGINE_OK else "❌ Engine"} ·
        {"✅ Orch." if ORCH_OK else "❌ Orch."}<br>
        {"✅ YFinance" if YF_OK else "❌ YFinance"} ·
        {"✅ RSS" if FP_OK else "❌ RSS"}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Barre de prix rapide
    wl   = cfg.get("watchlist",["^STOXX50E"])[:5]
    prix = load_prix_live(wl)
    if prix:
        cols = st.columns(len(prix))
        for i, (sym, d) in enumerate(prix.items()):
            v  = d.get("var_pct",0)
            cc = C["buy"] if v>0 else C["sell"] if v<0 else "#444"
            cols[i].markdown(f"""
            <div style="background:{C['card']};border-radius:11px;
            padding:9px 13px;border:.5px solid {C['sep']};
            text-align:center;margin-bottom:14px">
              <div style="font-size:10px;color:rgba(255,255,255,.35)">
                {INDICES.get(sym,sym)[:16]}</div>
              <div style="font-size:15px;font-weight:700;
              font-variant-numeric:tabular-nums;margin:2px 0">
                {d.get('prix',0):,.4f}</div>
              <div style="font-size:11px;color:{cc};font-weight:600">
                {v:+.3f}%</div>
            </div>""", unsafe_allow_html=True)

    # Onglets
    tabs = st.tabs([
        "🎯 Décision & Signaux",
        "📈 Tendances BCE",
        "📰 News & Impact",
        "🔍 Screener",
        "🔁 Backtest BCE",
    ])
    with tabs[0]: tab_decision(cfg)
    with tabs[1]: tab_tendances_bce()
    with tabs[2]: tab_news_impact()
    with tabs[3]: tab_screener(cfg)
    with tabs[4]: tab_backtest(cfg)

    st.markdown(f"""
    <div style="text-align:center;padding:16px 0 0;margin-top:20px;
    font-size:10px;color:rgba(255,255,255,.18);
    border-top:.5px solid {C['sep']}">
      Sources : BCE SDMX · FRED · Yahoo Finance · Reuters · Les Echos · Alternative.me ·
      ⚠️ À titre indicatif uniquement — Pas de conseil financier
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
