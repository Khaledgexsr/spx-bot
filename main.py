import os, time, requests, yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_photo_and_text():
    spx = yf.Ticker("^GSPC")
    data = spx.history(period="5d", interval="5m")
    last = data['Close'].iloc[-1]
    vol = data['Volume'].iloc[-1]
    
    plt.figure(figsize=(10,4))
    plt.plot(data['Close'], label='SPX')
    plt.title(f"SPX: {last:.2f} | Volume: {vol}")
    plt.legend()
    plt.savefig("/tmp/spx.png")
    plt.close()
    
    msg = f"📊 SPX Update {datetime.now().strftime('%H:%M')} KSA\nالسعر: {last:.2f}\nالفوليوم: {vol}\nhttps://www.tradingview.com/chart/?symbol=SPX"
    
    with open("/tmp/spx.png", "rb") as f:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                      data={"chat_id": CHAT_ID, "caption": msg},
                      files={"photo": f})

# رسالة بداية
requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
              data={"chat_id": CHAT_ID, "text": "✅ بوت SPX اشتغل مع الصور"})

while True:
    try:
        send_photo_and_text()
    except Exception as e:
        print(e)
    time.sleep(300)
