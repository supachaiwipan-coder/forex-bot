from flask import Flask
import threading
import time
import os
import io
import requests
import xml.etree.ElementTree as ET
import yfinance as yf

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# ========================================================
# ⚙️ [CONFIG: Your Telegram Chat ID]
# ========================================================
MY_CHAT_ID = -1003911767447  

sent_news_links = set()

@app.route('/')
def home():
    return "Forex Core System Online 🚀"

def escape_html(text):
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try: 
        res = requests.post(url, json=payload, timeout=8)
        print(f"🔗 Sent to Telegram Status: {res.status_code}")
    except Exception as e: 
        print(f"❌ Telegram Connection Error: {e}")

# ========================================================
# 🧠 AI Engine: English News Summary & Market Impact
# ========================================================
def summarize_news_with_gemini(api_key, raw_title):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        f"You are a professional Forex and Gold market analyst. "
        f"Translate, rewrite, and summarize the following English news headline into a concise, brief English summary. "
        f"Format it with bullet points that are extremely short and easy to read within 2-3 lines. "
        f"Conclude with a clear market impact analysis on Gold (XAU/USD) or US Dollar Index (DXY) "
        f"(e.g., 'Market Impact: Bullish for Gold / Bearish for DXY').\n\n"
        f"News Headline: {raw_title}"
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"❌ Gemini AI Core Error: {e}")
    return None

# ========================================================
# 📈 1. Market Index Chart Processor (Every 1 Hour)
# ========================================================
def chart_loop_process(token):
    while True:
        try:
            gold_ticker = yf.Ticker("GC=F")       
            oil_ticker = yf.Ticker("CL=F")        
            dxy_ticker = yf.Ticker("DX-Y.NYB")    

            gold_hist = gold_ticker.history(period="7d", interval="1h")
            oil_hist = oil_ticker.history(period="1d")
            dxy_hist = dxy_ticker.history(period="7d", interval="1h")

            if not gold_hist.empty and not dxy_hist.empty and not oil_hist.empty:
                current_gold = gold_hist['Close'].iloc[-1]
                current_oil = oil_hist['Close'].iloc[-1]
                current_dxy = dxy_hist['Close'].iloc[-1]

                gold_hist['MA20'] = gold_hist['Close'].rolling(window=20).mean()
                ma20_val = gold_hist['MA20'].iloc[-1]

                if current_gold > ma20_val:
                    recommendation = "📈 <b>Technical Analysis (1H):</b> BULLISH Trend\n🎯 <b>Trading Signal:</b> Look for <b>BUY / LONG</b> setups."
                else:
                    recommendation = "📉 <b>Technical Analysis (1H):</b> BEARISH Trend\n🎯 <b>Trading Signal:</b> Look for <b>SELL / SHORT</b> setups."

                caption = (
                    f"📊 <b>Real-Time Market Indices & Report</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🪙 <b>Gold Price (XAU/USD):</b> ${current_gold:,.2f}\n"
                    f"🛢️ <b>WTI Crude Oil:</b> ${current_oil:,.2f} / bbl\n"
                    f"💵 <b>US Dollar Index (DXY):</b> {current_dxy:,.2f}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"{recommendation}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ <i>Automated analysis. Manage your own risk.</i>"
                )

                fig, ax1 = plt.subplots(figsize=(10, 5))
                color = '#d4af37'
                ax1.set_xlabel('Date & Time (Past 7 Days)', fontweight='bold')
                ax1.set_ylabel('Gold Price ($/oz)', color=color, fontweight='bold')
                ax1.plot(gold_hist.index, gold_hist['Close'], color=color, linewidth=2, label='Gold')
                ax1.tick_params(axis='y', labelcolor=color)
                ax1.grid(True, linestyle=':', alpha=0.5)

                ax2 = ax1.twinx()
                color = '#1f77b4'
                ax2.set_ylabel('US Dollar Index (DXY)', color=color, fontweight='bold')
                ax2.plot(dxy_hist.index, dxy_hist['Close'], color=color, linewidth=1.5, linestyle='--', label='DXY')
                ax2.tick_params(axis='y', labelcolor=color)

                plt.title('Real-time Technical Chart: Gold vs US Dollar Index', fontsize=14, fontweight='bold', pad=15)
                fig.tight_layout()

                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150)
                buf.seek(0)
                plt.close()

                photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
                files = {'photo': ('chart.png', buf, 'image/png')}
                payload = {'chat_id': MY_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
                requests.post(photo_url, data=payload, files=files, timeout=20)
        except Exception as e:
            print(f"❌ Chart Generation Error: {e}")
            
        time.sleep(3600)

# ========================================================
# 🌐 2. Live News Streamer & AI Processor (Every 10 Seconds)
# ========================================================
def news_loop_process(token, gemini_key):
    print("🚀 Real-time news surveillance engine activated...")
    
    first_check = True 
    headers = {"User-Agent": "Mozilla/5.0"}
    feeds = {
        "Investing.com": "https://www.investing.com/rss/news_1.rss",
        "CNBC Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    }

    while True:
        for source, url in feeds.items():
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code != 200: continue
                
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                target_items = items[:2] if first_check else reversed(items)
                
                for item in target_items:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    if title_elem is None or link_elem is None: continue
                    
                    title = title_elem.text.strip() if title_elem.text else ""
                    link = link_elem.text.strip() if link_elem.text else ""
                    
                    if not link or link in sent_news_links: continue
                    sent_news_links.add(link)
                    
                    # AI summary execution
                    en_summary = summarize_news_with_gemini(gemini_key, title)
                    if not en_summary: continue
                        
                    clean_summary = escape_html(en_summary)
                    
                    message = (
                        f"📰 <b>BREAKING NEWS REPORT ({source})</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"{clean_summary}\n\n"
                        f"🔗 <a href='{link}'>Read Full Coverage</a>"
                    )
                    send_telegram_message(token, MY_CHAT_ID, message)
                    time.sleep(2) 
            except Exception as e:
                print(f"❌ Feed Processing Error [{source}]: {e}")
                
        first_check = False
        time.sleep(10) 

# ========================================================
# 🔁 3. Core Initialization 
# ========================================================
def start_bot():
    token = os.environ.get("TOKEN")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not token or not gemini_key:
        print("❌ System Error: Missing TOKEN or GEMINI_API_KEY variables in Render!")
        return
        
    threading.Thread(target=chart_loop_process, args=(token,), daemon=True).start()
    threading.Thread(target=news_loop_process, args=(token, gemini_key), daemon=True).start()

start_bot()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
