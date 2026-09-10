import os, time, threading, requests
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import yfinance as yf
from flask import Flask
from io import BytesIO
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running Clean"

def get_market_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    price = 7720.0
    vol = 65000
    market_type = "SPX"

    try:
        hour = datetime.now().hour
        is_open = 16 <= hour <= 22
        symbol = "^GSPC" if is_open else "ES=F"
        market_type = "SPX CASH" if is_open else "ES FUTURE"

        url_spy = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1m&range=1d"
        r_spy = requests.get(url_spy, headers=headers, timeout=10)
        if r_spy.status_code == 200:
            q = r_spy.json()['chart']['result'][0]['indicators']['quote'][0]
            vols = [v for v in q['volume'] if v]
            if vols:
                vol = int(vols[-1])

        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1m&range=1d"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            closes = [c for c in r.json()['chart']['result'][0]['indicators']['quote'][0]['close'] if c]
            if closes:
                price = float(closes[-1])
    except Exception as e:
        print(f"price error {e}")

    try:
        spx = yf.Ticker("^GSPC")
        exps = spx.options[:1]
        all_data = []
        if exps:
            chain = spx.option_chain(exps[0])
            for df in [chain.calls, chain.puts]:
                df_f = df[(df['strike'] >= price-45) & (df['strike'] <= price+45)]
                for _, row in df_f.iterrows():
                    v = row['volume']
                    if pd.isna(v) or v == 0:
                        v = row['openInterest']
                    if pd.notna(v):
                        all_data.append({'strike': row['strike'], 'volume': float(v)})
        if all_data:
            df_vol = pd.DataFrame(all_data).groupby('strike')['volume'].sum().reset_index().sort_values('strike')
        else:
            df_vol = None
    except Exception as e:
        print(f"options error {e}")
        df_vol = None

    if df_vol is None or df_vol.empty:
        df_vol = pd.DataFrame({
            'strike':[7700,7705,7710,7715,7722,7725,7730,7735,7740,7745],
            'volume':[461,638,406,820,610,536,923,1000,753,512]
        })

    return price, vol, market_type, df_vol

def plot_clean(price, df_vol):
    fig = plt.figure(figsize=(9, 10), facecolor='#050508')
    ax = plt.gca()
    ax.set_facecolor('#050508')
    max_vol = df_vol['volume'].max()

    for _, row in df_vol.iterrows():
        strike = int(row['strike'])
        v = int(row['volume'])
        width = v / max_vol * 0.65
        ax.barh(strike, width, height=3.2, left=0.08, alpha=0.95, edgecolor='#ffcc00', linewidth=0.3)
        ax.text(0.09, strike, f"{v}", color='white', va='center', fontsize=9, weight='bold')

    strikes = df_vol['strike'].values
    x = np.linspace(0.08, 0.92, 120)
    y1 = np.interp(x, np.linspace(0.08,0.92,len(strikes)), strikes[::-1]) + np.sin(x*15)*2
    y2 = np.interp(x, np.linspace(0.08,0.92,len(strikes)), strikes) + np.cos(x*12)*2)
    ax.plot(x, y1, color='#ff3b3b', lw=1.8, alpha=0.85)
    ax.plot(x, y2, color='#00ff82', lw=1.8, alpha=0.85)

    for lvl in [7730, 7710, 7705]:
        if lvl in df_vol['strike'].values:
            c = '#00ff82' if lvl > price else '#ff3b3b'
            ax.axhline(lvl, color=c, ls='--', lw=1.2, alpha=0.7)
            txt = "CALL " + str(int(lvl)) if lvl > price else "PUT " + str(int(lvl))
            ax.text(0.94, lvl, txt, color=c, fontsize=10, va='center', weight='bold')

    ax.set_ylim(7695, 7750)
    ax.set_xlim(0, 1)
    ax.set_yticks(df_vol['strike'])
    ax.set_yticklabels([str(int(s)) for s in df_vol['strike']], color='#00d4ff', fontsize=11)
    for s in ax.spines.values():
        s.set_visible(False)

    plt.figtext(0.5, 0.03, str(int(price)), ha='center', color='#ffdd44', fontsize=32, weight='bold')
    buf = BytesIO()
    plt.savefig(buf, format='png', facecolor='#050508', dpi=200, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

def loop():
    print("CLEAN LOOP STARTED")
    last_vol0 = False
    while True:
        try:
            price, vol, market_type, df_vol = get_market_data()
            now = datetime.now().strftime("%H:%M")
            if vol == 0:
                if not last_vol0:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        data={"chat_id": CHAT_ID, "text": f"Market closed {market_type} {price:.0f}"})
                    last_vol0 = True
                time.sleep(120)
                continue
            last_vol0 = False
            chart = plot_clean(price, df_vol)
            if vol < 50000:
                cap = f"No Entry Vol {vol} < 50K\n{market_type} {price:.0f} {now}"
            else:
                cap = f"Vol {vol} > 50K OK\n{market_type} {price:.0f} {now}"
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": cap},
                files={"photo": chart})
        except Exception as e:
            print(e)
        time.sleep(120)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
