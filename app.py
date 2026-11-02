"""RS Matrix — dark trading dashboard.
Public daily-data research tool; does not promise consolidated real-time quotes.
"""
import html
import io
import math
import re
from datetime import datetime
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="RS MATRIX | Sector Leadership", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# ---------- Theme / design ----------
BG = "#0b1018"
PANEL = "#131b26"
LINE = "#253142"
MUTED = "#97a6b9"
GREEN = "#24bd76"
RED = "#f05256"
AMBER = "#efbd5e"

st.markdown("""
<style>
:root{color-scheme:dark;--background-color:#0b1018;--secondary-background-color:#131b26;--text-color:#ecf2f8;--primary-color:#26c982}
html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"]{background:#0b1018!important;color:#ecf2f8!important}
[data-testid="stSidebar"], [data-testid="stSidebarContent"]{background:#111925!important}
[data-testid="stMainBlockContainer"]{max-width:1720px!important;padding-top:1.1rem!important;padding-left:2.2rem!important;padding-right:2.2rem!important}
h1,h2,h3,p,label,span{color:inherit}
[data-testid="stMarkdownContainer"] p{line-height:1.45}
[data-testid="stMetric"]{background:#141e2a;border:1px solid #253142;border-radius:10px;padding:12px 15px}
[data-testid="stMetricLabel"]{color:#9cacc1!important}
[data-testid="stMetricValue"]{color:#eaf2fa!important;font-weight:700}
[data-testid="stSelectbox"]>div>div, [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input{background:#172231!important;color:#eaf2fa!important;border-color:#304154!important}
[data-testid="stCheckbox"] label,[data-testid="stRadio"] label{color:#dce6f2!important}
button[kind="primary"]{background:#22ab73!important;border-color:#22ab73!important;color:#08120d!important}
[data-testid="stDataFrame"], [data-testid="stTable"]{border:1px solid #2c3847!important;border-radius:10px}
div[data-testid="stExpander"]{background:#101824;border:1px solid #253142;border-radius:10px}
[data-testid="stAlert"]{border-radius:10px}
.block-container hr{border-color:#233142}
.rsm-brand{display:flex;align-items:center;gap:14px;margin:4px 0 12px}
.rsm-brandmark{width:35px;height:35px;display:grid;place-items:center;background:#18293b;border:1px solid #2d5771;border-radius:8px;color:#54b9e9;font-weight:900;font-size:19px}
.rsm-title{font-size:24px;font-weight:820;letter-spacing:1px;line-height:1.05;color:#f4f8ff}
.rsm-subtitle{font-size:12px;color:#94a7bd;margin-top:4px}
.rsm-chip{font-size:11px;letter-spacing:.5px;background:#173528;color:#64df9b;padding:5px 9px;border-radius:7px;border:1px solid #22543b}
.rsm-note{font-size:12px;color:#8295a9}
.rsm-head{font-size:12px;color:#7f95ae;font-weight:750;letter-spacing:1.1px;margin:0 0 10px;text-transform:uppercase}
.rsm-rail{background:#101822;border:1px solid #293648;border-radius:12px;padding:15px 14px}
.rsm-sector{display:flex;align-items:center;gap:7px;padding:8px 1px;border-bottom:1px solid #1b2939}
.rsm-sector:last-child{border-bottom:0}
.rsm-rank{font-size:10px;color:#6e8298;width:17px;flex:none}
.rsm-sname{font-size:11px;font-weight:650;color:#dae4ee;width:125px;flex:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rsm-track{height:7px;background:#293444;border-radius:6px;flex:1;overflow:hidden;min-width:15px}
.rsm-fill{height:100%;border-radius:6px}
.rsm-rs{font-size:11px;font-weight:750;width:45px;text-align:right;flex:none}
.rsm-matrix{overflow-x:auto;border:1px solid #2a394b;border-radius:12px;background:#111a25}
.rsm-grid{min-width:670px}
.rsm-matrix-head,.rsm-matrix-row{display:grid;grid-template-columns:175px repeat(4,minmax(112px,1fr)) 70px}
.rsm-matrix-head{position:sticky;top:0;z-index:5;background:#1a2634;border-bottom:1px solid #314254}
.rsm-matrix-head>div{padding:13px 7px;text-align:center;font-size:11px;font-weight:750;color:#c8d6e5;border-left:1px solid #2c3c50}
.rsm-matrix-head>div:first-child{text-align:left;border-left:0}
.rsm-matrix-row{border-bottom:1px solid #273446;min-height:62px}
.rsm-matrix-row:nth-child(even){background:#131f2c}
.rsm-matrix-row:last-child{border-bottom:0}
.rsm-industry{padding:14px 9px;font-size:11px;line-height:1.3;color:#afc0d2;display:flex;align-items:center;overflow-wrap:anywhere}
.rsm-cell{display:flex;align-items:center;justify-content:flex-start;align-content:center;gap:5px;flex-wrap:wrap;padding:9px 6px;border-left:1px solid #273648}
.rsm-bubble{display:inline-flex;align-items:center;justify-content:center;flex:none;width:37px;height:37px;border-radius:50%;font-size:9px;font-weight:800;text-decoration:none!important;letter-spacing:-.15px;color:#fff!important;border:1px solid #ffffff22;transition:transform .14s ease,box-shadow .14s ease}
.rsm-bubble:hover{transform:scale(1.14);box-shadow:0 0 0 2px #fff5;z-index:2}
.rsm-empty{color:#3d4c5d;font-size:11px}
.rsm-foot{font-size:11px;color:#7d8fa4;padding:10px 4px}
.rsm-etftable{overflow-x:auto;border:1px solid #2a394b;border-radius:12px;background:#111a25;margin:12px 0}
.rsm-etfinner{min-width:760px}
.rsm-etfrow{display:grid;grid-template-columns:185px minmax(570px,1fr);align-items:center;border-bottom:1px solid #273648;min-height:80px}
.rsm-etfrow:nth-child(even){background:#131f2c}
.rsm-etfrow:last-child{border-bottom:0}
.rsm-etflabel{font-size:12px;color:#dce8f4;padding:12px;border-right:1px solid #293749}
.rsm-etflabel b{color:#f7fbff;font-size:14px}
.rsm-etfchips{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:9px 12px}
.rsm-etfbubble{display:inline-flex;align-items:center;justify-content:center;width:49px;height:49px;border-radius:50%;font-size:10px;font-weight:800;color:#f9fbff!important;border:1px solid #ffffff30;text-decoration:none!important;transition:transform .14s ease;flex:none}
.rsm-etfbubble:hover{transform:scale(1.13);box-shadow:0 0 0 2px #ffffff55}

.rsm-pill{display:inline-block;font-size:11px;color:#c2d0df;border:1px solid #34455a;border-radius:15px;padding:4px 10px;margin-right:8px;margin-top:3px}
.rsm-section{font-size:17px;color:#ecf2f8;font-weight:750;margin:12px 0 4px}
.rsm-small{font-size:12px;color:#9daec2;margin:2px 0 12px}
@media(max-width:900px){[data-testid="stMainBlockContainer"]{padding-left:1rem!important;padding-right:1rem!important}.rsm-matrix-head,.rsm-matrix-row{grid-template-columns:135px repeat(4,110px) 65px}.rsm-brand{flex-wrap:wrap}.rsm-title{font-size:20px}}
</style>
""", unsafe_allow_html=True)

