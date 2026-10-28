import time
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title='SAYGILI CRYPTO PRO', page_icon='📈', layout='wide')

st.markdown("""<style>
@media (max-width: 700px) {
.block-container {padding-top: 1rem; padding-left: .7rem; padding-right: .7rem;}
h1 {font-size: 1.6rem !important;}
[data-testid="stPlotlyChart"] {overflow-x: auto;}
}
</style>""", unsafe_allow_html=True)

st.title('📈 SAYGILI CRYPTO PRO')
st.caption('Binance Futures • Canlı halka açık piyasa verileri • Yalnızca simülasyon • Gerçek emir gönderilmez')
BASE='https://fapi.binance.com'

@st.cache_data(ttl=20)
def get_json(path,params=None):
    r=requests.get(BASE+path,params=params,timeout=12)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=60)
def symbols():
    d=get_json('/fapi/v1/exchangeInfo')
    return sorted([s['symbol'] for s in d['symbols'] if s.get('quoteAsset')=='USDT' and s.get('status')=='TRADING' and s.get('contractType')=='PERPETUAL'])

@st.cache_data(ttl=20)
def candles(symbol,interval):
    raw=get_json('/fapi/v1/klines',{'symbol':symbol,'interval':interval,'limit':300})
    df=pd.DataFrame(raw,columns=['time','open','high','low','close','volume','end','quotevol','trades','buyvol','buyquote','ignore'])
    for c in ['open','high','low','close','volume']:
        df[c]=pd.to_numeric(df[c])
    df['time']=pd.to_datetime(df['time'],unit='ms',utc=True)
    return df

def indicators(df):
    d=df.copy()
    d['ema20']=d.close.ewm(span=20,adjust=False).mean()
    d['ema50']=d.close.ewm(span=50,adjust=False).mean()
    delta=d.close.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    d['rsi']=100-100/(1+gain/loss.replace(0,np.nan))
    fast=d.close.ewm(span=12,adjust=False).mean(); slow=d.close.ewm(span=26,adjust=False).mean()
    d['macd']=fast-slow;d['signal']=d.macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()],axis=1).max(axis=1)
    d['atr']=tr.ewm(alpha=1/14,adjust=False).mean()
    d['resistance']=d.high.shift(1).rolling(20).max()
    d['support']=d.low.shift(1).rolling(20).min()
    d['volume_avg']=d.volume.shift(1).rolling(20).mean()
    return d

def signal(d):
    # Use last CLOSED candle only; last row is generally forming.
    a=d.iloc[-2];b=d.iloc[-3]
    bull=int(a.ema20>a.ema50)+int(a.macd>a.signal)+int(a.rsi>50)+int(a.close>a.resistance if pd.notna(a.resistance) else False)+int(a.volume>1.5*a.volume_avg if pd.notna(a.volume_avg) else False)
    bear=int(a.ema20<a.ema50)+int(a.macd<a.signal)+int(a.rsi<50)+int(a.close<a.support if pd.notna(a.support) else False)+int(a.volume>1.5*a.volume_avg if pd.notna(a.volume_avg) else False)
    side='LONG' if bull>=4 and bull>bear else ('SHORT' if bear>=4 and bear>bull else 'BEKLE')
    return side,bull,bear,a

try:
    syms=symbols()
except Exception as e:
    st.error('Binance Futures verilerine ulaşılamadı. Bölgesel erişim veya ağ kısıtı olabilir: '+str(e))
    st.stop()

with st.sidebar:
    st.header('⚙️ Kontroller')
    symbol=st.selectbox('USDT perpetual sözleşmesi',syms,index=syms.index('BTCUSDT') if 'BTCUSDT' in syms else 0)
    interval=st.selectbox('Zaman dilimi',['1m','5m','15m','1h','4h','1d'],index=2)
    leverage=st.select_slider('Kaldıraç (simülasyon)',options=[2,3,5,10,20,25,50,75,100,125],value=5)
    margin=st.number_input('Teminat (USDT)',min_value=1.0,value=10.0,step=1.0)
    fee=st.number_input('Tek yön varsayımsal komisyon (%)',min_value=0.0,max_value=1.0,value=0.05,step=0.01)
    st.warning('Kaldıraç seçenekleri temsili. Binance her sözleşme ve hesap için bu seviyeleri desteklemeyebilir.')
    if st.button('🔄 Veriyi yenile'):
        get_json.clear();candles.clear();st.rerun()

