import io
import time
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title='RS Matrix + Minervini', layout='wide', page_icon='📈')
st.title('RS MATRIX · US Equities')
st.caption('Relative strength vs SPY · S&P 500 / NYSE + Nasdaq · Date indicative, NU feed consolidat real-time')

HEADERS={'User-Agent':'Mozilla/5.0 (compatible; MarketResearchDashboard/1.0)'}

@st.cache_data(ttl=86400, show_spinner=False)
def get_universe():
    sp=pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
    sp['Symbol']=sp['Symbol'].str.replace('.', '-', regex=False)
    sp=sp.rename(columns={'GICS Sector':'Sector','GICS Sub-Industry':'Industry'})
    sp=sp[['Symbol','Security','Sector','Industry']].drop_duplicates('Symbol')
    def download_table(url):
        r=requests.get(url,headers=HEADERS,timeout=25)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text),sep='|',dtype=str)
    nas=download_table('https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt')
    nas=nas[(nas['Test Issue']=='N') & (nas['Symbol'].notna())]
    nas=nas[['Symbol','Security Name']].rename(columns={'Security Name':'Security'})
    oth=download_table('https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt')
    oth=oth[(oth['Test Issue']=='N') & oth['Exchange'].isin(['N','A'])]
    oth=oth[['ACT Symbol','Security Name']].rename(columns={'ACT Symbol':'Symbol','Security Name':'Security'})
    all_us=pd.concat([nas,oth],ignore_index=True).drop_duplicates('Symbol')
    all_us['Symbol']=all_us['Symbol'].str.replace('.', '-',regex=False)
    all_us=all_us[all_us['Symbol'].str.fullmatch(r'[A-Z]{1,5}(-[A-Z])?',na=False)]
    all_us=all_us[~all_us['Security'].str.contains('ETF|ETN|Exchange Traded|Warrant|Preferred|Depositary|Units|Rights',case=False,na=False)]
    all_us=all_us.merge(sp[['Symbol','Sector','Industry']],how='left',on='Symbol')
    return sp,all_us

@st.cache_data(ttl=1800,show_spinner=False)
def prices(symbols):
    # Chunked requests, auto_adjust=True to keep returns and averages on one basis.
    output=[]
    symbols=list(dict.fromkeys(['SPY']+list(symbols)))
    for k in range(0,len(symbols),80):
        chunk=symbols[k:k+80]
        try:
            raw=yf.download(chunk,period='1y',interval='1d',auto_adjust=True,
                            progress=False,threads=True,group_by='column')
            if raw.empty: continue
            if isinstance(raw.columns,pd.MultiIndex):
                c=raw['Close'];v=raw['Volume']
            else:
                c=raw[['Close']].rename(columns={'Close':chunk[0]})
                v=raw[['Volume']].rename(columns={'Volume':chunk[0]})
            output.append((c,v))
        except Exception:
            continue
    if not output: return pd.DataFrame(),pd.DataFrame()
    return pd.concat([x[0] for x in output],axis=1).loc[:,lambda x:~x.columns.duplicated()],pd.concat([x[1] for x in output],axis=1).loc[:,lambda x:~x.columns.duplicated()]

def calculate(close,volume,lookback,sp,universe):
    close=close.ffill(limit=3)
    if 'SPY' not in close or len(close)<205: return pd.DataFrame()
    ret=close.iloc[-1]/close.shift(lookback).iloc[-1]-1
    spy_ret=ret.get('SPY',np.nan)
    rs=(1+ret)/(1+spy_ret)-1
    ma50=close.rolling(50,min_periods=50).mean().iloc[-1]
    ma200=close.rolling(200,min_periods=200).mean().iloc[-1]
    last=close.iloc[-1]
    vol=volume.reindex(columns=close.columns).fillna(0)
    rvol=vol.iloc[-1]/vol.shift(1).rolling(20,min_periods=15).mean().iloc[-1].replace(0,np.nan)
    # Up/down volume is an explicitly labelled approximate proxy from daily close-to-close changes.
    up=(close.diff()>0).tail(50)
    dn=(close.diff()<0).tail(50)
    vol50=vol.tail(50)
    uv=vol50.where(up).sum();dv=vol50.where(dn).sum()
    ud=uv/dv.replace(0,np.nan)
    data=pd.DataFrame({'Symbol':rs.index,'RS %':rs.values*100,'Return %':ret.reindex(rs.index).values*100,
                       'Price':last.reindex(rs.index).values,'MA50':ma50.reindex(rs.index).values,
                       'MA200':ma200.reindex(rs.index).values,'RVOL':rvol.reindex(rs.index).values,
                       'U/D proxy':ud.reindex(rs.index).values})
    data=data.merge(universe,on='Symbol',how='left')
    data=data[data.Symbol!='SPY'].dropna(subset=['RS %','Price'])
    data['Trend']= (data.Price>data.MA50)&(data.MA50>data.MA200)
    data['Minervini candidate']=(data['RS %']>0)&data.Trend&(data.RVOL>1)&(data['U/D proxy']>1.5)
    data['Cap tier']='Unknown (no reliable market-cap feed)'
    return data

