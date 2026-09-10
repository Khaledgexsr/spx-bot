import os, time, threading, yfinance as yf, requests
import matplotlib.pyplot as plt
from flask import Flask
from io import BytesIO
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot 50K Fixed"

def send_chart():
    try:
        # حل مشكلة 429 - نستخدم session جديد
        for attempt in range(3):
            try:
                spx = yf.download("^GSPC", period="1d", interval="1m", progress=False, auto_adjust=True)
                spy = yf.download("SPY", period="1d", interval="1m", progress=False, auto_adjust=True)
                if not spx.empty: break
            except:
                time.sleep(2)

        if spx.empty:
            print("No data after retry - Yahoo blocked")
            # ارسل رسالة تنبيه ان ياهو مبلك
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": "⚠️ Yahoo بلوك مؤقت 429 - بيحاول بعد شوي"})
            return

        price = float(spx['Close'].iloc[-1])
        open_price = float(spx['Close'].iloc[0])
        change = (price - open_price) / open_price * 100

        vol = spy['Volume'] if not spy.empty else spx['Volume']
        avg_vol = vol.mean()
        last_vol = int(vol.iloc[-1])

        spy['typical'] = (spy['High'] + spy['Low'] + spy['Close']) / 3
        spy['vwap'] = (spy['typical'] * spy['Volume']).cumsum() / spy['Volume'].cumsum()
        vwap = float(spy['vwap'].iloc[-1])
        high_vol_price = float(spy.loc[spy['Volume'].idxmax()]['Close']) if not spy.empty else price

        MIN_VOL = 50000
        if last_vol < MIN_VOL:
            signal = f"⚪ لا دخول - الفوليوم {last_vol:,} < 50K"
            action = f"انتظر > 50K | VWAP {vwap:.2f}"
        elif price > vwap and price > high_vol_price:
            signal = f"🟢 CALL - Vol {last_vol:,}"
            action = f"هدف {price+5:.0f} | وقف {vwap:.0f}"
        elif price < vwap and price < high_vol_price:
            signal = f"🔴 PUT - Vol {last_vol:,}"
            action = f"هدف {price-5:.0f} | وقف {vwap:.0f}"
        else:
            signal = f"⚪ انتظار - Vol {last_vol:,}"
            action = f"VWAP {vwap:.2f}"

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5),
            gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.05}, facecolor='black')
        ax1.plot(spx['Close'], color='#00ff82', linewidth=1.2)
        ax1.axhline(vwap, color='yellow', linestyle='--', linewidth=0.8)
        ax1.set_facecolor('black')
        ax1.tick_params(colors='#666666', labelsize=7)
        ax1.set_title(f'SPX {price:.2f} ({change:+.2f}%)', color='white', fontsize=9)
        for s in ax1.spines.values(): s.set_visible(False)

        colors = ['#00ff82' if c >= o else '#ff3b3b' for c, o in zip(spy['Close'], spy['Open'])]
        ax2.bar(spy.index, spy['Volume'], color=colors, alpha=0.6, width=0.0006)
        ax2.axhline(MIN_VOL, color='red', linewidth=1, label='50K')
        ax2.set_facecolor('black')
        ax2.tick_params(colors='#666666', labelsize=7)
        for s in ax2.spines.values(): s.set_visible(False)

        buf = BytesIO()
        plt.savefig(buf, format='png', facecolor='black', dpi=200, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        caption = f"{signal}\n{action}\n\nSPX {price:.2f} {datetime.now().strftime('%H:%M')}\nVol: {last_vol:,} | Avg: {int(avg_vol):,}"
        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": buf})
        print(f"Sent {r.status_code} Vol {last_vol}")

    except Exception as e:
        print(f"Error {e}")

def loop():
    print("Loop started - 50K Rule FIXED")
    time.sleep(5)
    send_chart() # يرسل الحين حتى لو السوق مقفل للتجربة
    while True:
        time.sleep(60)
        send_chart() # شلت شرط الوقت عشان تجربه الحين

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
