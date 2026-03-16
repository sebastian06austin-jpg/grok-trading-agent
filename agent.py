import os
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

# Proper IST time (no deprecation warning)
utc_now = datetime.now(timezone.utc)
ist_now = utc_now + timedelta(hours=5, minutes=30)
is_morning = ist_now.hour < 12
report_title = "🌅 Morning Intelligence Briefing" if is_morning else "🌆 Evening Market Debrief"

# === FETCH SUPER DATA ===
data = {}
for t in TICKERS:
    try:
        stock = yf.Ticker(t)
        hist_1y = stock.history(period="1y")
        if len(hist_1y) < 50:
            data[t] = "Insufficient data"
            continue
        close = hist_1y['Close']
        volume = hist_1y['Volume']
        
        rsi = ta.rsi(close, length=14).iloc[-1]
        macd = ta.macd(close).iloc[-1]['MACD_12_26_9']
        bb = ta.bbands(close).iloc[-1]
        atr = ta.atr(hist_1y['High'], hist_1y['Low'], close, length=14).iloc[-1]
        vol_change = (volume.iloc[-1] / volume.rolling(20).mean().iloc[-1] - 1) * 100
        
        info = stock.info
        pe = info.get('trailingPE', 'N/A')
        eps = info.get('trailingEps', 'N/A')
        
        current = close.iloc[-1]
        change_1d = (current - close.iloc[-2]) / close.iloc[-2] * 100
        
        data[t] = {
            "price": round(current, 2),
            "change_1d": round(change_1d, 2),
            "rsi": round(rsi, 1),
            "macd": round(macd, 2),
            "bb_upper": round(bb['BBU_5_2.0'], 2),
            "bb_lower": round(bb['BBL_5_2.0'], 2),
            "atr": round(atr, 2),
            "vol_change": round(vol_change, 1),
            "pe": pe,
            "eps": eps
        }
    except:
        data[t] = "Data error"

# === SUPER PROMPT (4-agent simulation + full research) ===
prompt = f"""You are EliteSuperTrader — a 4-agent super-computer team (Captain for strategy, Harper for technicals, Benjamin for fundamentals, Lucas for risk). 
Today is {datetime.now().strftime('%Y-%m-%d %H:%M')} IST. Report type: {report_title}

Full market data:
{data}

INSTRUCTIONS:
- Act as all 4 agents debating internally before final answer (show the debate in your reasoning).
- Analyze EVERY single ticker in detail — even if price is completely flat or no change.
- Show complete research process and step-by-step decision making.
- Structure exactly like this:

{report_title}

MARKET OVERVIEW
- Nifty 50 summary + key global factors + overall sentiment

DETAILED ANALYSIS FOR EVERY TICKER
For each stock:
• Current price & 1-day change
• Technical breakdown (RSI, MACD, Bollinger Bands, ATR volatility)
• Volume surge analysis
• Fundamentals (PE, EPS)
• Full agent debate reasoning: why edge exists or not today
• Risk assessment (volatility, stop distance)

FINAL RECOMMENDATIONS
Top 3–5 setups:
- Action (BUY/SELL/HOLD)
- Suggested Entry, Stop-Loss, Target (with exact risk-reward ratio)
- Confidence % 
- Full plain-English explanation of the entire decision chain

RISK RULES: Never risk >1% capital. Stay extremely conservative.

Be extremely thorough, show all math and logic, never skip any stock. Use ₹ for .NS stocks.

Output ONLY this full structured report."""

response = client.chat.completions.create(
    model="grok-4.20-beta-0309-reasoning",
    messages=[
        {"role": "system", "content": "You are a professional risk-managed trading super-computer. Always show full internal agent debate and reasoning."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=3000,
    temperature=0.7
)

result = response.choices[0].message.content
send_telegram(f"<b>{report_title}</b>\n\n{result}")
print("Super report sent successfully!")
