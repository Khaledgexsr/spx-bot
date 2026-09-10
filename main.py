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
def home(): return "Premium Bot - Market Hours Only"

def is_market_open():
    now = datetime.now()
    # السوق من 4:30 عصر ل 11 ليل بتوقيت السعودية
    # 9:30 صباح ل 4 مساء بتوقيت نيويورك
    if now.weekday() >= 5: # سبت و أحد مقفل
        return False
    hour = now.hour
    minute = now.minute
    # 16:30 الى 23:00
    if hour < 16 or hour >= 23:
        return False
    if hour == 16 and minute < 30:
        return False
    return True

def get_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    price = 7657.0
    vol_1m = 0
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1m&range=1d",
                         headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()['chart']['result'][0]
            quotes = res['indicators']['quote'][0]
            closes = [c for c in quotes['close'] if c]
            volumes = quotes['volume']
            if closes:
                price = float(closes[-1]) * 10 # SPY to SPX approx
            for v in reversed(volumes):
                if v and v > 0:
                    vol_1m = int(v)
                    break
    except:
        pass

    try:
        spx = yf.Ticker("SPY")
        exps = spx.options[:1]
        all_data = []
        if exps:
            chain = spx.option_chain(exps[0])
            for df in [chain.calls, chain.puts]:
                df_f = df[(df['strike'] >= (price/10)-20) & (df['strike'] <= (price/10)+20)]
                for _, row in df_f.iterrows():
                    v = row['volume']
                    if pd.isna(v) or v==0:
                        v = row['openInterest']
                    if pd.notna(v) and v>0:
                        all_data.append({'strike': int(row['strike']*10), 'volume': float(v)})
        if all_data:
            df_vol = pd.DataFrame(all_data).groupby('strike')['volume'].sum().reset_index().sort_values('strike')
        else:
            df_vol = None
    except:
        df_vol = None

    if df_vol is None or df_vol.empty:
        base = int(price)
        df_vol = pd.DataFrame({
            'strike':[base-40, base-25, base-15, base-10, base-5, base+5, base+15, base+25, base+35, base+45],
            'volume':[461, 638, 406, 820, 610, 980, 1340, 1120, 945, 820]
        })
    return price, vol_1m, df_vol

def plot_premium(price, df_vol):
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='black')
    ax.set_facecolor('black')
    max_vol = float(df_vol['volume'].max())

    # ألوان متدرجة ذهبي لأزرق فخم
    for i, (idx, row) in enumerate(df_vol.iterrows()):
        strike = int(row['strike'])
        v = int(row['volume'])
        width = v / max_vol * 0.75

        # لون متدرج حسب القوة
        ratio = v / max_vol
        # ذهبي (قليل) -> سماوي (كثير)
        r = int(255 - ratio*150)
        g = int(200 + ratio*30)
        b = int(50 + ratio*180)
        color = f'#{r:02x}{g:02x}{b:02x}'

        # بار دائري فخم
        bar = FancyBboxPatch((0.05, strike-1.8), width, 3.2,
                             boxstyle="round,pad=0.1,rounding_size=1.5",
                             facecolor=color, edgecolor='none', alpha=0.95)
        ax.add_patch(bar)
        ax.text(0.05+width+0.02, strike, str(v), color='white', va='center', fontsize=9)

    # خطين أنيقين فقط
    strikes = df_vol['strike'].values
    xs = np.linspace(0.05, 0.85, 50)
    xp = np.linspace(0.05, 0.85, len(strikes))
    y_green = np.interp(xs, xp, strikes[::-1])
    y_red = np.interp(xs, xp, strikes)

    ax.plot(xs, y_green, color='#00FF7F', lw=1.5, alpha=0.9)
    ax.plot(xs, y_red, color='#FF4D4D', lw=1.2, alpha=0.9)

    # مستويات CALL/PUT فقط المهمة
    for lvl in df_vol['strike'].values:
        if lvl in df_vol.nlargest(3, 'volume')['strike'].values:
            is_call = lvl > price
            c = '#00FF7F' if is_call else '#FF6B6B'
            ax.axhline(lvl, color=c, ls='--', lw=0.8, alpha=0.5)
            label = f"{'CALL' if is_call else 'PUT'} {int(lvl)}"
            ax.text(0.88, lvl, label, color=c, fontsize=9, weight='bold', va='center')

    ax.set_ylim(price-50, price+50)
    ax.set_xlim(0, 1.05)
    ax.set_yticks(df_vol['strike'])
    ax.set_yticklabels([str(int(s)) for s in df_vol['strike']], color='#00E5FF', fontsize=10)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    for sp in ax.spines.values():
        sp.set_visible(False)

    # السعر تحت كبير فخم
    fig.text(0.5, 0.01, f"{int(price):,}", ha='center', color='#FFD700', fontsize=28, weight='bold', fontfamily='monospace')

    buf = BytesIO()
    plt.savefig(buf, format='png', facecolor='black', dpi=220, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def loop():
    print("PREMIUM LOOP - Market Hours Only")
    while True:
        try:
            if not is_market_open():
                print(f"Market Closed - Sleep {datetime.now().strftime('%H:%M')}")
                time.sleep(300) # ينام 5 دقايق اذا السوق مقفل
                continue

            price, vol_1m, df_vol = get_data()

            # قاعدة 50K
            if vol_1m < 50000:
                print(f"Low Vol {vol_1m} < 50K - Skip")
                time.sleep(60)
                continue

            chart = plot_premium(price, df_vol)
            top = df_vol.nlargest(1, 'volume').iloc[0]
            caption = f"📊 SPX {int(price)} | Vol {vol_1m:,}\n🎯 Strongest: {int(top['strike'])} ({int(top['volume'])})\n⏰ {datetime.now().strftime('%H:%M')} KSA"

            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": chart})
            print(f"Sent Premium {price}")

        except Exception as e:
            print(f"Err {e}")
        time.sleep(180) # كل 3 دقايق بس وقت السوق

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
