import os, time, threading, requests
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
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
def home(): return "MGT - General Idea Clusters"

def is_market_open():
    now = datetime.now()
    if now.weekday() >= 5: return False
    h, m = now.hour, now.minute
    if h < 16 or h >= 23: return False
    if h == 16 and m < 30: return False
    return True

def get_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    price = 7657.0
    vol_1m = 0
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1m&range=1d", headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()['chart']['result'][0]
            q = res['indicators']['quote'][0]
            closes = [c for c in q['close'] if c]
            vols = q['volume']
            if closes: price = float(closes[-1]) * 10
            for v in reversed(vols):
                if v and v > 0:
                    vol_1m = int(v)
                    break
    except: pass

    try:
        spx = yf.Ticker("SPY")
        exps = spx.options[:1]
        all_data = []
        if exps:
            chain = spx.option_chain(exps[0])
            for df in [chain.calls, chain.puts]:
                df_f = df[(df['strike'] >= price/10-30) & (df['strike'] <= price/10+30)]
                for _, row in df_f.iterrows():
                    v = row['volume']
                    if pd.isna(v) or v==0: v = row['openInterest']
                    if pd.notna(v) and v>0:
                        all_data.append({'strike': int(row['strike']*10), 'volume': float(v)})
        if all_data:
            df_vol = pd.DataFrame(all_data).groupby('strike')['volume'].sum().reset_index().sort_values('strike')
        else: df_vol = None
    except: df_vol = None

    if df_vol is None or df_vol.empty:
        base = int(price)
        df_vol = pd.DataFrame({
            'strike':[base-35, base-20, base-10, base+10, base+20, base+35, base+50],
            'volume':[461, 820, 945, 980, 1340, 1120, 720]
        })
    return price, vol_1m, df_vol

def plot_premium(price, df_vol):
    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor='black')
    ax.set_facecolor('black')
    max_vol = float(df_vol['volume'].max())

    for _, row in df_vol.iterrows():
        strike = int(row['strike'])
        v = int(row['volume'])
        width = v / max_vol * 0.78
        ratio = v / max_vol
        r_c = int(255 - ratio*120)
        g_c = int(190 + ratio*50)
        b_c = int(50 + ratio*170)
        color = f'#{r_c:02x}{g_c:02x}{b_c:02x}'
        bar = FancyBboxPatch((0.05, strike-1.5), width, 2.6, boxstyle="round,pad=0.1,rounding_size=1.4", facecolor=color, edgecolor='none', alpha=0.95)
        ax.add_patch(bar)
        ax.text(0.05+width+0.02, strike, str(v), color='white', va='center', fontsize=8)

    ax.set_ylim(price-45, price+55)
    ax.set_xlim(0, 1.15)
    ax.set_yticks(df_vol['strike'])
    ax.set_yticklabels([str(int(s)) for s in df_vol['strike']], color='#00E5FF', fontsize=10)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    fig.text(0.5, 0.01, f"{int(price):,}", ha='center', color='#FFD700', fontsize=24, weight='bold')
    buf = BytesIO()
    plt.savefig(buf, format='png', facecolor='black', dpi=200, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def loop():
    while True:
        try:
            if not is_market_open():
                time.sleep(300)
                continue

            price, vol_1m, df_vol = get_data()
            if vol_1m < 50000:
                print(f"Low vol {vol_1m}")
                time.sleep(60)
                continue

            # الفكرة العامة - كتل
            df_top = df_vol.nlargest(5, 'volume')
            puts_cluster = sorted(df_top[df_top['strike'] < price]['strike'].tolist())
            calls_cluster = sorted(df_top[df_top['strike'] > price]['strike'].tolist())

            puts_range = f"{min(puts_cluster)} - {max(puts_cluster)}" if puts_cluster else "لا يوجد"
            calls_range = f"{min(calls_cluster)} - {max(calls_cluster)}" if calls_cluster else "لا يوجد"

            # تحديد الاتجاه العام
            total_put_vol = df_vol[df_vol['strike'] < price]['volume'].sum()
            total_call_vol = df_vol[df_vol['strike'] > price]['volume'].sum()

            if total_put_vol > total_call_vol * 1.2:
                bias = "🔴 ضغط بيعي - كميات PUT أعلى"
            elif total_call_vol > total_put_vol * 1.2:
                bias = "🟢 ضغط شرائي - كميات CALL أعلى"
            else:
                bias = "⚪ متوازن"

            msg = f"""📊 SPX {int(price)} | فوليوم {vol_1m//1000}K
{bias}

🔴 كتلة PUT قوية: {puts_range} ({len(puts_cluster)} سترايكات)
🟢 كتلة CALL قوية: {calls_range} ({len(calls_cluster)} سترايكات)

💡 الفكرة العامة:
- الكميات فوق السعر = مقاومة
- الكميات تحت السعر = دعم
- انتظر كسر الكتلة كاملة بفوليوم >50K

⏰ {datetime.now().strftime('%H:%M')} KSA
"""

            chart = plot_premium(price, df_vol)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": msg},
                files={"photo": chart})

        except Exception as e:
            print(e)
        time.sleep(180)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