SPDR = {
    "XLK":"Technology", "XLF":"Financials", "XLE":"Energy", "XLV":"Health Care",
    "XLI":"Industrials", "XLY":"Consumer Discretionary", "XLP":"Consumer Staples",
    "XLU":"Utilities", "XLB":"Materials", "XLRE":"Real Estate", "XLC":"Communication Services",
}
PERIODS = ["1D", "1W", "1M", "3M", "6M", "YTD"]
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; RSMatrixResearch/3.0)"}
TIER_ORDER = ["Mega", "Large", "Mid", "Small", "Unknown"]


def fmt_signed(x):
    return f"{x:+.2f}%" if pd.notna(x) else "—"


def color_rs(x):
    if pd.isna(x): return "#415164"
    # Saturated enough to remain legible in a crowded trading matrix.
    if x >= 8: return "#0d8e56"
    if x >= 3: return "#168c61"
    if x >= 1: return "#3d996b"
    if x >= 0: return "#698b70"
    if x >= -1: return "#8b635e"
    if x >= -3: return "#b64b4b"
    return "#ce343b"


def cap_tier(value):
    if pd.isna(value) or value <= 0: return "Unknown"
    if value >= 200e9: return "Mega"
    if value >= 50e9: return "Large"
    if value >= 20e9: return "Mid"
    return "Small"


@st.cache_data(ttl=12*3600, show_spinner=False)
def get_snapshot():
    """Nasdaq-sourced market caps and listings, publisher updates on weekdays.
    This is NOT a live market-cap feed and is not an official GICS sector source.
    """
    url = "https://raw.githubusercontent.com/zyhe16/top-us-stock-tickers/main/data/v2/tickers.csv"
    r = requests.get(url, headers=HEADERS, timeout=22)
    r.raise_for_status()
    snap = pd.read_csv(io.StringIO(r.text), keep_default_na=False, low_memory=False)
    needed = {"symbol","name","market_cap","sector","industry","is_sp500"}
    if not needed.issubset(snap.columns) or len(snap) < 3000:
        raise RuntimeError("Nasdaq snapshot incomplete")
    snap["Symbol"] = snap["symbol"].astype(str).str.upper().str.replace("/", "-", regex=False).str.replace(".", "-",regex=False)
    snap["Market Cap"] = pd.to_numeric(snap["market_cap"], errors="coerce")
    snap["Market Cap"] = snap["Market Cap"].where(snap["Market Cap"] > 0)
    snap["Sector Source"] = snap["sector"].replace("", "Unclassified")
    snap["Industry Source"] = snap["industry"].replace("", "Unclassified")
    snap = snap.drop_duplicates("Symbol")
    return snap


@st.cache_data(ttl=86400, show_spinner=False)
def get_sp500():
    errors=[]
    for url in (
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    ):
        try:
            r = requests.get(url,headers=HEADERS,timeout=20)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text),dtype=str) if "csv" in url else pd.read_html(io.StringIO(r.text))[0]
            df = df.rename(columns={"GICS Sector":"Sector","GICS Sub-Industry":"Industry","Name":"Security"})
            df["Symbol"] = df["Symbol"].astype(str).str.replace(".","-",regex=False)
            df["Industry"] = df.get("Industry",pd.Series("Unclassified",index=df.index)).fillna("Unclassified")
            df = df[["Symbol","Security","Sector","Industry"]].drop_duplicates("Symbol").dropna(subset=["Symbol"])
            if len(df)>400: return df
            errors.append("short S&P 500 list")
        except Exception as exc:
            errors.append(str(exc)[:100])
    # If both canonical sources fail, use snapshot-flagged S&P membership; mark classification source.
    try:
        snap=get_snapshot()
        flags=snap["is_sp500"].astype(str).str.lower().eq("true")
        subset=snap.loc[flags].copy()
        if len(subset) > 400:
            subset=subset.rename(columns={"name":"Security","Sector Source":"Sector","Industry Source":"Industry"})
            return subset[["Symbol","Security","Sector","Industry"]]
    except Exception as exc:
        errors.append(str(exc)[:100])
    raise RuntimeError("S&P 500 constituents unavailable: " + "; ".join(errors))


