import os, time, requests, threading
from flask import Flask
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("AAFfZ7_4AowjTRgYS7qLMWS2RRXAyA8JXik")
CHAT_ID = os.getenv("955971198")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is alive!"

def check_and_send():
    try:
        spx = yf.Ticker("^GSPC")
        df = spx.history(period="1d", interval="5m")
        if df.empty: 
            print("No data - retry later")
            return
        last = float(df['Close'].iloc[-1])
        prev = float(df['Close'].iloc[-2]) if len(df)>1 else last
        change = ((last-prev)/prev*100) if prev else 0
        vol = float(df['Volume'].iloc[-1])

        plt.figure(figsize=(10,5))
        plt.style.use('dark_background')
        plt.plot(df['Close'].tail(100), color='#00ff88', linewidth=2)
        plt.title(f"SPX {last:.2f} ({change:+.2f}%)", color='white')
        plt.grid(alpha=0.2)
        plt.tight_layout()
        plt.savefig("/tmp/chart.png")
        plt.close()

        caption = f"📊 *SPX Update* {datetime.now().strftime('%H:%M KSA')}\n*السعر:* {last:.2f} ({change:+.2f}%)\n*الفوليوم:* {vol:,.0f}\n\n[TradingView](https://www.tradingview.com/chart/?symbol=SPX)"
        with open("/tmp/chart.png","rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id":CHAT_ID,"caption":caption,"parse_mode":"Markdown"},
                files={"photo":f})
            print(f"Sent {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

def loop():
    time.sleep(5)
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id":CHAT_ID,"text":"✅ بوت SPX اشتغل"})
        print("Start msg sent")
    except Exception as e:
        print(f"Start fail {e}")
    while True:
        check_and_send()
        time.sleep(300)

threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
