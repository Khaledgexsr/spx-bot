import os, time, requests, threading
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

print("TOKEN exists:", bool(TOKEN))
print("TOKEN length:", len(TOKEN) if TOKEN else 0)

r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe")
print("getMe status:", r.status_code)
print("getMe response:", r.text)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot alive"

def check_and_send():
    try:
        print("Checking SPX...", flush=True)
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=5m&range=1d"
        r = requests.get(url, headers=headers, timeout=15)
        print(f"Yahoo status: {r.status_code}", flush=True)
        j = r.json()['chart']['result'][0]
        closes = j['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None]
        last = closes[-1]
        prev = closes[-2]
        change = (last-prev)/prev*100
        plt.figure(figsize=(10,5))
        plt.style.use('dark_background')
        plt.plot(closes[-100:], color='#00ff88', linewidth=2)
        plt.title(f"SPX {last:.2f} ({change:+.2f}%)")
        plt.grid(alpha=0.2)
        plt.tight_layout()
        plt.savefig("/tmp/chart.png")
        plt.close()
        cap = f"SPX {last:.2f} ({change:+.2f}%) {datetime.now().strftime('%H:%M')}"
        with open("/tmp/chart.png","rb") as f:
            res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={"chat_id":CHAT_ID,"caption":cap}, files={"photo":f}, timeout=15)
            print(f"Sent {res.status_code}", flush=True)
    except Exception as e:
        print(f"Error {e}", flush=True)

def bg():
    print("Loop started", flush=True)
    time.sleep(5)
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":"✅ بوت SPX اشتغل"}, timeout=10)
        print("Start msg sent", flush=True)
    except Exception as e:
        print(f"Start fail {e}", flush=True)
    while True:
        check_and_send()
        time.sleep(300)

threading.Thread(target=bg, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
