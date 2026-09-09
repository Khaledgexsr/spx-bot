import os, time, requests, yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("AAFfZ7_4AowjTRgYS7qLMWS2RRXAyA8JXik")
CHAT_ID = os.getenv("955971198")

def check_and_send():
    try:
        spx = yf.Ticker("^GSPC")
        df = spx.history(period="2d", interval="5m")
        if df.empty: return
        
        last = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        vol = df['Volume'].iloc[-1]
        change = ((last - prev) / prev) * 100
        
        plt.figure(figsize=(10,5))
        plt.style.use('dark_background')
        plt.plot(df['Close'].tail(100), color='#00ff88', linewidth=2)
        plt.title(f"SPX {last:.2f} ({change:+.2f}%) Vol: {vol:,.0f}", color='white')
        plt.grid(alpha=0.2)
        plt.tight_layout()
        plt.savefig("/tmp/chart.png")
        plt.close()
        
        caption = f"""📊 *SPX Update* {datetime.now().strftime('%H:%M KSA')}
*السعر:* {last:.2f} ({change:+.2f}%)
*الفوليوم:* {vol:,.0f}
*التغير:* {'🟢 صاعد' if change>0 else '🔴 هابط'}

🔗 [TradingView](https://www.tradingview.com/chart/?symbol=SPX)"""

        with open("/tmp/chart.png", "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                          data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
                          files={"photo": f})
    except Exception as e:
        print(f"Error: {e}")

# رسالة بدء
requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
              data={"chat_id": CHAT_ID, "text": "✅ بوت SPX مع الفوليوم اشتغل"})

while True:
    check_and_send()
    time.sleep(300)