try:
    sp,all_us=get_universe()
except Exception as e:
    st.error(f'Nu am putut descărca lista de simboluri: {e}')
    st.stop()

with st.sidebar:
    st.header('Universe & filters')
    choice=st.radio('Universe', ['S&P 500','NYSE + Nasdaq'],index=0)
    period=st.selectbox('RS window',['1D','1W','1M','3M','6M','YTD'],index=1)
    lookbacks={'1D':1,'1W':5,'1M':21,'3M':63,'6M':126,'YTD':max(1,int(np.busday_count(f'{datetime.now().year}-01-01',datetime.now().date().isoformat())))}
    positive=st.checkbox('Only outperforming SPY',False)
    minervini=st.checkbox('Minervini candidates only',False)
    symbol_search=st.text_input('Ticker search','').upper().strip()
    if choice=='NYSE + Nasdaq':
        st.warning('Whole-market mode can require thousands of Yahoo Finance requests and may be rate-limited. Use a subset for free-tier reliability.')
        limit=st.slider('Number of tickers to scan',100,min(2000,len(all_us)),500,100)
    else:
        limit=len(sp)
    run=st.button('Refresh / scan',type='primary',use_container_width=True)

universe=sp if choice=='S&P 500' else all_us.head(limit)
symbols=universe.Symbol.tolist()
if symbol_search and symbol_search not in symbols:
    st.warning('Ticker is not in the selected universe/subset.')
with st.spinner(f'Downloading daily history for {len(symbols)} symbols (cached 30 minutes)...'):
    close,volume=prices(tuple(symbols))
if close.empty:
    st.error('Price source unavailable or rate-limited. Try again later or scan fewer symbols.')
    st.stop()
data=calculate(close,volume,lookbacks[period],sp,universe)
if data.empty:
    st.error('Insufficient SPY or stock history to compute signals.')
    st.stop()
if positive:data=data[data['RS %']>0]
if minervini:data=data[data['Minervini candidate']]
if symbol_search:data=data[data.Symbol.str.contains(symbol_search,regex=False)]

st.info('Data: Yahoo Finance daily bars, delayed/variable availability. RS = stock return relative to SPY return. U/D proxy uses 50 daily close-to-close directions; it is NOT the official Up/Down Volume metric. Market-cap tiers are intentionally omitted until a reliable feed is configured.')
a,b,c,d=st.columns(4)
a.metric('Tickers with valid data',len(data))
b.metric('Outperform SPY',int((data['RS %']>0).sum()))
c.metric('Minervini candidates',int(data['Minervini candidate'].sum()))
d.metric('Latest price date',str(close.index.max().date()))

sector=data.groupby('Sector',dropna=False).agg(Mean_RS=('RS %','mean'),Count=('Symbol','count')).reset_index().fillna({'Sector':'Unclassified'})
sector=sector.sort_values('Mean_RS',ascending=False)
left,right=st.columns([1,2])
with left:
    st.subheader('Sector leadership')
    fig=px.bar(sector,x='Mean_RS',y='Sector',orientation='h',color='Mean_RS',color_continuous_scale='RdYlGn',hover_data=['Count'])
    fig.update_layout(yaxis={'categoryorder':'total ascending'},height=520,coloraxis_showscale=False,margin=dict(l=0,r=0,t=10,b=10))
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('RS matrix · Industry × Ticker')
    top=data.sort_values('RS %',ascending=False).head(120).copy()
    top['Industry']=top['Industry'].fillna('Unclassified')
    fig=px.scatter(top,x='Symbol',y='Industry',color='RS %',size=np.maximum(top['RS %'].abs(),1),
                   color_continuous_scale='RdYlGn',color_continuous_midpoint=0,
                   hover_data=['Return %','RVOL','U/D proxy','Trend'])
    fig.update_layout(height=520,xaxis={'tickangle':-70},margin=dict(l=0,r=0,t=10,b=10))
    st.plotly_chart(fig,use_container_width=True)

