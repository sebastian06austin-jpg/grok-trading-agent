import os
from openai import OpenAI
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime

# === SETTINGS ===
TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS", "ICICIBANK.NS", "ITC.NS", "BHARTIARTL.NS", "HINDUNILVR.NS", "LT.NS",
           "AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "^NSEI"]  # Top Indian + Global + Nifty

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage"
    requests.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": message, "parse_mode": "HTML"})

# Detect morning or evening
now_ist = datetime.utcnow().hour + 5.5
is_morning = now_ist < 12
report_title = "🌅 Morning Intelligence Briefing" if is_morning else "🌆 Evening Market Debrief"

# === FETCH SUPER DATA ===
data = {}
for t in TICKERS:
    try:
        stock = yf.Ticker(t)
        hist_1y = stock.history(period="1y")
        hist_1mo = stock.history(period="1mo")
        
        if len(hist_1y) < 50:
            data[t] = "Insufficient data"
            continue
            
        close = hist_1y['Close']
        volume = hist_1y['Volume']
        
        # Professional indicators
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

# === SUPER PROMPT FOR FULL RESEARCH + DECISION MAKING ===
prompt = f"""You are EliteSuperTrader — a multi-agent super-computer trading team (Grok 4.20 Multi-Agent).
Today is {datetime.now().strftime('%Y-%m-%d %H:%M')} IST. Report type: {report_title}

Full market data:
{data}

INSTRUCTIONS FOR SUPER DETAILED REPORT:
1. ALWAYS analyze EVERY single ticker — even if price is flat or no change.
2. Show your complete research process and step-by-step decision making (like internal agent debate).
3. Structure the report exactly like this:

{report_title}

MARKET OVERVIEW
- Nifty 50 summary
- Overall sentiment & key global factors

DETAILED ANALYSIS FOR EVERY TICKER
For each stock:
• Current price & 1-day change
• Technical breakdown (RSI, MACD, Bollinger Bands, ATR volatility)
• Volume analysis
• Fundamentals (PE, EPS if available)
• Full reasoning: why this setup has edge or no edge today
• Risk assessment

FINAL RECOMMENDATIONS
Top 3–5 setups with:
- Action (BUY/SELL/HOLD)
- Suggested Entry, Stop-Loss, Target
- Exact risk-reward ratio
- Confidence % 
- Full plain-English explanation of the entire decision chain

RISK MANAGEMENT RULES
- Never risk more than 1% of capital
- Conservative approach

Be extremely thorough, show all math and logic, never skip any stock. Use Indian Rupee for .NS stocks.

Output only this full structured report. No extra text."""

response = client.chat.completions.create(
    model="grok-4.20-multi-agent-beta-0309",
    messages=[
        {"role": "system", "content": "You are a professional risk-managed trading super-computer. Always show full reasoning."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=2500,
    temperature=0.7
)

result = response.choices[0].message.content
send_telegram(f"<b>{report_title}</b>\n\n{result}")
print("Super report sent successfully!")
