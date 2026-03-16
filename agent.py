import os
import time
from openai import OpenAI
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime, timedelta, timezone

# === SETTINGS ===
TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS", "ICICIBANK.NS", "ITC.NS", "BHARTIARTL.NS", "HINDUNILVR.NS", "LT.NS",
           "AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "^NSEI"]

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage"
    requests.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": message, "parse_mode": "HTML"})

# Proper IST time
utc_now = datetime.now(timezone.utc)
ist_now = utc_now + timedelta(hours=5, minutes=30)
is_morning = ist_now.hour < 12
report_title = "🌅 Morning Intelligence Briefing" if is_morning else "🌆 Evening Market Debrief"

# === ROBUST BATCH DATA FETCH (2026 fix) ===
print("Fetching market data with retries...")
data = {}

tickers_str = " ".join(TICKERS)
for attempt in range(3):
    try:
        df_multi = yf.download(tickers_str, period="1y", group_by="ticker", progress=False, auto_adjust=True, prepost=False)
        if not df_multi.empty:
            print(f"Data fetched successfully on attempt {attempt+1}")
            break
        time.sleep(3)
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(3)
else:
    print("All fetch attempts failed")

# Process each ticker safely
for t in TICKERS:
    try:
        if t in df_multi.columns.get_level_values(0):
            hist = df_multi[t].dropna()
        else:
            stock = yf.Ticker(t)
            hist = stock.history(period="1y", auto_adjust=True)
        
        if len(hist) < 50:
            data[t] = {"status": "Insufficient history"}
            continue
            
        close = hist['Close']
        volume = hist['Volume']
        
        rsi = ta.rsi(close, length=14).iloc[-1]
        macd_line = ta.macd(close).iloc[-1]['MACD_12_26_9']
        bb = ta.bbands(close).iloc[-1]
        atr = ta.atr(hist['High'], hist['Low'], close, length=14).iloc[-1]
        vol_change = (volume.iloc[-1] / volume.rolling(20).mean().iloc[-1] - 1) * 100
        
        info = yf.Ticker(t).info
        pe = info.get('trailingPE', 'N/A')
        eps = info.get('trailingEps', 'N/A')
        
        current = close.iloc[-1]
        change_1d = (current - close.iloc[-2]) / close.iloc[-2] * 100 if len(close) >= 2 else 0
        
        data[t] = {
            "price": round(current, 2),
            "change_1d": round(change_1d, 2),
            "rsi": round(rsi, 1),
            "macd": round(macd_line, 2),
            "bb_upper": round(bb['BBU_5_2.0'], 2),
            "bb_lower": round(bb['BBL_5_2.0'], 2),
            "atr": round(atr, 2),
            "vol_change": round(vol_change, 1),
            "pe": pe,
            "eps": eps,
            "status": "OK"
        }
    except Exception as e:
        data[t] = {"status": f"Error: {str(e)[:100]}"}

# === SUPER PROMPT (unchanged – full research + agent debate) ===
prompt = f"""You are EliteSuperTrader — a 4-agent super-computer team (Captain, Harper, Benjamin, Lucas). 
Today is {datetime.now().strftime('%Y-%m-%d %H:%M')} IST. Report type: {report_title}

Full market data:
{data}

INSTRUCTIONS:
- Analyze EVERY ticker in detail (even if price flat).
- Show internal 4-agent debate in reasoning.
- Structure EXACTLY as below:

{report_title}

MARKET OVERVIEW
- Nifty 50 summary + global factors + sentiment

DETAILED ANALYSIS FOR EVERY TICKER
• Price & change
• Technicals (RSI, MACD, Bollinger, ATR)
• Volume & fundamentals
• Full agent debate + edge explanation

FINAL RECOMMENDATIONS
Top 3–5 setups with Action | Entry | Stop | Target | RR ratio | Confidence % | explanation

RISK RULE: Never risk >1% capital. Stay conservative.

Use ₹ for .NS stocks. Output ONLY this full structured report."""

response = client.chat.completions.create(
    model="grok-4.20-beta-0309-reasoning",
    messages=[
        {"role": "system", "content": "You are a professional risk-managed trading super-computer. Always show full internal debate."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=3000,
    temperature=0.7
)

result = response.choices[0].message.content
send_telegram(f"<b>{report_title}</b>\n\n{result}")
print("Super report sent successfully!")