try:
    df=indicators(candles(symbol,interval))
    book=get_json('/fapi/v1/depth',{'symbol':symbol,'limit':100})
    premium=get_json('/fapi/v1/premiumIndex',{'symbol':symbol})
    oi=get_json('/fapi/v1/openInterest',{'symbol':symbol})
except Exception as e:
    st.error('Piyasa verisi alınamadı: '+str(e));st.stop()

side,bull,bear,a=signal(df)
last=float(df.close.iloc[-1]);support=float(a.support);resistance=float(a.resistance);atr=float(a.atr)
bid_notional=sum(float(p)*float(q) for p,q in book['bids']);ask_notional=sum(float(p)*float(q) for p,q in book['asks'])
imbalance=(bid_notional-ask_notional)/(bid_notional+ask_notional)*100 if bid_notional+ask_notional else 0
c1,c2,c3,c4=st.columns(4)
c1.metric('Son fiyat',f'{last:,.6g} USDT');c2.metric('Kapalı mum sinyali',side);c3.metric('RSI (14)',f'{a.rsi:.1f}');c4.metric('Emir defteri dengesizliği',f'{imbalance:+.1f}%')
st.caption('Sinyal yalnızca kapanmış mumdan hesaplanır. Emir defteri anlık görüntüdür; balina kimliği veya kesin yön tahmini değildir.')
fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.04,row_heights=[.75,.25])
fig.add_trace(go.Candlestick(x=df.time,open=df.open,high=df.high,low=df.low,close=df.close,name='Fiyat'),row=1,col=1)
for name,color in [('ema20','#ffbb33'),('ema50','#4ea5ff')]:
    fig.add_trace(go.Scatter(x=df.time,y=df[name],name=name.upper(),line=dict(color=color,width=1.5)),row=1,col=1)
fig.add_hline(y=support,line_dash='dash',line_color='#26a69a',annotation_text='Destek (20)',row=1,col=1)
fig.add_hline(y=resistance,line_dash='dash',line_color='#ef5350',annotation_text='Direnç (20)',row=1,col=1)
fig.add_trace(go.Bar(x=df.time,y=df.volume,name='Hacim',marker_color='#8494a7'),row=2,col=1)
fig.update_layout(height=650,xaxis_rangeslider_visible=False,template='plotly_dark',legend_orientation='h',margin=dict(l=10,r=10,t=20,b=10))
st.plotly_chart(fig,use_container_width=True)

left,right=st.columns(2)
with left:
    st.subheader('📊 Teknik analiz')
    st.write(f'EMA20: **{a.ema20:.6g}** · EMA50: **{a.ema50:.6g}**')
    st.write(f'MACD: **{a.macd:.6g}** · Sinyal: **{a.signal:.6g}**')
    st.write(f'Destek: **{support:.6g}** · Direnç: **{resistance:.6g}** · ATR: **{atr:.6g}**')
    st.write(f'LONG koşulları: **{bull}/5** · SHORT koşulları: **{bear}/5**')
    st.info('Fincan-kulp, Elliott ve karmaşık formasyonların güvenilir otomatik tespiti henüz uygulanmadı; ilk sürüm EMA/RSI/MACD/hacim/kırılım kullanır.')
with right:
    st.subheader('🐋 Likidite izleme')
    st.write(f'İlk 100 seviye alış emir değeri: **{bid_notional:,.0f} USDT**')
    st.write(f'İlk 100 seviye satış emir değeri: **{ask_notional:,.0f} USDT**')
    st.write(f'Açık pozisyon (kontrat miktarı): **{float(oi["openInterest"]):,.2f}**')
    st.write(f'Fonlama oranı: **{float(premium["lastFundingRate"])*100:.4f}%**')
    st.caption('Büyük emirler iptal edilebilir; bu veriler manipülasyon kanıtı değildir. OI tek anlık değerdir, değişim analizi değildir.')