@st.cache_data(ttl=86400, show_spinner=False)
def fallback_all_us():
    """Fallback if GitHub Nasdaq snapshot unavailable; cannot provide reliable cap tiers."""
    def txt(url):
        r=requests.get(url,headers=HEADERS,timeout=20);r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text),sep="|",dtype=str)
    nas=txt("https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt")
    nas=nas[(nas["Test Issue"]=="N") & nas["Symbol"].notna()]
    nas=nas[["Symbol","Security Name"]].rename(columns={"Security Name":"Security"})
    other=txt("https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt")
    other=other[(other["Test Issue"]=="N") & other["Exchange"].isin(["N","A"])]
    other=other[["ACT Symbol","Security Name"]].rename(columns={"ACT Symbol":"Symbol","Security Name":"Security"})
    out=pd.concat([nas,other],ignore_index=True).drop_duplicates("Symbol")
    out["Symbol"]=out["Symbol"].str.replace(".","-",regex=False)
    out=out[out.Symbol.str.fullmatch(r"[A-Z]{1,5}(-[A-Z])?",na=False)]
    out=out[~out.Security.str.contains(r"ETF|ETN|Warrant|Preferred|Depositary|Units|Rights",case=False,regex=True,na=False)]
    out["Market Cap"]=np.nan
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def prices(symbols):
    """Batch daily adjusted history. Caller must not assume exact synchronicity."""
    symbols=list(dict.fromkeys(["SPY"]+list(symbols)))
    closes=[];volumes=[]
    for i in range(0,len(symbols),70):
        batch=symbols[i:i+70]
        try:
            raw=yf.download(batch, period="18mo", interval="1d", auto_adjust=True,
                            progress=False, threads=True, group_by="column")
            if raw.empty: continue
            if isinstance(raw.columns,pd.MultiIndex):
                c=raw["Close"]; v=raw["Volume"]
            else:
                c=raw[["Close"]].rename(columns={"Close":batch[0]})
                v=raw[["Volume"]].rename(columns={"Volume":batch[0]})
            if isinstance(c,pd.Series): c=c.to_frame(name=batch[0])
            if isinstance(v,pd.Series): v=v.to_frame(name=batch[0])
            closes.append(c);volumes.append(v)
        except Exception:
            continue
    if not closes: return pd.DataFrame(),pd.DataFrame()
    c=pd.concat(closes,axis=1).loc[:,lambda x: ~x.columns.duplicated()]
    v=pd.concat(volumes,axis=1).loc[:,lambda x: ~x.columns.duplicated()]
    return c.sort_index(),v.reindex(c.index)


def lookback_for(period, index):
    if period!="YTD":return {"1D":1,"1W":5,"1M":21,"3M":63,"6M":126}[period]
    if len(index)==0:return 1
    last=pd.Timestamp(index[-1]).tz_localize(None) if pd.Timestamp(index[-1]).tzinfo else pd.Timestamp(index[-1])
    in_year=sum(pd.Timestamp(d).year==last.year for d in index)
    return max(1,in_year-1)


def period_rs(close, days, offset=0):
    if close.empty or "SPY" not in close:return pd.Series(dtype=float)
    c=close.ffill(limit=3)
    if len(c)<=days+offset:return pd.Series(dtype=float)
    end = c.iloc[len(c)-1-offset]
    start=c.iloc[len(c)-1-offset-days]
    spy_ratio=end.get("SPY",np.nan)/start.get("SPY",np.nan)
    if not np.isfinite(spy_ratio) or spy_ratio<=0:return pd.Series(dtype=float)
    return ((end/start)/spy_ratio-1)*100


def build_signals(close, volume, days, universe):
    close=close.ffill(limit=3)
    if close.empty or "SPY" not in close or len(close)<205:return pd.DataFrame()
    rs=period_rs(close,days)
    rs_week=period_rs(close,5)
    rs_prev=period_rs(close,5,offset=5)
    rs_1m=period_rs(close,21)
    last=close.iloc[-1]
    ma50=close.rolling(50,min_periods=50).mean().iloc[-1]
    ma200=close.rolling(200,min_periods=200).mean().iloc[-1]
    # Last observed volumes may reflect an incomplete trading day; view is labelled accordingly.
    vol=volume.reindex(index=close.index,columns=close.columns).fillna(0)
    prior_avg=vol.shift(1).rolling(20,min_periods=15).mean().iloc[-1].replace(0,np.nan)
    rvol=vol.iloc[-1]/prior_avg
    up=close.diff().tail(50)>0; down=close.diff().tail(50)<0
    upvol=vol.tail(50).where(up).sum()
    dnvol=vol.tail(50).where(down).sum()
    ud=upvol/dnvol.replace(0,np.nan)
    line=close.div(close["SPY"],axis=0)
    prior20=line.shift(1).rolling(20,min_periods=20).max().iloc[-1]
    line_break=(line.iloc[-1]>prior20) & (line.shift(1).iloc[-1]<=prior20)
    signal=pd.DataFrame({
        "Symbol":rs.index, "RS %":rs.values,
        "RS 1W %":rs_week.reindex(rs.index).values,
        "RS 1M %":rs_1m.reindex(rs.index).values,
        "RS acceleration":(rs_week-rs_prev).reindex(rs.index).values,
        "RS new 20D high":line_break.reindex(rs.index).fillna(False).values,
        "Price":last.reindex(rs.index).values,
        "MA50":ma50.reindex(rs.index).values,
        "MA200":ma200.reindex(rs.index).values,
        "RVOL":rvol.reindex(rs.index).values,
        "U/D proxy":ud.reindex(rs.index).values,
    })
    signal=signal[signal.Symbol!="SPY"].dropna(subset=["RS %","Price"])
    signal=signal.merge(universe,on="Symbol",how="left")
    signal["Sector"]=signal["Sector"].fillna("Unclassified")
    signal["Industry"]=signal["Industry"].fillna("Unclassified")
    signal["Market Cap"]=pd.to_numeric(signal["Market Cap"],errors="coerce")
    signal["Cap tier"]=signal["Market Cap"].map(cap_tier)
    signal["Trend"]=(signal.Price>signal.MA50)&(signal.MA50>signal.MA200)
    signal["Minervini candidate"]=(signal["RS 1W %"]>0)&(signal["RS 1M %"]>0)&signal.Trend&(signal.RVOL>1)&(signal["U/D proxy"]>1.5)
    return signal


