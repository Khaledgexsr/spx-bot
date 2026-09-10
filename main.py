import os, time, threading, yfinance as yf, requests
import matplotlib.pyplot as plt
from flask import Flask
from io import BytesIO
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot 50K Rule Running"

def send_chart():
    try:
        spx = yf.download("^GSPC", period="1d", interval="1m", progress=False)
        spy = yf.download("SPY", period="1d", interval="1m", progress=False)
        if spx.empty or spy.empty:
            print("No data")
            return

        price = float(spx['Close'].iloc[-1])
        open_price = float(spx['Close'].iloc[0])
        change = (price - open_price) / open_price * 100

        vol = spy['Volume']
        avg_vol = vol.mean()
        last_vol = int(vol.iloc[-1])

        # VWAP
        spy['typical'] = (spy['High'] + spy['Low'] + spy['Close']) / 3
        spy['vwap'] = (spy['typical'] * spy['Volume']).cumsum() / spy['Volume'].cumsum()
        vwap = float(spy['vwap'].iloc[-1])

        # اقوى مستوى فوليوم
        high_vol_price = float(spy.loc[spy['Volume'].idxmax()]['Close'])

        # ===== قاعدة 50K الذهبية =====
        MIN_VOL = 50000
        signal = ""
        action = ""

        if last_vol < MIN_VOL:
            signal = f"⚪ لا دخول\nالسبب: الفوليوم {last_vol:,} أقل من 50K"
            action = f"انتظر فوليوم > 50K | VWAP: {vwap:.2f}"
        elif price > vwap and price > high_vol_price:
            signal = f"🟢 دخول CALL - فوليوم {last_vol:,}\nالسبب: فوق VWAP + فوق مستوى الفوليوم + فوق 50K"
            action = f"الهدف: {price+5:.0f} | الوقف: {vwap:.0f}"
        elif price < vwap and price < high_vol_price:
            signal = f"🔴 دخول PUT - فوليوم {last_vol:,}\nالسبب: تحت VWAP + تحت مستوى الفوليوم + فوق 50K"
            action = f"الهدف: {price-5:.0f} | الوقف: {vwap:.0f}"
        else:
            signal = f"⚪ انتظار حول VWAP\nفوليوم {last_vol:,} فوق 50K لكن السعر متردد"
            action = f"VWAP: {vwap:.2f} | مستوى الفوليوم: {high_vol_price:.2f}"

        # الرسم - ستايل اسود مثل صورتك
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5),
            gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.05}, facecolor='black')

        ax1.plot(spx['Close'], color='#00ff82', linewidth=1.2)
        ax1.axhline(vwap, color='yellow', linestyle='--', linewidth=0.8, alpha=0.7, label='VWAP')
        ax1.axhline(high_vol_price, color='white', linestyle=':', linewidth=0.8, alpha=0.5)
        ax1.set_facecolor('black')
        ax1.tick_params(colors='#666666', labelsize=7)
        ax1.set_title(f'SPX {price:.2f} ({change:+.2f}%) | VWAP {vwap:.2f}', color='white', fontsize=9)
        for s in ax1.spines.values(): s.set_visible(False)

        colors = ['#00ff82' if c >= o else '#ff3b3b' for c, o in zip(spy['Close'], spy['Open'])]
        ax2.bar(spy.index, spy['Volume'], color=colors, alpha=0.6, width=0.0006)
        ax2.axhline(avg_vol, color='#666666', linestyle='--', linewidth=0.5)
        ax2.axhline(MIN_VOL, color='red', linestyle='-', linewidth=1, alpha=0.8, label='50K')
        ax2.set_facecolor('black')
        ax2.tick_params(colors='#666666', labelsize=7)
        ax2.set_ylabel(f'VOL >50K', color='#666666', fontsize=7)
        for s in ax2.spines.values(): s.set_visible(False)

        buf = BytesIO()
        plt.savefig(buf, format='png', facecolor='black', dpi=200, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        time_str = datetime.now().strftime("%H:%M")
        caption = f"{signal}\n{action}\n\nSPX {price:.2f} {time_str}\nVol: {last_vol:,} | Avg: {int(avg_vol):,}\n\n⚠️ للتعليم فقط"

        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": buf})
        print(f"Sent {r.status_code} | Vol {last_vol} | Signal {signal[:20]}")

    except Exception as e:
        print(f"Error {e}")

def loop():
    print("Loop started - 50K Rule")
    time.sleep(5)
    send_chart()
    while True:
        time.sleep(60)
        now = datetime.now()
        if 16 <= now.hour <= 23: # وقت السوق السعودي
            send_chart()

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