# --- Sector SPDR module: official sector ETFs, weighted top-ten holdings ---
SPDR_ETFS = {
    'XLK':'Technology', 'XLF':'Financials', 'XLE':'Energy',
    'XLV':'Health Care', 'XLI':'Industrials', 'XLY':'Consumer Discretionary',
    'XLP':'Consumer Staples', 'XLU':'Utilities', 'XLB':'Materials',
    'XLRE':'Real Estate', 'XLC':'Communication Services'
}

@st.cache_data(ttl=21600, show_spinner=False)
def spdr_top_holdings(ticker):
    """Fetch live provider-reported top holdings; never substitute guessed holdings."""
    # yfinance top holdings is typically already sorted by portfolio weight.
    try:
        fund = yf.Ticker(ticker).funds_data
        frame = fund.top_holdings
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            h = frame.copy()
            if 'Symbol' not in h.columns:
                h = h.reset_index().rename(columns={'index':'Symbol'})
            symcol = next((c for c in h if str(c).lower() in ('symbol','ticker','holding')),None)
            weightcol = next((c for c in h if 'holding percent' in str(c).lower() or 'weight' in str(c).lower()), None)
            if symcol and weightcol:
                out = h[[symcol,weightcol]].copy()
                out.columns = ['Symbol','Weight %']
                out['Symbol'] = out['Symbol'].astype(str).str.replace('.', '-',regex=False)
                out['Weight %'] = pd.to_numeric(out['Weight %'],errors='coerce')
                if out['Weight %'].max() <= 1.0:
                    out['Weight %'] *= 100
                out=out.dropna().sort_values('Weight %',ascending=False).head(10)
                if len(out)>=5:
                    return out, 'Yahoo Finance fund holdings (actualizare neconfirmată)'
    except Exception:
        pass
    # Alternative public source: fund holdings table. Availability may vary.
    try:
        url=f'https://stockanalysis.com/etf/{ticker.lower()}/holdings/'
        response=requests.get(url,headers=HEADERS,timeout=12)
        response.raise_for_status()
        for h in pd.read_html(io.StringIO(response.text)):
            symcol=next((c for c in h if str(c).strip().lower() in ('symbol','ticker')),None)
            weightcol=next((c for c in h if 'weight' in str(c).lower()),None)
            if symcol and weightcol:
                out=h[[symcol,weightcol]].copy()
                out.columns=['Symbol','Weight %']
                out['Symbol']=out['Symbol'].astype(str).str.replace('.', '-',regex=False)
                out['Weight %']=pd.to_numeric(out['Weight %'].astype(str).str.replace('%','',regex=False),errors='coerce')
                out=out.dropna().sort_values('Weight %',ascending=False).head(10)
                if len(out)>=5:
                    return out, f'Stock Analysis (verifică data holdings: {url})'
    except Exception:
        pass
    return pd.DataFrame(columns=['Symbol','Weight %']), 'Indisponibil: furnizorul de holdings nu a răspuns'

st.divider()
st.header('Sector SPDR · 11 ETF-uri și Top 10 holdings')
st.caption('Dețineri reale raportate de furnizori, nu estimări după market cap. Datele ETF și prețurile acțiunilor pot avea momente diferite de actualizare.')
sector_choice=st.selectbox('Analizează sectorul', ['Toate cele 11 sectoare'] + [f'{ticker} — {name}' for ticker,name in SPDR_ETFS.items()])
selected_etfs=list(SPDR_ETFS) if sector_choice.startswith('Toate') else [sector_choice.split(' ')[0]]
with st.spinner('Se încarcă deținerile și RS pentru ETF-urile sectoriale...'):
    holdings_blocks=[]
    errors=[]
    for etf in selected_etfs:
        h, source=spdr_top_holdings(etf)
        if h.empty:
            errors.append(etf)
            continue
        h=h.copy()
        h['ETF']=etf
        h['Sector SPDR']=SPDR_ETFS[etf]
        h['Holdings source']=source
        holdings_blocks.append(h)
    holdings=pd.concat(holdings_blocks,ignore_index=True) if holdings_blocks else pd.DataFrame()
    etf_symbols=list(SPDR_ETFS)
    constituent_symbols=holdings['Symbol'].dropna().unique().tolist() if not holdings.empty else []
    spdr_close,spdr_volume=prices(tuple(dict.fromkeys(etf_symbols+constituent_symbols)))

if errors:
    st.warning('Nu s-au putut verifica Top 10 holdings pentru: '+', '.join(errors)+'. Nu afișez o listă presupusă. Poți reîncerca mai târziu.')
if spdr_close.empty or 'SPY' not in spdr_close:
    st.warning('Datele de preț SPDR/SPY sunt momentan indisponibile.')