st.subheader('🧪 Onaylı SANAL işlem')
if 'trades' not in st.session_state: st.session_state.trades=[]
if 'pending' not in st.session_state: st.session_state.pending=None
col1,col2,col3=st.columns(3)
with col1: direction=st.selectbox('Yön',['LONG','SHORT'],index=0 if side!='SHORT' else 1)
with col2: stop_distance=st.number_input('Stop mesafesi (%)',min_value=.1,max_value=50.,value=2.,step=.1)
with col3: take_distance=st.number_input('Kâr hedefi (%)',min_value=.1,max_value=100.,value=4.,step=.1)
notional=margin*leverage
risk_gross=margin*leverage*stop_distance/100
reward_gross=margin*leverage*take_distance/100
roundtrip_fee=notional*fee/100*2
st.write(f'Pozisyon: **{notional:.2f} USDT** · Stopta tahmini PnL: **−{risk_gross+roundtrip_fee:.2f} USDT** · Hedefte tahmini PnL: **+{reward_gross-roundtrip_fee:.2f} USDT**')
st.warning('Likidasyon, fonlama, slippage, marjin gereksinimleri ve stopun garanti edilmemesi bu basit hesapta modellenmiyor. 50x–125x özellikle tehlikelidir.')
if st.button('📋 Sanal işlem için onay iste'):
    st.session_state.pending=dict(symbol=symbol,direction=direction,leverage=leverage,margin=margin,entry=last,stop=last*(1-stop_distance/100 if direction=='LONG' else 1+stop_distance/100),take=last*(1+take_distance/100 if direction=='LONG' else 1-take_distance/100),fee=fee,time=pd.Timestamp.now(tz='UTC').isoformat())
if st.session_state.pending:
    p=st.session_state.pending
    st.info(f'ONAY BEKLİYOR: {p["symbol"]} {p["direction"]} {p["leverage"]}x | Giriş {p["entry"]:.6g} | Stop {p["stop"]:.6g} | Hedef {p["take"]:.6g}')
    yes,no=st.columns(2)
    if yes.button('✅ SANAL işlemi onayla'):
        st.session_state.trades.append({**p,'status':'AÇIK','exit':None,'pnl':None});st.session_state.pending=None;st.rerun()
    if no.button('❌ İptal et'):
        st.session_state.pending=None;st.rerun()

if st.session_state.trades:
    st.subheader('📒 Sanal işlem defteri')
    for i,t in enumerate(st.session_state.trades):
        if t['status']=='AÇIK':
            st.write(f'#{i+1} {t["symbol"]} {t["direction"]} {t["leverage"]}x — giriş {t["entry"]:.6g}')
            if st.button(f'#{i+1} işlemi güncel fiyatla sanal kapat',key=f'close{i}'):
                try:
                    price=float(get_json('/fapi/v1/ticker/price',{'symbol':t['symbol']})['price'])
                    sign=1 if t['direction']=='LONG' else -1
                    gross=t['margin']*t['leverage']*sign*(price/t['entry']-1)
                    fees=(t['margin']*t['leverage']+t['margin']*t['leverage']*price/t['entry'])*t['fee']/100
                    t.update(status='KAPALI',exit=price,pnl=round(gross-fees,4));st.rerun()
                except Exception as e: st.error(str(e))
    st.dataframe(pd.DataFrame(st.session_state.trades),use_container_width=True)
    st.download_button('📥 İşlem geçmişini CSV indir',pd.DataFrame(st.session_state.trades).to_csv(index=False).encode('utf-8-sig'),'sanal_islemler.csv','text/csv')
    st.caption('Sanal işlemler yalnızca mevcut Streamlit oturumunda tutulur. Stop/hedef otomatik tetiklenmez; pozisyonlar manuel sanal kapatılır.')

st.divider()
st.caption('Güvenlik: API anahtarı istemez, saklamaz veya Binance hesabına emir göndermez. Finansal tavsiye değildir.')
