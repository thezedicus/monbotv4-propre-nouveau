#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import os
from streamlit_autorefresh import st_autorefresh

st.set_page_config("🏦 THE ZEDICUS", layout="wide")
st_autorefresh(interval=300000, key="auto")

st.markdown("<style>.stMetric{background:#1a1f2a;border-radius:12px;padding:12px}.news-card{background:#1e2432;border-radius:10px;padding:10px;margin-bottom:8px}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def geo(): return requests.get("https://ipapi.co/json/").json() if requests.get("https://ipapi.co/json/").ok else {"country":"France","currency":"EUR"}
@st.cache_data(ttl=600)
def rates(): return requests.get("https://api.exchangerate-api.com/v4/latest/EUR").json().get("rates",{"USD":1.09}) if requests.get("https://api.exchangerate-api.com/v4/latest/EUR").ok else {"USD":1.09}
@st.cache_data(ttl=300)
def macro(): return {name:{"value":v,"chg":round((v-p)/p*100,2) if p else 0} for name,tkr in [("VIX","^VIX"),("Taux10Y","^TNX"),("Or","GC=F"),("Pétrole","CL=F")] if not (d:=yf.download(tkr,period="3d",progress=False)).empty for v,p in [(float(d["Close"].iloc[-1]),float(d["Close"].iloc[-2]) if len(d)>1 else v)]}
@st.cache_data(ttl=120)
def indices(): return [{"nom":n,"prix":float(d["Close"].iloc[-1]),"var":round((float(d["Close"].iloc[-1])/float(d["Close"].iloc[-2])-1)*100,2) if len(d)>1 else 0} for n,t in [("Euro Stoxx","^STOXX50E"),("CAC40","^FCHI"),("DAX","^GDAXI")] if not (d:=yf.download(t,period="3d",progress=False)).empty]
@st.cache_data(ttl=600)
def news(): return [{"title":a["title"],"source":a["source"]["name"],"date":a["publishedAt"][:10],"url":a["url"]} for a in requests.get(f"https://newsapi.org/v2/everything?q=BCE&language=fr&pageSize=6&apiKey={os.getenv('NEWSAPI_KEY','')}").json().get("articles",[])] if os.getenv("NEWSAPI_KEY") else []
@st.cache_data(ttl=300)
def crypto(): return requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=eur&include_24hr_change=true").json() if requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=eur&include_24hr_change=true").ok else {}
@st.cache_data(ttl=300)
def commod(): return {name:{"price":float(d["Close"].iloc[-1]),"chg":round((float(d["Close"].iloc[-1])/float(d["Close"].iloc[-2])-1)*100,2) if len(d)>1 else 0} for name,sym in [("Brent","BZ=F"),("Gaz","NG=F"),("Or","GC=F")] if not (d:=yf.download(sym,period="3d",progress=False)).empty}

st.title("🏦 THE ZEDICUS – BCE Zone Euro")
c=geo()["currency"]
st.sidebar.success(f"📍 {geo()['country']} | Devise {c}")
r=rates()
st.subheader("📊 Signal instantané")
st.metric("Décision","ATTENDRE",delta="Confiance 50%")
st.progress(0.5)
df=pd.DataFrame(indices())
if c!="EUR": df["Prix"]=(df["prix"]*r.get(c,1)).round(2)
else: df["Prix"]=df["prix"]
st.dataframe(df[["nom","Prix","var"]].rename(columns={"var":"Var%"}), use_container_width=True)
st.subheader("🌍 Macro")
cols=st.columns(4)
for i,(k,v) in enumerate(macro().items()):
    if i<4: cols[i].metric(k,f"{v['value']:.2f}",f"{v['chg']:+.2f}%" if v['chg'] else None)
if (n:=news()):
    st.subheader("📰 Actualités")
    for a in n[:4]: st.markdown(f"<div class='news-card'><a href='{a['url']}' target='_blank'><b>{a['title']}</b></a><br><span>{a['source']} – {a['date']}</span></div>", unsafe_allow_html=True)
if (cr:=crypto()):
    st.subheader("₿ Crypto")
    for cid,sym in [("bitcoin","BTC"),("ethereum","ETH"),("solana","SOL")]:
        d=cr.get(cid,{})
        if d: st.metric(sym,f"€{d.get('eur',0):,.2f}",f"{d.get('eur_24h_change',0):+.2f}%")
st.subheader("🛢️ Matières premières")
for name,data in commod().items():
    price=data["price"]*(r.get(c,1) if c!="EUR" else 1)
    st.metric(name,f"{price:.2f} {c}",f"{data['chg']:+.2f}%")
st.caption(f"📅 {datetime.utcnow():%Y-%m-%d %H:%M} UTC · Sources indicatives")
