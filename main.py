import os, time, requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_text(msg):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg})

send_text("✅ بوت SPX مع صور الفوليوم اشتغل")

while True:
    print("Bot alive")
    time.sleep(300)
