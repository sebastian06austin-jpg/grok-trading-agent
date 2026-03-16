import os
from openai import OpenAI
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime

# === SETTINGS ===
TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS", "ICICIBANK.NS", 
           "ITC.NS", "HINDUNILVR.NS", "BHARTIARTL.NS", "AAPL", "NVDA", "TSLA", "MSFT", "GOOGL"]

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage"
    requests.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": message, "parse_mode": "HTML"})

# Fetch super data
data = {}
for t in TICKERS:
    try:
        stock = yf.Ticker(t)
        hist = stock.history(period="1y")
        info = stock.info
        
        if len(hist) >= 50:
            close = hist['Close']
            current = close.iloc[-1]
            prev = close.iloc[-2]
            change = (current - prev) / prev * 100
            
            rsi = ta.rsi(close, length=14).iloc[-1]
            macd = ta.macd(close)['MACD_12_26_9'].iloc[-1]
            bb_upper = ta.bbands(close)['BBU_20_2.0'].iloc[-1]
            bb_lower = ta.bbands(close)['BBL_20_2.0'].iloc[-1]
            volume_change = (hist['Volume'].iloc[-1] / hist['Volume'].iloc[-2]) * 100 - 100
            
            data[t] = {
                "name": info.get('longName', t),
                "price": round(current, 2),
                "change": round(change, 2),
                "rsi": round(rsi, 1),
                "macd": round(macd, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
                "volume_change": round(volume_change, 1),
                "pe": info.get('trailingPE', 'N/A'),
                "eps": info.get('trailingEps', 'N/A'),
                "sector": info.get('sector', 'N/A')
            }
    except:
        data[t] = {"name": t, "error": "Data issue"}

# Super prompt for full transparent reasoning
prompt = f"""You are EliteTrade Super-Computer Agent powered by Grok 4.20 Multi-Agent Beta.
Today is {datetime.now().strftime('%Y-%m-%d %H:%M')} IST.

Here is complete real-time data for analysis:
{data}

INSTRUCTIONS (follow exactly):
1. Show EVERY step of your multi-agent thinking process.
2. Start with Global Market Snapshot (major indices, key news impact, overall sentiment).
3. For EVERY ticker: full technical analysis (RSI, MACD, Bollinger, volume), fundamentals, risk-reward calculation.
4. Compare stocks against each other.
5. End with Ranked Top 3 Setups only (or say none if none qualify).
6. For each setup: Entry | Stop | Target | Risk-Reward ratio | Confidence % | Full decision chain visible.
7. Be extremely detailed, conservative, and transparent. Use tables and bullets.
8. Never suggest more than 1% portfolio risk per trade.
Output a massive, professional report (use HTML formatting for Telegram: <b>, <code>, bullets)."""

response = client.chat.completions.create(
    model="grok-4.20-multi-agent-beta-0309",
    messages=[
        {"role": "system", "content": "You are the world's most accurate risk-managed trading super-computer. Show all reasoning."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=4000
)

result = response.choices[0].message.content
full_report = f"<b>🚀 SUPER GROK TRADING REPORT</b>\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M IST')}</i>\n\n{result}"

send_telegram(full_report)
print("Super report sent!")