@st.cache_data(ttl=21600, show_spinner=False)
def spdr_holdings(etf):
    """Top 10 reported provider positions; no invented/stale hardcoded holdings."""
    try:
        f=yf.Ticker(etf).funds_data.top_holdings
        if isinstance(f,pd.DataFrame) and not f.empty:
            if "Symbol" not in f.columns: f=f.reset_index().rename(columns={"index":"Symbol"})
            sc=next((c for c in f if str(c).lower() in ("symbol","ticker","holding")),None)
            wc=next((c for c in f if "weight" in str(c).lower() or "holding percent" in str(c).lower()),None)
            if sc and wc:
                out=f[[sc,wc]].copy();out.columns=["Symbol","Weight %"]
                out["Weight %"]=pd.to_numeric(out["Weight %"],errors="coerce")
                if out["Weight %"].max()<=1:out["Weight %"]*=100
                out["Symbol"]=out["Symbol"].astype(str).str.replace(".","-",regex=False)
                out=out.dropna().sort_values("Weight %",ascending=False).head(10)
                if len(out)>=5:return out,"Yahoo Finance · holdings date not verified"
    except Exception:
        pass
    try:
        u=f"https://stockanalysis.com/etf/{etf.lower()}/holdings/"
        r=requests.get(u,headers=HEADERS,timeout=12);r.raise_for_status()
        for h in pd.read_html(io.StringIO(r.text)):
            sc=next((c for c in h if str(c).lower().strip() in ("symbol","ticker")),None)
            wc=next((c for c in h if "weight" in str(c).lower()),None)
            if sc and wc:
                out=h[[sc,wc]].copy();out.columns=["Symbol","Weight %"]
                out["Weight %"]=pd.to_numeric(out["Weight %"].astype(str).str.replace("%","",regex=False),errors="coerce")
                out["Symbol"]=out["Symbol"].astype(str).str.replace(".","-",regex=False)
                out=out.dropna().sort_values("Weight %",ascending=False).head(10)
                if len(out)>=5:return out,f"Stock Analysis · {u} · verify date"
    except Exception:
        pass
    return pd.DataFrame(columns=["Symbol","Weight %"]),"Holdings source unavailable"


def sector_rail(frame):
    if frame.empty:return "<div class='rsm-rail'>No sector data</div>"
    groups=frame.groupby("Sector",dropna=False).agg(RS=("RS %","mean"),Count=("Symbol","count")).reset_index()
    groups=groups.sort_values("RS",ascending=False)
    scale=max(groups["RS"].abs().max(),1)
    lines=[]
    for j, row in enumerate(groups.itertuples(index=False)):
        s=html.escape(str(row.Sector)); v=float(row.RS)
        color=color_rs(v);pct=max(5,int(abs(v)/scale*100))
        lines.append(f"<div class='rsm-sector' title='{row.Count} active symbols'>"
                     f"<span class='rsm-rank'>{j+1:02d}</span><span class='rsm-sname'>{s}</span>"
                     f"<div class='rsm-track'><div class='rsm-fill' style='width:{pct}%;background:{color}'></div></div>"
                     f"<span class='rsm-rs' style='color:{color}'>{v:+.1f}</span></div>")
    return "<div class='rsm-rail'><div class='rsm-head'>Sector RS · equal-weight mean</div>"+"".join(lines)+"</div>"


def bubbles_matrix(frame, max_symbols=160, group_col="Industry"):
    if frame.empty:return "<div class='rsm-rail'>No matching tickers.</div>"
    frame=frame.sort_values("RS %",ascending=False).head(max_symbols).copy()
    # Order groups by their strongest performers, not alphabetically.
    groups=frame.groupby(group_col).agg(strength=("RS %","mean"),n=("Symbol","size")).sort_values("strength",ascending=False)
    lines=["<div class='rsm-matrix'><div class='rsm-grid'>",
           "<div class='rsm-matrix-head'><div>INDUSTRY</div>",
           "<div>MEGA <small>≥$200B</small></div><div>LARGE <small>$50–200B</small></div>",
           "<div>MID <small>$20–50B</small></div><div>SMALL <small>&lt;$20B</small></div><div>UNKNOWN</div></div>"]
    for ind in groups.index:
        sub=frame.loc[frame[group_col]==ind].copy()
        lines.append("<div class='rsm-matrix-row'><div class='rsm-industry'>"+html.escape(str(ind))+" <span style='color:#657c93'>&nbsp;· "+str(len(sub))+"</span></div>")
        for tier in TIER_ORDER:
            group=sub[sub["Cap tier"]==tier]
            content=[]
            for _, r in group.iterrows():
                sym=html.escape(str(r["Symbol"]))
                sector=html.escape(str(r.get("Sector","")))
                cap=r["Market Cap"]
                cap_str=f"${cap/1e9:,.1f}B" if pd.notna(cap) else "unavailable"
                desc=html.escape(f"{r['Symbol']} | {sector} | RS {fmt_signed(r['RS %'])} | Market cap {cap_str} | RVOL {r['RVOL']:.2f}" if pd.notna(r['RVOL']) else f"{r['Symbol']} | RS {fmt_signed(r['RS %'])} | Market cap {cap_str}",quote=True)
                url="https://www.tradingview.com/chart/?symbol="+quote(str(r["Symbol"]),safe="")
                content.append(f"<a class='rsm-bubble' target='_blank' rel='noopener noreferrer' href='{url}' title='{desc}' style='background:{color_rs(r['RS %'])}'>{sym}</a>")
            lines.append("<div class='rsm-cell'>"+("".join(content) if content else "<span class='rsm-empty'>·</span>")+"</div>")
        lines.append("</div>")
    lines.append("</div></div>")
    return "".join(lines)


