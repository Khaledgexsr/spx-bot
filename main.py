import os, time, requests, threading
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is alive!"

def check_and_send():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=5m&range=1d"
        r = requests.get(url, headers=headers, timeout=15)
        print(f"Yahoo status: {r.status_code}")
        j = r.json()['chart']['result'][0]
        closes = j['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            print("Not enough data")
            return
        last = closes[-1]
        prev = closes[-2]
        change = (last-prev)/prev*100

        plt.figure(figsize=(10,5))
        plt.style.use('dark_background')
        plt.plot(closes[-100:], color='#00ff88', linewidth=2)
        plt.title(f"SPX {last:.2f} ({change:+.2f}%)", color='white')
        plt.grid(alpha=0.2)
        plt.tight_layout()
        plt.savefig("/tmp/chart.png")
        plt.close()

        caption = f"📊 *SPX {last:.2f} ({change:+.2f}%) - {datetime.now().strftime('%H:%M KSA')}\nhttps://www.tradingview.com/chart/?symbol=SPX"
        with open("/tmp/chart.png","rb") as f:
            res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id":CHAT_ID,"caption":caption},
                files={"photo":f}, timeout=15)
            print(f"Sent {res.status_code} {res.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

def loop():
    time.sleep(5)
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id":CHAT_ID,"text":"✅ بوت SPX اشتغل - النسخة الجديدة"})
        print("Start msg sent")
    except Exception as e:
        print(f"Start fail {e}")
    while True:
        check_and_send()
        time.sleep(300)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
