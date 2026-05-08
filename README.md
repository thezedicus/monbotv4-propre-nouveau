# ⚡ THE ZEDICUS — Dashboard BCE Zone Euro

> Tableau de bord algorithmique de trading basé sur les décisions de la **Banque Centrale Européenne**.  
> Génère des signaux **ACHETER / VENDRE / ATTENDRE** avec scoring composite, sizing automatique et analyse macro temps réel.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)
![Data](https://img.shields.io/badge/Data-Yahoo%20Finance%20%7C%20BCE%20%7C%20FRED-F28C28)

---

## 🚀 Démarrage rapide

```bash
git clone https://github.com/VOTRE_USERNAME/zedicus.git
cd zedicus
pip install -r requirements.txt
python3 -m streamlit run zedicus.py
```

Ouvre **http://localhost:8501**

---

## 🌐 Déploiement Streamlit Cloud (gratuit)

1. **Fork** ce repo sur GitHub
2. Aller sur [share.streamlit.io](https://share.streamlit.io)
3. **New app** → votre fork → fichier : `zedicus.py` → **Deploy**

---

## 📊 Fonctionnalités

| Onglet | Description |
|---|---|
| ⚡ Signal & Décision | ACHETER/VENDRE/ATTENDRE · Sizing · Stop Loss · Take Profit · R:R |
| 🏦 Tendances BCE | Historique 2022-2025 · Probabilités prochaine décision · Calendrier |
| 📰 News & Impact | RSS temps réel · Sentiment · Impact indices et secteurs |
| 🌍 Macro | FRED : Fed Funds, T10Y, CPI, Spread 10-2, Chômage, Bilan Fed |
| 🔍 Screener | 13 actifs · Signal · RSI · ADX · Performance comparative |
| 🔁 Backtest BCE | Equity curve · Sharpe · Alpha vs Buy&Hold · Max Drawdown |
| 📄 Export | Rapport Markdown complet téléchargeable |

---

## 🔧 Indicateurs techniques

Tous calculés **nativement** en NumPy/Pandas — aucune dépendance `pandas-ta` ou `TA-Lib`.

`RSI (14)` · `MACD (12/26/9)` · `EMA (20/50/200)` · `Bollinger Bands (20, ±2σ)` · `ATR (14)` · `ADX (14)` · `SuperTrend (10×3)`

---

## 📁 Structure

```
zedicus/
├── zedicus.py           ← Dashboard principal (fichier unique à lancer)
├── bce_engine.py        ← Moteur BCE avancé (optionnel)
├── orchestrator.py      ← Scores composite (optionnel)
├── requirements.txt     ← Dépendances
├── Procfile             ← Déploiement Heroku/Railway
├── .streamlit/
│   └── config.toml      ← Thème sombre
└── README.md
```

> `bce_engine.py` et `orchestrator.py` sont **optionnels** — sans eux le dashboard fonctionne en mode autonome.

---

## 🎯 Sources de données (toutes gratuites, aucune clé requise)

| Source | Données | Cache |
|---|---|---|
| Yahoo Finance | Prix live, OHLCV | 20s–5min |
| BCE SDMX | Euribor, taux officiels | 1h |
| FRED | Taux US, CPI, spreads | 1h |
| Alternative.me | Fear & Greed Index | 10min |
| RSS | BCE, Reuters, Les Echos, Yahoo Finance | 10min |

---

## ⚙️ Configuration optionnelle

Créer `.env` à la racine :

```env
ALPHA_VANTAGE_KEY=   # alphavantage.co (gratuit, 25 req/jour)
FINNHUB_KEY=         # finnhub.io (gratuit)
FRED_API_KEY=        # fred.stlouisfed.org (gratuit)
CAPITAL=100          # Capital par défaut en €
```

---

## ⚠️ Avertissement

Fourni à titre **éducatif et informatif uniquement**.  
Ne constitue pas un conseil financier. Le trading comporte des risques de perte en capital.

---

## 📄 Licence

MIT — libre d'utilisation, modification et distribution.