def spdr_bubbles(holdings, value_col="RS vs SPY %"):
    """Provider-weight sorted, ticker-linked dark bubble rows for SPDR holdings.

    Missing quotes / weights are shown as unavailable and never colored as signal.
    """
    if holdings.empty:
        return "<div class='rsm-rail'>No holdings available.</div>"
    lines=["<div class='rsm-etftable'><div class='rsm-etfinner'>"]
    for etf, group in holdings.groupby("ETF",sort=False):
        sec=html.escape(SPDR.get(etf,etf))
        lines.append(f"<div class='rsm-etfrow'><div class='rsm-etflabel'><b>{html.escape(etf)}</b><div>{sec}</div><div style='font-size:10px;color:#869db2'>Top {len(group)} by ETF weight</div></div><div class='rsm-etfchips'>")
        for _,r in group.sort_values("Weight %",ascending=False).iterrows():
            sym=str(r["Symbol"])
            val=r.get(value_col,np.nan)
            val_str=fmt_signed(val)
            weight=r.get("Weight %",np.nan)
            title=html.escape(f"{sym} · fund weight {weight:.2f}% · {value_col}: {val_str}" if pd.notna(weight) else f"{sym} · {value_col}: {val_str}",quote=True)
            bubble_color=color_rs(val)
            url="https://www.tradingview.com/chart/?symbol="+quote(sym,safe="")
            lines.append(f"<a target='_blank' rel='noopener noreferrer' class='rsm-etfbubble' style='background:{bubble_color}' href='{url}' title='{title}'>{html.escape(sym)}</a>")
        lines.append("</div></div>")
    return "".join(lines)+"</div></div>"


def market_scope(sp, snap, use_sp):
    if snap is None:
        if use_sp: df=sp.copy();df["Market Cap"]=np.nan;return df
        try:
            all_us=fallback_all_us()
            joined=all_us.merge(sp[["Symbol","Sector","Industry"]],on="Symbol",how="left")
            joined["Industry"]=joined.Industry.fillna("Unclassified")
            joined["Sector"]=joined.Sector.fillna("Unclassified")
            return joined
        except Exception as exc:
            st.warning("NYSE/Nasdaq list currently unavailable; showing S&P 500 instead. " + str(exc)[:140])
            df=sp.copy();df["Market Cap"]=np.nan;return df
    cols=["Symbol","Market Cap","Sector Source","Industry Source","name"]
    if use_sp:
        out=sp.merge(snap[cols],on="Symbol",how="left")
        return out
    out=snap.copy()
    out=out[out["Symbol"].str.fullmatch(r"[A-Z]{1,5}(-[A-Z])?",na=False)]
    out=out[~out["name"].astype(str).str.contains(r"ETF|ETN|Exchange.Traded|Warrant|Preferred|Depositary|Units|Rights",case=False,regex=True,na=False)]
    out=out.rename(columns={"name":"Security","Sector Source":"Sector","Industry Source":"Industry"})
    out=out.sort_values("Market Cap",ascending=False)
    gics=sp[["Symbol","Sector","Industry"]].rename(columns={"Sector":"GICS Sector","Industry":"GICS Industry"})
    out=out.merge(gics,on="Symbol",how="left")
    out["Sector"]=out["GICS Sector"].fillna(out["Sector"])
    out["Industry"]=out["GICS Industry"].fillna(out["Industry"])
    return out


def rotation_fig(c):
    # x = 20d relative return vs SPY; y = change in 5d relative return, vs prior 5d.
    # This is a transparent custom rotation proxy, NOT an official RRG / JdK measure.
    fig=go.Figure()
    qcolors={"Leading":"#25be77","Improving":"#4c9fdb","Weakening":"#f0b75c","Lagging":"#e75d63"}
    for x0,x1,y0,y1,color in [(-25,0,0,25,"#142b3b"),(0,25,0,25,"#143025"),
                               (-25,0,-25,0,"#302022"),(0,25,-25,0,"#352c20")]:
        fig.add_shape(type="rect",x0=x0,x1=x1,y0=y0,y1=y1,fillcolor=color,line_width=0,layer="below")
    for label,x,y in [("IMPROVING",-23,22),("LEADING",22,22),("LAGGING",-23,-22),("WEAKENING",22,-22)]:
        fig.add_annotation(x=x,y=y,text=label,showarrow=False,font=dict(color="#8a9aaf",size=13),opacity=.82)
    rows=[]
    for etf,sector in SPDR.items():
        current_x=period_rs(c,21).get(etf,np.nan)
        now=period_rs(c,5).get(etf,np.nan)
        prev=period_rs(c,5,offset=5).get(etf,np.nan)
        dy=now-prev
        if not np.isfinite(current_x) or not np.isfinite(dy):continue
        status=("Leading" if dy>=0 else "Weakening") if current_x>=0 else ("Improving" if dy>=0 else "Lagging")
        rows.append({"ETF":etf,"Sector":sector,"RS 1M %":current_x,"RS momentum pp":dy,"Rotation":status})
        # Weekly relative-performance trail; each point uses information available at the offset.
        trail=[]
        for off in (15,10,5,0):
            xx=period_rs(c,21,offset=off).get(etf,np.nan)
            yy=period_rs(c,5,offset=off).get(etf,np.nan)-period_rs(c,5,offset=off+5).get(etf,np.nan)
            if np.isfinite(xx) and np.isfinite(yy):trail.append((xx,yy))
        if len(trail)>1:
            fig.add_trace(go.Scatter(x=[a for a,b in trail],y=[b for a,b in trail],mode="lines+markers",
                marker=dict(size=[4]*(len(trail)-1)+[8],color=qcolors[status]),
                line=dict(color=qcolors[status],width=2),name=etf,showlegend=False,
                hovertemplate=etf+"<br>20D RS %{x:.2f}<br>RS acceleration %{y:.2f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=[current_x],y=[dy],mode="markers+text",text=[etf],textposition="top center",
            textfont=dict(size=11,color="#eef5fa"),marker=dict(size=16,color=qcolors[status],line=dict(color="#d2e3ee",width=1)),
            name=etf,showlegend=False,hovertemplate=f"{etf} · {sector}<br>RS 1M %{{x:.2f}}<br>Momentum %{{y:.2f}} pp<extra></extra>"))
    fig.add_hline(y=0,line_width=1,line_color="#8291a2")
    fig.add_vline(x=0,line_width=1,line_color="#8291a2")
    xs=[r["RS 1M %"] for r in rows];ys=[r["RS momentum pp"] for r in rows]
    marginx=max(7,max((abs(v) for v in xs),default=7)*1.35)
    marginy=max(7,max((abs(v) for v in ys),default=7)*1.35)
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,font=dict(color="#c3d2e2"),
        margin=dict(l=12,r=12,t=10,b=15),height=580,
        xaxis=dict(title="20-day RS vs SPY (%)",range=[-marginx,marginx],zeroline=False,gridcolor="#2a3645"),
        yaxis=dict(title="5-day RS acceleration (pp)",range=[-marginy,marginy],zeroline=False,gridcolor="#2a3645"))
    return fig,pd.DataFrame(rows)


