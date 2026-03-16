import os
from openai import OpenAI
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# === YOUR SETTINGS ===
TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "AAPL", "NVDA", "TSLA", "MSFT"]  # Indian + global

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage"
    requests.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": message, "parse_mode": "HTML"})

# Fetch data
data = {}
for t in TICKERS:
    stock = yf.Ticker(t)
    hist = stock.history(period="1y")
    if not hist.empty:
        current = hist['Close'][-1]
        sma50 = hist['Close'].rolling(50).mean()[-1]
        change = (current - hist['Close'][-2]) / hist['Close'][-2] * 100
        data[t] = f"Price: ₹{current:.2f} | 1d change: {change:.2f}% | 50-day avg: ₹{sma50:.2f}"

# Send to Grok
prompt = f"""You are EliteTrade Agent – the most accurate financial reasoning AI.
Today is {datetime.now().strftime('%Y-%m-%d')}.
Analyze these stocks with real data:
{data}

Rules:
- Only suggest trades with real edge
- Max risk 1% per trade
- Output ONLY in this format (nothing else):
Top 3 Setups:
1. TICKER – BUY/SELL/HOLD | Entry | Stop | Target | Confidence XX% | Full plain-English reason (2-3 lines)
If no good setups today, say "No high-confidence trades today. Market neutral."

Be extremely accurate and conservative."""

response = client.chat.completions.create(
    model="grok-4-0709",
    messages=[{"role": "system", "content": "You are a professional risk-managed trader."},
              {"role": "user", "content": prompt}],
    max_tokens=800
)

result = response.choices[0].message.content
send_telegram(f"<b>Grok Daily Trading Report</b>\n\n{result}")
print("Report sent!")
