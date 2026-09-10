import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import requests
import os
import time
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_data():
    # SPX
    spx = yf.Ticker("^GSPC")
    hist = spx.history(period="1d", interval="1m")
    if hist.empty:
        raise Exception("ياهو ما رجع سعر SPX")
    price = hist['Close'].iloc[-1]
    vol_1m = int(hist['Volume'].iloc[-1])

    # SPXW Options
    # نجيب تاريخ اليوم
    today = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    opt = yf.Ticker("SPXW")

    # جرب كل التواريخ المتاحة
    try:
        dates = opt.options
        if not dates:
            raise Exception("ما فيه تواريخ اوبشن")
        # خذ اقرب تاريخ
        chain = opt.option_chain(dates[0])
        df_calls = chain.calls
        df_puts = chain.puts
        df_all = pd.concat([df_calls, df_puts])
        # فلتر سترايكات قريبة من السعر +- 100 نقطة
        df_all = df_all[(df_all['strike'] >= price-100) & (df_all['strike'] <= price+100)]
        df_vol = df_all[['strike','volume']].copy()
        df_vol = df_vol.sort_values('volume', ascending=False)
    except Exception as e:
        print(f"Options error: {e} - using dummy")
        # لو فشل الاوبشن نرسل بس السعر
        df_vol = pd.DataFrame({'strike':[price-20, price-10, price+10, price+20], 'volume':[1000,2000,2000,1000]})

    return price, vol_1m, df_vol

def plot_premium(price, df_vol):
    plt.figure(figsize=(10,4))
    plt.bar(df_vol['strike'].astype(str), df_vol['volume'], color='orange')
    plt.axvline(x=str(int