# ---------- Header / global filters ----------
st.markdown("""<div class='rsm-brand'>
<span class='rsm-brandmark'>▥</span><div><div class='rsm-title'>RS MATRIX <span style='color:#57bf94'>/</span> MARKET LEADERSHIP</div>
<div class='rsm-subtitle'>S&P 500 · Sector SPDR · Market-cap tiers · Breakout candidates</div></div>
<span class='rsm-chip'>FREE DAILY DATA</span></div>""",unsafe_allow_html=True)

bar1,bar2,bar3,bar4=st.columns([1.7,2.7,1.9,1.5])
with bar1:
    universe_choice=st.selectbox("Universe",["S&P 500","NYSE + Nasdaq (top N)"],
                                help="Used for RS Matrix and Minervini Scanner; sector views use only sector ETFs.")
with bar2:
    view=st.radio("Workspace",["RS MATRIX","SECTOR SPDR","SECTOR ROTATION","MINERVINI SCANNER"],
                  horizontal=True,label_visibility="collapsed")
with bar3:
    period=st.selectbox("RS WINDOW",PERIODS,index=1)
with bar4:
    refresh=st.button("↻ Refresh prices",type="primary",use_container_width=True)

if refresh:
    prices.clear()

# Sector modules should NOT incur hundreds of quote downloads from the stock scanner.
if view in ("RS MATRIX","MINERVINI SCANNER"):
    try:
        sp=get_sp500()
    except Exception as exc:
        st.error("Cannot load S&P 500 list: " + str(exc));st.stop()
    try:
        snap=get_snapshot()
    except Exception as exc:
        snap=None
        st.warning("Market-cap snapshot unavailable: cap tiers will show 'Unknown'. " + str(exc)[:160])

    all_symbols=market_scope(sp,snap,universe_choice=="S&P 500")
    if universe_choice!="S&P 500":
        n=st.slider("NYSE + Nasdaq sample (ranked by available market cap)",100,2000,500,100)
        all_symbols=all_symbols.head(n)
    universe=all_symbols.copy()
    with st.spinner(f"Loading price history for {len(universe)} tickers (Yahoo Finance, cached 30 minutes)…"):
        close,volume=prices(tuple(universe.Symbol.tolist()))
    if close.empty or "SPY" not in close:
        st.error("Yahoo Finance temporarily unavailable/rate-limited. Try later or reduce the universe size.")
        st.stop()
    days=lookback_for(period,close.index)
    data=build_signals(close,volume,days,universe)
    if data.empty:
        st.error("Insufficient historical price data for this scan.");st.stop()
    k1,k2,k3,k4,k5=st.columns(5)
    k1.metric("Valid tickers",f"{len(data):,}")
    k2.metric("Outperform SPY",f"{(data['RS %']>0).sum():,}")
    k3.metric("RS accelerating",f"{(data['RS acceleration']>0).sum():,}")
    k4.metric("Minervini candidates",f"{data['Minervini candidate'].sum():,}")
    k5.metric("Price date",str(pd.Timestamp(close.index[-1]).date()))
    st.markdown("<div class='rsm-note'>Adjusted daily close · relative returns vs SPY · market caps: Nasdaq snapshot (not intraday) · RVOL/U-D estimates from daily bars · no guaranteed real-time consolidated feed</div>",unsafe_allow_html=True)
else:
    st.markdown("<div class='rsm-note'>Sector ETFs are loaded independently of the stock universe · daily Yahoo Finance bars · holdings may update on a different date</div>",unsafe_allow_html=True)
st.divider()

if view=="RS MATRIX":
    sub1,sub2,sub3=st.columns([1.85,1.0,1.4])
    with sub1:
        sectors=sorted(data["Sector"].dropna().unique().tolist())
        sector_name=st.selectbox("Sector",["All sectors"]+sectors,index=(sectors.index("Technology")+1 if "Technology" in sectors else 0))
    with sub2:
        show_count=st.select_slider("Max bubbles",options=[50,80,120,160,250,500],value=160)
    with sub3:
        search=st.text_input("Find ticker",placeholder="AAPL, NVDA, PLTR…").upper().strip()
    with st.expander("Additional matrix filters",expanded=False):
        filt1,filt2,filt3=st.columns(3)
        with filt1: positive=st.checkbox("Only outperforming SPY",value=False)
        with filt2: improving=st.checkbox("Only RS accelerating",value=False)
        with filt3: only_trend=st.checkbox("Only MA50 > MA200 + price above MA50",value=False)
    shown=data.copy()
    if sector_name!="All sectors":shown=shown[shown["Sector"]==sector_name]
    if positive:shown=shown[shown["RS %"]>0]
    if improving:shown=shown[shown["RS acceleration"]>0]
    if only_trend:shown=shown[shown["Trend"]]
    if search:shown=shown[shown["Symbol"].str.contains(search,regex=False)]
    left,right=st.columns([1.2,3.6],gap="small")
    with left:
        st.markdown(sector_rail(data),unsafe_allow_html=True)
        st.caption("Sector RS = unweighted mean of available constituent RS, not an ETF return. Ranked over the selected window.")
    with right:
        st.markdown("<div class='rsm-head'>INDUSTRY × MARKET CAP · "+html.escape(period)+" vs SPY</div>",unsafe_allow_html=True)
        st.markdown(bubbles_matrix(shown,max_symbols=show_count),unsafe_allow_html=True)
        st.markdown("<div class='rsm-foot'>Green: outperforming SPY · Red: underperforming · Hover to view RS/market cap · Click a ticker for TradingView. 'Unknown' = missing market cap. Top symbols by RS shown.</div>",unsafe_allow_html=True)
    st.markdown("<div class='rsm-section'>Quick leadership list</div>",unsafe_allow_html=True)
    top=shown.sort_values("RS %",ascending=False).head(35).copy()
    top["TradingView"]=top.Symbol.map(lambda s:"https://www.tradingview.com/chart/?symbol="+quote(str(s),safe=""))
    st.dataframe(top[["Symbol","Security","Sector","Industry","Cap tier","RS %","RS acceleration","RVOL","TradingView"]],
        hide_index=True,use_container_width=True,
        column_config={"RS %":st.column_config.NumberColumn(format="%.2f%%"),
                       "RS acceleration":st.column_config.NumberColumn("RS accel. (pp)",format="%+.2f"),
                       "RVOL":st.column_config.NumberColumn(format="%.2f"),
                       "TradingView":st.column_config.LinkColumn("Chart",display_text="Open ↗")})