else:
    def rs_for_period(frame, days):
        if len(frame)<=days: return pd.Series(dtype=float)
        before=frame.ffill(limit=3).iloc[-days-1]
        after=frame.ffill(limit=3).iloc[-1]
        spy_start=before.get('SPY',np.nan)
        spy_end=after.get('SPY',np.nan)
        if pd.isna(spy_start) or pd.isna(spy_end) or spy_start<=0: return pd.Series(dtype=float)
        spy_return=spy_end/spy_start
        return ((after/before)/spy_return - 1)*100
    etf_rs=rs_for_period(spdr_close,lookbacks[period])
    ranking=pd.DataFrame({'ETF':etf_symbols,'Sector':[SPDR_ETFS[s] for s in etf_symbols]})
    ranking['RS vs SPY %']=ranking['ETF'].map(etf_rs)
    ranking=ranking.sort_values('RS vs SPY %',ascending=False)
    fig=px.bar(ranking,x='RS vs SPY %',y='ETF',orientation='h',color='RS vs SPY %',
               color_continuous_scale='RdYlGn',color_continuous_midpoint=0,
               hover_data=['Sector'],title=f'Sector ETF relative strength · {period}')
    fig.update_layout(yaxis={'categoryorder':'total ascending'},height=440,
                      coloraxis_showscale=False,margin=dict(l=0,r=0,t=45,b=0))
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(ranking,use_container_width=True,hide_index=True,
                 column_config={'RS vs SPY %':st.column_config.NumberColumn(format='%.2f')})
    if not holdings.empty:
        constituent_rs=rs_for_period(spdr_close,lookbacks[period])
        holdings['RS vs SPY %']=holdings['Symbol'].map(constituent_rs)
        holdings['Relative to ETF %']=holdings.apply(
            lambda row: row['RS vs SPY %']-etf_rs.get(row['ETF'],np.nan),axis=1)
        holdings=holdings.sort_values(['ETF','Weight %'],ascending=[True,False])
        st.subheader('Top 10 holdings · concentrare și leadership')
        st.caption('Top 10 după pondere în fond, NU top 10 după performanță. RS relativ la ETF este diferența dintre RS-ul acțiunii și RS-ul ETF-ului, exprimată în puncte procentuale.')
        holdings['TradingView']=holdings['Symbol'].map(lambda s:f'https://www.tradingview.com/chart/?symbol={s}')
        st.dataframe(holdings[['ETF','Sector SPDR','Symbol','Weight %','RS vs SPY %','Relative to ETF %','TradingView','Holdings source']],
                     hide_index=True,use_container_width=True,
                     column_config={'Weight %':st.column_config.NumberColumn(format='%.2f%%'),
                                    'RS vs SPY %':st.column_config.NumberColumn(format='%.2f'),
                                    'Relative to ETF %':st.column_config.NumberColumn(format='%.2f'),
                                    'TradingView':st.column_config.LinkColumn('Chart')})
        figure=px.scatter(holdings.dropna(subset=['RS vs SPY %']),x='ETF',y='Symbol',
                          size='Weight %',color='RS vs SPY %',hover_data=['Weight %','Sector SPDR'],
                          color_continuous_scale='RdYlGn',color_continuous_midpoint=0,
                          title=f'Top 10 holdings · Sector ETF matrix ({period})')
        figure.update_layout(height=max(450, 28*holdings.Symbol.nunique()),margin=dict(l=0,r=0,t=50,b=0))
        st.plotly_chart(figure,use_container_width=True)
        st.download_button('Export SPDR Top 10 CSV',holdings.to_csv(index=False).encode('utf-8'),
                           'spdr_top10_holdings_rs.csv','text/csv')
        st.caption('Sursa oficială pentru verificare: https://www.ssga.com/us/en/individual/capabilities/equities/sector-investing/select-sector-etfs. Holdings se pot modifica; data exactă trebuie verificată pe pagina fiecărui ETF.')

st.subheader('Scanner results')
columns=['Symbol','Security','Sector','Industry','RS %','Return %','Price','MA50','MA200','RVOL','U/D proxy','Trend','Minervini candidate']
st.dataframe(data.sort_values('RS %',ascending=False)[columns],use_container_width=True,hide_index=True,
             column_config={'RS %':st.column_config.NumberColumn(format='%.2f'),
                            'RVOL':st.column_config.NumberColumn(format='%.2f'),
                            'U/D proxy':st.column_config.NumberColumn(format='%.2f')})
st.download_button('Export CSV',data.to_csv(index=False).encode('utf-8'),'rs_matrix.csv','text/csv')
st.caption('Click ticker in TradingView: https://www.tradingview.com/chart/?symbol=NASDAQ%3AAAPL (replace exchange and ticker). This scanner is informational, not investment advice.')
