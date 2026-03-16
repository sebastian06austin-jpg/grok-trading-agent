import os
from openai import OpenAI
import yfinance as yf
import requests
from datetime import datetime

# === YOUR SETTINGS ===
TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS", "AAPL", "NVDA", "TSLA", "MSFT"]

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage"
    requests.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": message, "parse_mode": "HTML"})

# Fetch data safely
data = {}
for t in TICKERS:
    try:
        stock = yf.Ticker(t)
        hist = stock.history(period="1y")
        if len(hist) >= 2:
            close = hist['Close']
            current = close.iloc[-1]
            prev = close.iloc[-2]
            sma50 = close.rolling(50).mean().iloc[-1]
            change = (current - prev) / prev * 100
            data[t] = f"Price: {current:.2f} | 1d change: {change:.2f}% | 50-day avg: {sma50:.2f}"
        else:
            data[t] = "No recent data available"
    except Exception:
        data[t] = "Data fetch error (safe skip)"

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
print("Report sent successfully!")