elif view=="SECTOR SPDR":
    st.markdown("<div class='rsm-section'>SELECT SECTOR SPDR · 11 ETFs + TOP 10 HOLDINGS</div><div class='rsm-small'>Compare sector returns vs SPY and each ETF's largest reported holdings. Holdings source date must be verified with provider.</div>",unsafe_allow_html=True)
    sector_etfs=list(SPDR)
    with st.spinner("Loading sector ETF histories…"):
        etf_close,_=prices(tuple(sector_etfs))
    if etf_close.empty or "SPY" not in etf_close:
        st.warning("Sector ETF prices unavailable from Yahoo Finance.")
    else:
        etf_rs=period_rs(etf_close,lookback_for(period,etf_close.index))
        ranking=pd.DataFrame({"ETF":sector_etfs,"Sector":[SPDR[t] for t in sector_etfs]})
        ranking["RS vs SPY %"]=ranking.ETF.map(etf_rs)
        ranking=ranking.sort_values("RS vs SPY %",ascending=False)
        bars=go.Figure(go.Bar(x=ranking["RS vs SPY %"],y=ranking["ETF"],orientation="h",
            marker_color=[color_rs(v) for v in ranking["RS vs SPY %"]],
            customdata=ranking["Sector"],hovertemplate="%{y} · %{customdata}<br>RS %{x:.2f}%<extra></extra>"))
        bars.update_layout(paper_bgcolor=PANEL,plot_bgcolor=PANEL,font=dict(color="#d8e3ee"),height=395,
                           margin=dict(l=5,r=10,t=8,b=22),xaxis=dict(title="RS vs SPY %",gridcolor=LINE),
                           yaxis=dict(autorange="reversed"))
        a,b=st.columns([2,1],gap="medium")
        with a: st.plotly_chart(bars,use_container_width=True,theme=None)
        with b:
            st.dataframe(ranking,hide_index=True,use_container_width=True,height=397,
                column_config={"RS vs SPY %":st.column_config.NumberColumn(format="%+.2f")})
    etf_pick=st.selectbox("Top holdings for sector",["All 11 ETFs"]+[f"{s} · {SPDR[s]}" for s in SPDR],index=1)
    picks=sector_etfs if etf_pick=="All 11 ETFs" else [etf_pick.split(" · ")[0]]
    with st.spinner("Loading reported Top 10 holdings…"):
        blocks=[];miss=[]
        for etf in picks:
            h,source=spdr_holdings(etf)
            if h.empty:miss.append(etf);continue
            h=h.copy();h["ETF"]=etf;h["Sector"]=SPDR[etf];h["Holdings source"]=source
            blocks.append(h)
    if miss:st.warning("Holdings not available for: "+", ".join(miss)+". No substitute holdings are invented.")
    if blocks:
        holdings=pd.concat(blocks,ignore_index=True)
        with st.spinner("Loading daily history for holdings…"):
            hclose,_=prices(tuple(list(SPDR)+list(holdings.Symbol.dropna().unique())))
        rs=period_rs(hclose,lookback_for(period,hclose.index))
        holdings["RS vs SPY %"]=holdings.Symbol.map(rs)
        holdings["RS vs ETF (pp)"]=holdings.apply(lambda r: r["RS vs SPY %"]-rs.get(r["ETF"],np.nan),axis=1)
        holdings["TradingView"]=holdings.Symbol.map(lambda s:"https://www.tradingview.com/chart/?symbol="+quote(str(s),safe=""))
        holdings=holdings.sort_values(["ETF","Weight %"],ascending=[True,False])
        st.markdown("<div class='rsm-section'>Top 10 holdings · relative leadership</div>",unsafe_allow_html=True)
        color_mode=st.radio("Color the bubbles by",["RS vs SPY %","RS vs ETF (pp)"],horizontal=True,
                            help="RS vs ETF is the difference, in percentage points, between the stock and ETF relative performance versus SPY.")
        st.markdown(spdr_bubbles(holdings,color_mode),unsafe_allow_html=True)
        st.caption("Bubble labels are stock tickers · click to open TradingView · sorted by holding weight, not by RS.")
        holdings_show=holdings[["ETF","Sector","Symbol","Weight %","RS vs SPY %","RS vs ETF (pp)","TradingView","Holdings source"]]
        st.dataframe(holdings_show,use_container_width=True,hide_index=True,height=min(620,max(230,34*len(holdings)+40)),
            column_config={"Weight %":st.column_config.NumberColumn(format="%.2f%%"),
                "RS vs SPY %":st.column_config.NumberColumn(format="%+.2f"),
                "RS vs ETF (pp)":st.column_config.NumberColumn(format="%+.2f"),
                "TradingView":st.column_config.LinkColumn("Chart",display_text="Open ↗")})
        st.download_button("⬇ Export SPDR holdings CSV",data=holdings_show.to_csv(index=False).encode("utf-8"),
            file_name="sector_spdr_top10_rs.csv",mime="text/csv")
        st.caption("ETF membership is sorted by fund weight; it is NOT a list of top performers. RS vs ETF (pp) = difference of two RS-versus-SPY percentages. Holdings may be from a different date than prices. Verify official ETF files at ssga.com.")

elif view=="SECTOR ROTATION":
    st.markdown("<div class='rsm-section'>SECTOR ROTATION · four-quadrant leadership map</div><div class='rsm-small'>Leading / Improving / Weakening / Lagging based on 20-day relative performance and change in weekly RS.</div>",unsafe_allow_html=True)
    with st.spinner("Loading sector rotation histories…"):
        etf_close,_=prices(tuple(SPDR))
    if etf_close.empty or "SPY" not in etf_close or len(etf_close)<50:
        st.warning("Insufficient daily data for sector rotation.")
    else:
        fig,rot=rotation_fig(etf_close)
        st.plotly_chart(fig,use_container_width=True,theme=None)
        if not rot.empty:
            a,b,c,d=st.columns(4)
            for widget,status in zip((a,b,c,d),("Leading","Improving","Weakening","Lagging")):
                widget.metric(status,int((rot.Rotation==status).sum()))
            rot=rot.sort_values("RS 1M %",ascending=False)
            st.dataframe(rot,use_container_width=True,hide_index=True,
                column_config={"RS 1M %":st.column_config.NumberColumn(format="%+.2f"),
                               "RS momentum pp":st.column_config.NumberColumn(format="%+.2f")})
        st.info("Custom rotation proxy — NOT an official RRG/JdK RS-Ratio or RS-Momentum. X: 21-session ETF return vs SPY. Y: latest 5-session RS minus preceding 5-session RS (percentage points). Trails are weekly observations, not predictions.")

else:
    st.markdown("<div class='rsm-section'>MINERVINI-STYLE BREAKOUT SCANNER</div><div class='rsm-small'>Screen for positive RS, improving leadership, trend alignment, RVOL and approximate directional volume. No signal guarantees an entry.</div>",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1: only_rs=st.checkbox("RS vs SPY > 0",value=True)
    with c2: only_acc=st.checkbox("RS accelerating (5D)",value=False)
    with c3: only_break=st.checkbox("New 20-day RS line high",value=False)
    with c4: only_trend=st.checkbox("Trend: price > MA50 > MA200",value=False)
    c5,c6,c7=st.columns(3)
    with c5: min_rvol=st.number_input("Minimum RVOL",min_value=0.0,max_value=20.0,value=1.0,step=.1)
    with c6: min_ud=st.number_input("Minimum U/D proxy",min_value=0.0,max_value=20.0,value=0.0,step=.1)
    with c7: min_cap=st.selectbox("Minimum market cap",["Any","$2B","$10B","$20B","$50B"],index=0)
    name=st.text_input("Search symbol or company",placeholder="e.g. PLTR").strip().upper()
    view_df=data.copy()
    if only_rs:view_df=view_df[view_df["RS %"]>0]
    if only_acc:view_df=view_df[view_df["RS acceleration"]>0]
    if only_break:view_df=view_df[view_df["RS new 20D high"]]
    if only_trend:view_df=view_df[view_df["Trend"]]
    if min_rvol>0:view_df=view_df[view_df["RVOL"]>=min_rvol]
    if min_ud>0:view_df=view_df[view_df["U/D proxy"]>=min_ud]
    if min_cap!="Any":view_df=view_df[view_df["Market Cap"]>=float(min_cap.replace("$","").replace("B",""))*1e9]
    if name:view_df=view_df[view_df["Symbol"].str.contains(name,regex=False)|view_df["Security"].fillna("").str.upper().str.contains(name,regex=False)]
    sort=st.selectbox("Sort results",["RS %","RS acceleration","RVOL","Market Cap","U/D proxy"],index=0)
    view_df=view_df.sort_values(sort,ascending=False).copy()
    view_df["TradingView"]=view_df.Symbol.map(lambda s:"https://www.tradingview.com/chart/?symbol="+quote(str(s),safe=""))
    st.caption(f"{len(view_df)} matches · {int(view_df['Minervini candidate'].sum())} meet the dashboard's simplified Minervini-style composite")
    ordered=["Symbol","Security","Sector","Industry","Cap tier","RS %","RS acceleration","RS new 20D high","Price","MA50","MA200","RVOL","U/D proxy","Trend","Minervini candidate","TradingView"]
    st.dataframe(view_df[ordered],hide_index=True,use_container_width=True,height=620,
        column_config={"Symbol":st.column_config.TextColumn("TICKER",width="small"),
            "RS %":st.column_config.NumberColumn(format="%+.2f"),
            "RS acceleration":st.column_config.NumberColumn(format="%+.2f"),
            "Price":st.column_config.NumberColumn(format="$%.2f"),
            "MA50":st.column_config.NumberColumn(format="%.2f"),
            "MA200":st.column_config.NumberColumn(format="%.2f"),
            "RVOL":st.column_config.NumberColumn(format="%.2f"),
            "U/D proxy":st.column_config.NumberColumn(format="%.2f"),
            "TradingView":st.column_config.LinkColumn("Chart",display_text="Open ↗")})
    st.download_button("⬇ Export scanner CSV",view_df.to_csv(index=False).encode("utf-8"),
                       file_name="minervini_rs_scanner.csv",mime="text/csv")
    st.caption("Simplified candidate = RS 1W>0 & RS 1M>0 & Price>MA50>MA200 & RVOL>1 & U/D proxy>1.5. It does NOT implement all original Minervini trend-template/VCP conditions; U/D is NOT the official Up/Down Volume metric.")

st.divider()
st.markdown("<span class='rsm-note'>DATA SOURCES · Constituents: public S&P 500 lists · Market cap: Nasdaq snapshot via zyhe16/top-us-stock-tickers · Price/volume: Yahoo Finance via yfinance · ETF holdings: Yahoo Finance or Stock Analysis. No execution, no brokerage credentials, no guaranteed real-time data.</span>",unsafe_allow_html=True)
